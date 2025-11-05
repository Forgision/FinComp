#database/master_contract_db.py

import gzip
import shutil
import os

import pandas as pd
import requests
from sqlalchemy import Float, Index, Integer, Sequence, String, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.core.schemas import get_db
from app.utils.logging import logger
from app.utils.web.socketio import socketio  # Import SocketIO


class Base(DeclarativeBase):
    pass


class SymToken(Base):
    __tablename__ = 'symtoken'
    id: Mapped[int] = mapped_column(Integer, Sequence('symtoken_id_seq'), primary_key=True)
    symbol: Mapped[str] = mapped_column(String, nullable=False, index=True)  # Single column index
    brsymbol: Mapped[str] = mapped_column(String, nullable=False, index=True)  # Single column index
    name: Mapped[str] = mapped_column(String)
    exchange: Mapped[str] = mapped_column(String, index=True)  # Include this column in a composite index
    brexchange: Mapped[str] = mapped_column(String, index=True)
    token: Mapped[str] = mapped_column(String, index=True)  # Indexed for performance
    expiry: Mapped[str] = mapped_column(String)
    strike: Mapped[float] = mapped_column(Float)
    lotsize: Mapped[int] = mapped_column(Integer)
    instrumenttype: Mapped[str] = mapped_column(String)
    tick_size: Mapped[float] = mapped_column(Float)

    # Define a composite index on symbol and exchange columns
    __table_args__ = (Index('idx_symbol_exchange', 'symbol', 'exchange'),)

def init_db():
    db = next(get_db())
    logger.info("Initializing Master Contract DB")
    Base.metadata.create_all(bind=db.get_bind())

def delete_symtoken_table():
    db = next(get_db())
    logger.info("Deleting Symtoken Table")
    db.query(SymToken).delete()
    db.commit()

def copy_from_dataframe(df):
    db = next(get_db())
    logger.info("Performing Bulk Insert")
    # Convert DataFrame to a list of dictionaries
    data_dict = df.to_dict(orient='records')

    # Retrieve existing tokens to filter them out from the insert
    existing_tokens = {result.token for result in db.execute(select(SymToken.token)).scalars().all()}

    # Filter out data_dict entries with tokens that already exist
    filtered_data_dict = [row for row in data_dict if row['token'] not in existing_tokens]

    # Insert in bulk the filtered records
    try:
        if filtered_data_dict:  # Proceed only if there's anything to insert
            db.bulk_insert_mappings(SymToken, filtered_data_dict)
            db.commit()
            logger.info(f"Bulk insert completed successfully with {len(filtered_data_dict)} new records.")
        else:
            logger.info("No new records to insert.")
    except Exception as e:
        logger.error(f"Error during bulk insert: {e}")
        db.rollback()


def download_and_unzip_upstox_data(url, input_path, output_path):
    """
    Downloads the compressed JSON from Upstox, unzips it, and saves it to the specified path.
    """
    logger.info("Downloading Upstox Master Contract")
    response = requests.get(url, timeout=10)  # timeout after 10 seconds
    with open(input_path, 'wb') as f:
        f.write(response.content)
    logger.info("Decompressing the JSON file")
    with gzip.open(input_path, 'rt', encoding='utf-8') as f_in:
        with open(output_path, 'w', encoding='utf-8') as f_out:
            shutil.copyfileobj(f_in, f_out)


def reformat_symbol(row):
    symbol = row['symbol']
    instrument_type = row['instrumenttype']

    if instrument_type == 'FUT':
        # For FUT, remove the spaces and append 'FUT' at the end
        parts = symbol.split(' ')
        if len(parts) == 5:  # Make sure the symbol has the correct format
            symbol = parts[0] + parts[2] + parts[3] + parts[4] + parts[1]
    elif instrument_type in ['CE', 'PE']:
        # For CE/PE, rearrange the parts and remove spaces
        parts = symbol.split(' ')
        if len(parts) == 6:  # Make sure the symbol has the correct format
            symbol = parts[0] + parts[3] + parts[4] + parts[5] + parts[1] + parts[2]
    else:
        symbol = symbol  # No change for other instrument types

    return symbol


def process_upstox_json(path):
    """
    Processes the Upstox JSON file to fit the existing database schema and performs exchange name mapping.
    """
    logger.info("Processing Upstox Data")
    df = pd.read_json(path)

    # Filter out NSE_COM instruments
    df = df[df['segment'] != 'NSE_COM']

    #return df

    # Assume your JSON structure requires some transformations to match your schema
    # For the sake of this example, let's assume 'df' now represents your transformed DataFrame
    # Map exchange names
    exchange_map = {
        "NSE_EQ": "NSE",
        "NSE_FO": "NFO",
        "NCD_FO": "CDS",
        "NSE_INDEX": "NSE_INDEX",
        "BSE_INDEX": "BSE_INDEX",
        "BSE_EQ": "BSE",
        "BSE_FO": "BFO",
        "BCD_FO": "BCD",
        "MCX_FO": "MCX"

    }
    segment_copy = df['segment'].copy()
    df['segment'] = df['segment'].map(exchange_map)
    df['expiry'] = pd.to_datetime(df['expiry'], unit='ms').dt.strftime('%d-%b-%y').str.upper()


    df = df[['instrument_key', 'trading_symbol', 'name', 'expiry',
                       'strike_price', 'lot_size', 'instrument_type', 'segment',
                       'tick_size']].rename(columns={
    'instrument_key': 'token',
    'trading_symbol': 'symbol',
    'name': 'name',
    'expiry': 'expiry',
    'strike_price': 'strike',
    'lot_size': 'lotsize',
    'instrument_type': 'instrumenttype',
    'segment': 'exchange',
    'tick_size': 'tick_size'
    })

    df['brsymbol'] =  df['symbol']
    df['symbol'] = df.apply(reformat_symbol, axis=1)
    df['brexchange'] = segment_copy

    df['symbol'] = df['symbol'].replace({'INDIA VIX': 'INDIAVIX'})


    return df




def delete_upstox_temp_data(input_path, output_path):
    try:
        # Check if the file exists
        if os.path.exists(input_path) and os.path.exists(output_path):
            # Delete the file
            os.remove(input_path)
            os.remove(output_path)
            logger.info(f"The temporary file {input_path} and {output_path} has been deleted.")
        else:
            logger.info(f"The temporary file {input_path} and {output_path} does not exist.")
    except Exception as e:
        logger.error(f"An error occurred while deleting the file: {e}")




def master_contract_download():
    logger.info("Downloading Master Contract")
    url = 'https://assets.upstox.com/market-quote/instruments/exchange/complete.json.gz'
    input_path = 'tmp/temp_upstox.json.gz'
    output_path = 'tmp/upstox.json'
    try:
        download_and_unzip_upstox_data(url, input_path, output_path)
        token_df = process_upstox_json(output_path)
        delete_upstox_temp_data(input_path, output_path)
        #token_df['token'] = pd.to_numeric(token_df['token'], errors='coerce').fillna(-1).astype(int)

        #token_df = token_df.drop_duplicates(subset='symbol', keep='first')

        delete_symtoken_table()  # Consider the implications of this action
        copy_from_dataframe(token_df)

        return socketio.emit('master_contract_download', {'status': 'success', 'message': 'Successfully Downloaded'})


    except Exception as e:
        logger.info(f"{str(e)}")
        return socketio.emit('master_contract_download', {'status': 'error', 'message': str(e)})



def search_symbols(symbol, exchange):
    db = next(get_db())
    return db.query(SymToken).filter(SymToken.symbol.like(f'%{symbol}%'), SymToken.exchange == exchange).all()
