import hashlib
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

import pandas as pd
from sqlalchemy import MetaData, Table, create_engine, insert, or_, select

from qd_cyberpank_game.structures import InvestmentBid, Transaction, User


def read_db_schema(db_conn_str: str) -> Dict[str, Union[MetaData, Table]]:
    engine = create_engine(db_conn_str, future=True)
    metadata = MetaData()
    return {
        'metadata': metadata,
        'users': Table('users', metadata, autoload_with=engine),
        'cycles': Table('cycles', metadata, autoload_with=engine),
        'stocks': Table('stocks', metadata, autoload_with=engine),
        'transactions': Table('transactions', metadata, autoload_with=engine),
        'markets': Table('markets', metadata, autoload_with=engine),
        'investments': Table('investments', metadata, autoload_with=engine),
    }


def auth(login: str, password: str, db_conn_str: str, users_table: Table) -> Optional[User]:
    engine = create_engine(db_conn_str, future=True)
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    stmt = select(users_table.c.uid, users_table.c.name, users_table.c.ticket, users_table.c.home_market)
    stmt = stmt.filter_by(login=login, password=password_hash)
    with engine.connect() as conn:
        result = conn.execute(stmt).one_or_none()
    if result is not None:
        return User(*result)
    return None


def get_users(db_conn_str: str, users_table: Table) -> pd.DataFrame:
    engine = create_engine(db_conn_str, future=True)
    stmt = select(users_table.c.uid, users_table.c.name, users_table.c.ticket, users_table.c.home_market)
    stmt = stmt.where(users_table.c.uid != 'root')
    with engine.connect() as conn:
        result = conn.execute(stmt).fetchall()
    return pd.DataFrame([User(*user) for user in result])


def get_current_cycle(db_conn_str: str, cycles_table: Table) -> int:
    engine = create_engine(db_conn_str, future=True)
    stmt = select(cycles_table.c.cycle).order_by(cycles_table.c.timestamp.desc())
    with engine.connect() as conn:
        result = conn.execute(stmt).first()
    return result.cycle if result is not None else 1


def make_next_cycle(db_conn_str, current_cycle: int, cycles_table: Table) -> None:
    engine = create_engine(db_conn_str, future=True)
    stmt = insert(cycles_table).values(cycle=current_cycle + 1, timestamp=datetime.now())
    with engine.connect() as conn:
        conn.execute(stmt)
        conn.commit()


def get_transactions(db_conn_str: str, uid: str, transactions_table: Table) -> pd.DataFrame:
    engine = create_engine(db_conn_str, future=True)
    cols = transactions_table.c
    stmt = select(cols.from_, cols.to_, cols.amount, cols.cycle)
    if uid != 'root':
        stmt = stmt.where(or_(cols.from_ == uid, cols.to_ == uid))
    with engine.connect() as conn:
        result = conn.execute(stmt).fetchall()
    return pd.DataFrame([Transaction(*transaction) for transaction in result])


def make_transaction(db_conn_str: str, transactions_table: Table, transaction: Transaction) -> None:
    engine = create_engine(db_conn_str, future=True)
    stmt = insert(transactions_table).values(
        from_=transaction.from_,
        to_=transaction.to_,
        amount=transaction.amount,
        cycle=transaction.cycle,
    )
    with engine.connect() as conn:
        conn.execute(stmt)
        conn.commit()


def get_markets(db_conn_str: str, markets_table: Table) -> pd.DataFrame:
    engine = create_engine(db_conn_str, future=True)
    cols = markets_table.c
    stmt = select(cols.id, cols.name, cols.capacity, cols.min_capacity, cols.link1, cols.link2)
    with engine.connect() as conn:
        result = conn.execute(stmt).fetchall()
    markets_df = pd.DataFrame([dict(market) for market in result])
    markets_df = markets_df.set_index('id')
    markets_df['link1'] = markets_df.loc[markets_df.index.intersection(markets_df['link1'])].reindex(markets_df['link1'])['name'].values
    markets_df['link2'] = markets_df.loc[markets_df.index.intersection(markets_df['link2'])].reindex(markets_df['link2'])['name'].values
    return markets_df


def get_cycle_investments(db_conn_str: str, uid: str, cycle: int, investments_table: Table) -> pd.DataFrame:
    engine = create_engine(db_conn_str, future=True)
    c = investments_table.c
    stmt = select(
        c.uid,
        c.market,
        c.amount,
        c.timestamp_created,
        c.timestamp_approved,
        c.status,
        c.cycle,
        c.income,
    )
    stmt = stmt.where(c.cycle == cycle)
    if uid != 'root':
        stmt = stmt.where(c.uid == uid)
    with engine.connect() as conn:
        result = conn.execute(stmt).fetchall()
    return pd.DataFrame(
        data=[InvestmentBid(*requirement) for requirement in result],
        columns=[c.uid.name, c.market.name, c.amount.name, c.timestamp_created.name, c.timestamp_approved.name, c.status.name, c.cycle.name, c.income.name],
    )


def make_investment(db_conn_str: str, investments_table: Table, invest_bid: InvestmentBid) -> None:
    engine = create_engine(db_conn_str, future=True)
    stmt = insert(investments_table).values(
        uid=invest_bid.uid,
        market=invest_bid.market,
        amount=invest_bid.amount,
        timestamp_created=invest_bid.timestamp_created,
        status=invest_bid.status,
        cycle=invest_bid.cycle,
    )
    with engine.connect() as conn:
        conn.execute(stmt)
        conn.commit()


def get_stocks(db_conn_str: str, stocks_table: Table) -> pd.DataFrame:
    engine = create_engine(db_conn_str, future=True)
    stmt = select(stocks_table.c.price, stocks_table.c.ticket, stocks_table.c.cycle)
    # stmt = stmt.where(stocks_table.c.cycle > 0)
    with engine.connect() as conn:
        result = conn.execute(stmt).fetchall()
    return pd.DataFrame(result, columns=[stocks_table.c.price.name, stocks_table.c.ticket.name, stocks_table.c.cycle.name])
