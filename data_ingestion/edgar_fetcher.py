"""SEC EDGAR fetchers — the authoritative point-in-time fundamentals source.

Every XBRL fact carries a ``filed`` date (when it became public), which is exactly the stamp
a no-look-ahead fundamental backtest needs. We pull per-company ``companyconcept`` facts and
the ticker→CIK map, caching both to parquet/JSON so a run re-derives without re-hitting SEC.

SEC requires a descriptive ``User-Agent`` with a contact; requests are rate-limited politely.
"""
import json
import logging
import os
import time

import pandas as pd
import requests

from utils.config import DATA_CACHE, DATA_STORE

log = logging.getLogger("traderplusplus")

_HEADERS = {"User-Agent": "traderplusplus research (rohitashwachaks@gmail.com)"}
_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
_CONCEPT_URL = "https://data.sec.gov/api/xbrl/companyconcept/CIK{cik}/{taxonomy}/{concept}.json"
_FACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
_SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"
_REQUEST_PAUSE_S = 0.12  # ~8 req/s — under SEC's 10 req/s ceiling

_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
_LOCAL_CIK_FILES = (os.path.join(_DATA_DIR, "sp500.csv"), os.path.join(_DATA_DIR, "sp50.csv"))


def _local_cik_overrides(paths: tuple[str, ...] = _LOCAL_CIK_FILES) -> dict[str, str]:
    """Ticker → CIK from committed universe CSVs (a ``CIK`` column next to ``Symbol``).

    These are point-of-truth for the names we actually trade — they beat the SEC's live
    ticker map (which only knows *today's* symbols) and need no network call.
    """
    mapping: dict[str, str] = {}
    for path in paths:
        if not os.path.exists(path):
            continue
        table = pd.read_csv(path, sep=None, engine="python")
        cols = {c.lower().strip(): c for c in table.columns}
        if "symbol" not in cols or "cik" not in cols:
            continue
        for sym, cik in zip(table[cols["symbol"]], table[cols["cik"]]):
            if pd.isna(sym) or pd.isna(cik):
                continue
            mapping[str(sym).strip().upper().replace(".", "-")] = f"{int(cik):010d}"
    return mapping


def cik_map() -> dict[str, str]:
    """Map ticker → 10-digit zero-padded CIK. Symbols normalized to yahoo convention.

    The SEC's ``company_tickers.json`` map is fetched once and cached; CIKs from the
    committed universe CSVs (``data/sp500.csv`` etc.) override it, so a stale or mismatched
    live symbol can't misroute a name we explicitly listed.
    """
    cache = os.path.join(DATA_CACHE, "edgar_cik_map.json")
    if os.path.exists(cache):
        with open(cache) as fh:
            mapping = json.load(fh)
    else:
        resp = requests.get(_TICKERS_URL, headers=_HEADERS, timeout=30)
        resp.raise_for_status()
        mapping = {
            row["ticker"].strip().upper().replace(".", "-"): f"{int(row['cik_str']):010d}"
            for row in resp.json().values()
        }
        os.makedirs(DATA_CACHE, exist_ok=True)
        with open(cache, "w") as fh:
            json.dump(mapping, fh)

    mapping.update(_local_cik_overrides())
    return mapping


