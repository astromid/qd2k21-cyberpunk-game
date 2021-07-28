import hashlib
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple, Union

import pandas as pd
from sqlalchemy import MetaData, Table, create_engine, insert, or_, select, update

from qd_cyberpank_game.engine import calculate_investments, generate_stocks
from qd_cyberpank_game.structures import InvestmentBid, Transaction, User

DEFAULT_FUND_SPEED = 50000000.0  # 50kk / minute
INIT_STOCK = 100.0
START_BALANCE = 500000000.0
START_CAPATICY = {
    'IT': 250000000.0,
    'Медицина': 250000000.0,
    'Ритейл': 250000000.0,
    'Добыча': 250000000.0,
    'Робототехника': 800000000.0,
    'Фармакология': 800000000.0,
    'Энергетика': 800000000.0,
    'Коммуникации': 800000000.0,
    'Военный комплекс': 2500000000.0,
}
START_BONUSES = {
    '80dfd80bbad0b833f04fcef077fa929362316c3c5e9462bc5e385e084296eb39': 245000000,  # ParaLife
    'b1e92783765ac9d3dc176532f9bb2069b75a6f293defd771a05ee592d853064d': 290000000,  # CyberSell
    'cb1f98e20caeb07a9ecdbeed7d8deb870ca011451ec9b4921c3658f7765f7deb': 295000000,  # FOCS
    'ed30b6622f68b817098c577c1cd4b3da0f955be10962bdd016541a2cf79bdebf': 360000000,  # LOOP
}


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
    return (result.cycle, float(result.fund_speed)) if result is not None else (1, DEFAULT_FUND_SPEED)


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
    transactions = [Transaction(
        from_=tr.from_,
        to_=tr.to_,
        amount=float(tr.amount),
        cycle=tr.cycle,
    ) for tr in result]
    return pd.DataFrame(transactions)


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
    dict_results = [dict(market) for market in result]
    for record in dict_results:
        record['capacity'] = float(record['capacity'])
        record['min_capacity'] = float(record['min_capacity'])
    markets_df = pd.DataFrame(dict_results)
    markets_df = markets_df.set_index('id')
    markets_df['link1'] = markets_df.loc[markets_df.index.intersection(markets_df['link1'])].reindex(markets_df['link1'])['name'].values
    markets_df['link2'] = markets_df.loc[markets_df.index.intersection(markets_df['link2'])].reindex(markets_df['link2'])['name'].values
    return markets_df


