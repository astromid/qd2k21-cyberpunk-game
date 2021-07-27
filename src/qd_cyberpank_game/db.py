import hashlib
from datetime import datetime
from typing import Dict, Optional, Tuple, Union

import pandas as pd
from sqlalchemy import MetaData, Table, create_engine, insert, or_, select, update

from qd_cyberpank_game.engine import calculate_investments
from qd_cyberpank_game.structures import InvestmentBid, Transaction, User

DEFAULT_FUND_SPEED = 1000


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


def get_current_cycle(db_conn_str: str, cycles_table: Table) -> Tuple[int, float]:
    engine = create_engine(db_conn_str, future=True)
    stmt = select(cycles_table.c.cycle, cycles_table.c.fund_speed).order_by(cycles_table.c.timestamp.desc())
    with engine.connect() as conn:
        result = conn.execute(stmt).first()
    return (result.cycle, result.fund_speed) if result is not None else (1, DEFAULT_FUND_SPEED)


def make_next_cycle(db_conn_str, current_cycle: int, fund_speed: float, cycles_table: Table) -> None:
    engine = create_engine(db_conn_str, future=True)
    stmt = insert(cycles_table).values(cycle=current_cycle + 1, timestamp=datetime.now(), fund_speed=fund_speed)
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
    select_cols = [c.id, c.uid, c.market, c.amount, c.timestamp_created, c.timestamp_approved, c.status, c.cycle, c.income]
    select_cols_names = [col.name for col in select_cols]
    stmt = select(*select_cols)
    stmt = stmt.where(c.cycle == cycle)
    if uid != 'root':
        stmt = stmt.where(c.uid == uid)
    with engine.connect() as conn:
        result = conn.execute(stmt).fetchall()
    return pd.DataFrame(
        data=[InvestmentBid(*requirement) for requirement in result],
        columns=select_cols_names,
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


def update_investment_status(db_conn_str: str, investments_table: Table, bid_id: int, status: int) -> None:
    engine = create_engine(db_conn_str, future=True)
    stmt = update(investments_table).where(investments_table.c.id == bid_id)
    if status == 1:
        stmt = stmt.values(status=status, timestamp_approved=datetime.now())
    else:
        stmt = stmt.values(status=status)
    with engine.connect() as conn:
        conn.execute(stmt)
        conn.commit()


def update_investment_income(db_conn_str: str, investments_table: Table, bid_id: int, income: float) -> None:
    engine = create_engine(db_conn_str, future=True)
    stmt = update(investments_table).where(investments_table.c.id == bid_id)
    stmt = stmt.values(income=income)
    with engine.connect() as conn:
        conn.execute(stmt)
        conn.commit()


def get_stocks(db_conn_str: str, stocks_table: Table) -> pd.DataFrame:
    engine = create_engine(db_conn_str, future=True)
    stmt = select(stocks_table.c.price, stocks_table.c.ticket, stocks_table.c.cycle)
    with engine.connect() as conn:
        result = conn.execute(stmt).fetchall()
    return pd.DataFrame(result, columns=[stocks_table.c.price.name, stocks_table.c.ticket.name, stocks_table.c.cycle.name])


def update_market_capacity(db_conn_str: str, markets_table: Table, market: str, capacity: float) -> None:
    engine = create_engine(db_conn_str, future=True)
    stmt = update(markets_table).where(markets_table.c.name == market)
    stmt = stmt.values(capacity=capacity)
    with engine.connect() as conn:
        conn.execute(stmt)
        conn.commit()


def calculate_markets_state(
    db_conn_str: str,
    investments_df: pd.DataFrame,
    markets_df: pd.DataFrame,
    fund_speed: float,
    cycle: int,
    investments_table: Table,
    markets_table: Table,
    transactions_table: Table,
):
    market_incomes, market_capacities = calculate_investments(investments_df, markets_df, fund_speed)
    for market, capacity in market_capacities.items():
        update_market_capacity(db_conn_str, markets_table, market, capacity)

    for invest_income in market_incomes:
        update_investment_income(db_conn_str, investments_table, bid_id=invest_income['bid_id'], income=invest_income['income'])
        if invest_income['income'] >= 0:
            from_ = invest_income['market']
            to_ = invest_income['uid']
        else:
            from_ = invest_income['uid']
            to_ = invest_income['market']
        transaction = Transaction(from_=from_, to_=to_, amount=invest_income['income'], cycle=cycle)
        make_transaction(db_conn_str, transactions_table, transaction)
