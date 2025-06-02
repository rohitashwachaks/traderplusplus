from typing import Optional
from datetime import datetime
from dataclasses import dataclass
from dataclasses_json import dataclass_json


@dataclass
@dataclass_json
class TradeLog:
    date: datetime
    ticker: str
    action: str  # e.g., 'BUY' or 'SELL'
    shares: int
    price: float
    cash_remaining: float
    note: Optional[str] = None  # Optional field