def get_cycle_investments(db_conn_str: str, uid: str, cycle: int, investments_table: Table) -> pd.DataFrame:
    engine = create_engine(db_conn_str, future=True)
    c = investments_table.c
    select_cols = [c.id, c.uid, c.market, c.amount, c.timestamp_created, c.timestamp_approved, c.status, c.cycle, c.income, c.multiplier]
    select_cols_names = [col.name for col in select_cols]
    stmt = select(*select_cols)
    stmt = stmt.where(c.cycle == cycle)
    if uid != 'root':
        stmt = stmt.where(c.uid == uid)
    with engine.connect() as conn:
        result = conn.execute(stmt).fetchall()
    investment_bids = [InvestmentBid(*requirement) for requirement in result]
    for bid in investment_bids:
        bid.amount = float(bid.amount) if bid.amount else None
        bid.income = float(bid.income) if bid.income else None
        bid.multiplier = float(bid.multiplier) if bid.multiplier else None
    return pd.DataFrame(
        data=investment_bids,
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
    stmt = stmt.values(status=status, timestamp_approved=datetime.now())
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


def update_investment_multiplier(db_conn_str: str, investments_table: Table, bid_id: int, multiplier: float) -> None:
    engine = create_engine(db_conn_str, future=True)
    stmt = update(investments_table).where(investments_table.c.id == bid_id)
    stmt = stmt.values(multiplier=multiplier)
    with engine.connect() as conn:
        conn.execute(stmt)
        conn.commit()


def get_stocks(db_conn_str: str, stocks_table: Table) -> pd.DataFrame:
    engine = create_engine(db_conn_str, future=True)
    stmt = select(stocks_table.c.price, stocks_table.c.ticket, stocks_table.c.cycle)
    with engine.connect() as conn:
        result = conn.execute(stmt).fetchall()
    dict_results = [dict(record) for record in result]
    for record in dict_results:
        record['price'] = float(record['price'])
        record['cycle'] = float(record['cycle'])
    return pd.DataFrame(dict_results, columns=[stocks_table.c.price.name, stocks_table.c.ticket.name, stocks_table.c.cycle.name])


def make_stocks(db_conn_str: str, stocks_table: Table, stocks_df: pd.DataFrame):
    engine = create_engine(db_conn_str, future=True)
    for stocks_row in stocks_df.to_dict('records'):
        stmt = insert(stocks_table).values(**stocks_row)
        with engine.connect() as conn:
            conn.execute(stmt)
            conn.commit()    


def update_market_capacity(db_conn_str: str, markets_table: Table, market: str, capacity: float) -> None:
    engine = create_engine(db_conn_str, future=True)
    stmt = update(markets_table).where(markets_table.c.name == market)
    stmt = stmt.values(capacity=capacity)
    with engine.connect() as conn:
        conn.execute(stmt)
        conn.commit()


def make_auto_green_investment(
    db_conn_str: str,
    investments_df: pd.DataFrame,
    prev_investments_df: pd.DataFrame,
    cycle: int,
    investments_table: Table,
):
    engine = create_engine(db_conn_str, future=True)
    last_green_markets = prev_investments_df[prev_investments_df['income'] > 0].groupby('uid')['market'].apply(set).reset_index()
    current_investments = investments_df[investments_df['status'] == 1].groupby('uid')['market'].apply(set).reset_index()
    if current_investments.empty:
        merged_info = last_green_markets.copy()
        merged_info['market_prev'] = merged_info['market']
        merged_info['market'] = [set()] * len(merged_info)
    else:
        merged_info = pd.merge(last_green_markets, current_investments, on='uid', suffixes=('_prev', ''))
    uids = merged_info['uid'].tolist()
    for uid in uids:
        lost_green_markets = merged_info.loc[merged_info['uid'] == uid, 'market_prev'].item() - merged_info.loc[merged_info['uid'] == uid, 'market'].item()
        lost_green_markets = list(lost_green_markets)
        for lost_market in lost_green_markets:
            stmt = insert(investments_table).values(
                uid=uid,
                market=lost_market,
                amount=1000000,
                timestamp_created=datetime.now() - timedelta(minutes=1),
                timestamp_approved=datetime.now() - timedelta(minutes=1),
                status=1,
                cycle=cycle,
            )
            with engine.connect() as conn:
                conn.execute(stmt)
                conn.commit()


def finish_cycle(
    db_conn_str: str,
    investments_df: pd.DataFrame,
    markets_df: pd.DataFrame,
    stocks_df: pd.DataFrame,
    users_df: pd.DataFrame,
    fund_speed: float,
    cycle: int,
    investments_table: Table,
    markets_table: Table,
    transactions_table: Table,
    stocks_table: Table,
):
    cycle_investments_calculation = calculate_investments(investments_df, markets_df, fund_speed)
    if cycle_investments_calculation is not None:
        market_incomes, market_capacities = cycle_investments_calculation
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
            transaction = Transaction(from_=from_, to_=to_, amount=abs(invest_income['income']), cycle=cycle)
            make_transaction(db_conn_str, transactions_table, transaction)
    else:
        market_incomes = None
    new_stocks = generate_stocks(market_incomes, stocks_df, users_df, cycle)
    make_stocks(db_conn_str, stocks_table, new_stocks)


def reinit_game(
    db_conn_str: str,
    users_df: pd.DataFrame,
    markets_table: Table,
    stocks_table: Table,
    transactions_table: Table,
):
    for market, start_capacity in START_CAPATICY.items():
        update_market_capacity(db_conn_str, markets_table, market, start_capacity)

    for uid in users_df['uid'].tolist():
        make_transaction(
            db_conn_str,
            transactions_table,
            Transaction(from_='root', to_=uid, amount=START_BALANCE, cycle=-1),
        )

    start_incomes = []
    for uid, start_bonus in START_BONUSES.items():
        start_incomes.append({'uid': uid, 'income': start_bonus})
        if start_bonus > 0:
            make_transaction(db_conn_str, transactions_table, Transaction(from_='root', to_=uid, amount=start_bonus, cycle=0))
    stocks_df = pd.DataFrame({'ticket': users_df['ticket'], 'price': INIT_STOCK, 'cycle': 0})
    new_stocks = generate_stocks(start_incomes, stocks_df, users_df, cycle=0)
    make_stocks(db_conn_str, stocks_table, pd.concat([stocks_df, new_stocks]))
