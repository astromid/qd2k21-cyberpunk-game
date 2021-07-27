from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import List, Optional


class ThemeColors(Enum):
    RED = '#ee6666'
    GREEN = '#91cc75'
    BLUE = '#5470c6'
    GRAY = '#bbbbbb'


@dataclass
class User:
    uid: str
    name: str
    ticket: str
    home_market: str


@dataclass
class Transaction:
    from_: str
    to_: str
    amount: float
    cycle: int


@dataclass
class InvestmentBid:
    uid: str
    market: str
    amount: float
    timestamp_created: datetime
    timestamp_approved: Optional[datetime]
    status: Optional[int]
    cycle: int
    income: Optional[float]
