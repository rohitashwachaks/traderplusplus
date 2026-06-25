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

from utils.config import DATA_CACHE

log = logging.getLogger("traderplusplus")

_HEADERS = {"User-Agent": "traderplusplus research (rohitashwachaks@gmail.com)"}
_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
_CONCEPT_URL = "https://data.sec.gov/api/xbrl/companyconcept/CIK{cik}/{taxonomy}/{concept}.json"
_REQUEST_PAUSE_S = 0.12  # ~8 req/s — under SEC's 10 req/s ceiling


def cik_map() -> dict[str, str]:
    """Map ticker → 10-digit zero-padded CIK (cached). Symbols normalized to yahoo convention."""
    cache = os.path.join(DATA_CACHE, "edgar_cik_map.json")
    if os.path.exists(cache):
        with open(cache) as fh:
            return json.load(fh)

    resp = requests.get(_TICKERS_URL, headers=_HEADERS, timeout=30)
    resp.raise_for_status()
    mapping = {
        row["ticker"].strip().upper().replace(".", "-"): f"{int(row['cik_str']):010d}"
        for row in resp.json().values()
    }
    os.makedirs(DATA_CACHE, exist_ok=True)
    with open(cache, "w") as fh:
        json.dump(mapping, fh)
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