def fetch_concept(cik: str, concept: str, taxonomy: str = "us-gaap") -> list[dict]:
    """All reported datapoints for one XBRL concept (cached per cik+concept).

    Returns a list of ``{start, end, val, filed, form, fp}`` dicts across every reporting unit.
    A 404 (the company never tags this concept) is cached as empty so we don't refetch it.
    Any other HTTP error raises — we never silently treat a fetch failure as "no data".
    """
    cache = os.path.join(DATA_CACHE, f"edgar_{cik}_{taxonomy}_{concept}.parquet")
    if os.path.exists(cache):
        return pd.read_parquet(cache).to_dict("records")

    url = _CONCEPT_URL.format(cik=cik, taxonomy=taxonomy, concept=concept)
    resp = requests.get(url, headers=_HEADERS, timeout=30)
    os.makedirs(DATA_CACHE, exist_ok=True)
    if resp.status_code == 404:
        empty = pd.DataFrame(columns=["start", "end", "val", "filed", "form", "fp"])
        empty.to_parquet(cache)
        return []
    resp.raise_for_status()

    rows = [
        {"start": e.get("start"), "end": e["end"], "val": e["val"],
         "filed": e["filed"], "form": e.get("form"), "fp": e.get("fp")}
        for entries in resp.json().get("units", {}).values()
        for e in entries
    ]
    df = pd.DataFrame(rows, columns=["start", "end", "val", "filed", "form", "fp"])
    df.to_parquet(cache)
    time.sleep(_REQUEST_PAUSE_S)
    return df.to_dict("records")


_FACTS_COLUMNS = ["taxonomy", "concept", "unit", "start", "end", "val", "filed", "form", "fp", "accn"]


def fetch_company_facts(cik: str) -> pd.DataFrame:
    """Every XBRL fact a company ever filed — the full 10-K / 10-Q line-item history.

    This is the structured ingest for financial statements: one long frame where each row is
    a single datapoint of a single concept (revenue, net income, assets, EPS, shares, …),
    keyed by its **``filed``** date — the point-in-time stamp — never the period it covers.
    Cached to the canonical data store (``data_store/edgar/``), so a universe re-derives
    offline. For a single targeted concept, :func:`fetch_concept` stays the cheaper call.
    """
    cache_dir = os.path.join(DATA_STORE, "edgar")
    cache = os.path.join(cache_dir, f"facts_{cik}.parquet")
    if os.path.exists(cache):
        return pd.read_parquet(cache)

    url = _FACTS_URL.format(cik=cik)
    resp = requests.get(url, headers=_HEADERS, timeout=60)
    os.makedirs(cache_dir, exist_ok=True)
    if resp.status_code == 404:
        empty = pd.DataFrame(columns=_FACTS_COLUMNS)
        empty.to_parquet(cache)
        return empty
    resp.raise_for_status()

    rows = [
        {"taxonomy": taxonomy, "concept": concept, "unit": unit,
         "start": e.get("start"), "end": e["end"], "val": e["val"], "filed": e["filed"],
         "form": e.get("form"), "fp": e.get("fp"), "accn": e.get("accn")}
        for taxonomy, concepts in resp.json().get("facts", {}).items()
        for concept, body in concepts.items()
        for unit, entries in body.get("units", {}).items()
        for e in entries
    ]
    df = pd.DataFrame(rows, columns=_FACTS_COLUMNS)
    numeric = pd.to_numeric(df["val"], errors="coerce")
    dropped = int(numeric.isna().sum() - df["val"].isna().sum())
    if dropped:
        log.warning("CIK %s: %d non-numeric XBRL values coerced to NaN", cik, dropped)
    df["val"] = numeric
    df.to_parquet(cache)
    time.sleep(_REQUEST_PAUSE_S)
    return df


def fetch_submissions(cik: str) -> dict:
    """Company-level EDGAR metadata (name, SIC code/description, exchanges), cached.

    The SIC classification is the comparables / sector-neutral seam that GICS (paid) would
    otherwise cover.
    """
    cache_dir = os.path.join(DATA_STORE, "edgar")
    cache = os.path.join(cache_dir, f"submissions_{cik}.json")
    if os.path.exists(cache):
        with open(cache) as fh:
            return json.load(fh)

    resp = requests.get(_SUBMISSIONS_URL.format(cik=cik), headers=_HEADERS, timeout=30)
    resp.raise_for_status()
    payload = resp.json()
    # The recent-filings block is bulky and duplicated by company facts; keep the metadata.
    payload.pop("filings", None)
    os.makedirs(cache_dir, exist_ok=True)
    with open(cache, "w") as fh:
        json.dump(payload, fh)
    time.sleep(_REQUEST_PAUSE_S)
    return payload
