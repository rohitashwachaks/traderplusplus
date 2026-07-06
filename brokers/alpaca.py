import requests

from brokers.base import Broker
from utils.config import ALPACA_API_KEY, ALPACA_API_SECRET, ALPACA_BASE_URL


class AlpacaBroker(Broker):
    """Alpaca **paper** trading via the REST API (plain ``requests``).

    We talk to the REST endpoints directly rather than via ``alpaca-py`` to avoid a
    pydantic-v2 dependency clash in this environment. The base URL must be a paper host —
    we assert it so this seam can never hit a live account. Credentials come from
    ``ALPACA_API_KEY`` / ``ALPACA_API_SECRET`` in ``.env``.
    """

    def __init__(self):
        assert ALPACA_API_KEY and ALPACA_API_SECRET, \
            "Set ALPACA_API_KEY and ALPACA_API_SECRET in .env"
        self._base = ALPACA_BASE_URL.rstrip("/").removesuffix("/v2")
        assert "paper-api" in self._base, \
            f"Refusing to trade against a non-paper endpoint: {self._base}"
        self._session = requests.Session()
        self._session.headers.update({
            "APCA-API-KEY-ID": ALPACA_API_KEY,
            "APCA-API-SECRET-KEY": ALPACA_API_SECRET,
        })

    def _get(self, path: str):
        resp = self._session.get(f"{self._base}/v2/{path}", timeout=30)
        if not resp.ok:
            raise RuntimeError(f"Alpaca GET {path} failed [{resp.status_code}]: {resp.text}")
        return resp.json()

    def equity(self) -> float:
        return float(self._get("account")["equity"])

    def positions(self) -> dict[str, float]:
        return {p["symbol"]: float(p["qty"]) for p in self._get("positions")}

    def submit(self, ticker: str, qty: int, side: str) -> None:
        resp = self._session.post(f"{self._base}/v2/orders", timeout=30, json={
            "symbol": ticker, "qty": qty, "side": side,
            "type": "market", "time_in_force": "day",
        })
        if not resp.ok:
            raise RuntimeError(f"Alpaca order {side} {qty} {ticker} failed "
                               f"[{resp.status_code}]: {resp.text}")

    def orders(self, since: str) -> list[dict]:
        resp = self._session.get(f"{self._base}/v2/orders", timeout=30, params={
            "status": "all", "after": since, "limit": 500, "direction": "asc",
        })
        if not resp.ok:
            raise RuntimeError(f"Alpaca GET orders failed [{resp.status_code}]: {resp.text}")
        return [
            {"symbol": o["symbol"], "side": o["side"], "qty": float(o["qty"] or 0),
             "filled_qty": float(o["filled_qty"] or 0),
             "filled_avg_price": float(o["filled_avg_price"] or 0),
             "status": o["status"], "submitted_at": o["submitted_at"]}
            for o in resp.json()
        ]
