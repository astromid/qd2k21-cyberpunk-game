import hashlib
from typing import Optional

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

SELECT_QUERY = ""
INSERT_QUERY = ""


def auth(login, password) -> Optional[str]:
    pass
