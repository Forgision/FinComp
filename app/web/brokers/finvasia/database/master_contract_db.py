import io
import zipfile
from pathlib import Path

import pandas as pd
import requests
from sqlalchemy import Float, Index, Integer, Sequence, String, select
from sqlalchemy.orm import (DeclarativeBase, Mapped, mapped_column)

from app.core.schemas import get_db
from app.utils.logging import logger
from app.utils.web.socketio import socketio

class Base(DeclarativeBase):
    pass

class SymToken(Base):
    __tablename__ = 'symtoken'
    id: Mapped[int] = mapped_column(Integer, Sequence('symtoken_id_seq'), primary_key=True)
    symbol: Mapped[str] = mapped_column(String, nullable=False, index=True)
    brsymbol: Mapped[str] = mapped_column(String, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String, nullable=True)
    exchange: Mapped[str] = mapped_column(String, index=True)
    brexchange: Mapped[str] = mapped_column(String, index=True)
    token: Mapped[str] = mapped_column(String, index=True)
    expiry: Mapped[str] = mapped_column(String, nullable=True)
    strike: Mapped[float] = mapped_column(Float, nullable=True)
    lotsize: Mapped[int] = mapped_column(Integer, nullable=True)
    instrumenttype: Mapped[str] = mapped_column(String, nullable=True)
    tick_size: Mapped[float] = mapped_column(Float, nullable=True)
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
    data_dict = df.to_dict(orient='records')
    stmt = select(SymToken.token, SymToken.exchange)
    existing_token_exchange = {(result.token, result.exchange) for result in db.execute(stmt).all()}
    filtered_data_dict = [row for row in data_dict if (row['token'], row['exchange']) not in existing_token_exchange]
    try:
        if filtered_data_dict:
            db.bulk_insert_mappings(SymToken, filtered_data_dict)
            db.commit()
            logger.info(f"Bulk insert completed successfully with {len(filtered_data_dict)} new records.")
        else:
            logger.info("No new records to insert.")
    except Exception as e:
        logger.error(f"Error during bulk insert: {e}")
        db.rollback()

finvasia_urls = {
    "NSE": "https://api.finvasia.com/NSE_symbols.txt.zip",
    "NFO": "https://api.finvasia.com/NFO_symbols.txt.zip",
    "CDS": "https://api.finvasia.com/CDS_symbols.txt.zip",
    "MCX": "https://api.finvasia.com/MCX_symbols.txt.zip",
    "BSE": "https://api.finvasia.com/BSE_symbols.txt.zip",
    "BFO": "https://api.finvasia.com/BFO_symbols.txt.zip"
}

def download_and_unzip_finvasia_data(output_path):
    """
    NOTE: This is a placeholder implementation.
    """
    logger.info("Downloading and Unzipping Finvasia Data")
    output_path_obj = Path(output_path)
    if not output_path_obj.exists():
        output_path_obj.mkdir(parents=True, exist_ok=True)
    downloaded_files = []
    for key, url in finvasia_urls.items():
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                logger.info(f"Successfully downloaded {key} from {url}")
                z = zipfile.ZipFile(io.BytesIO(response.content))
                z.extractall(output_path)
                downloaded_files.append(f"{key}.txt")
            else:
                logger.error(f"Failed to download {key} from {url}. Status code: {response.status_code}")
        except Exception as e:
            logger.error(f"Error downloading {key} from {url}: {e}")
    return downloaded_files

def process_finvasia_nse_data(output_path):
    """
    NOTE: This is a placeholder implementation.
    """
    logger.info("Processing Finvasia NSE Data")
    file_path = f'{output_path}/NSE_symbols.txt'
    df = pd.read_csv(file_path, usecols=['Exchange', 'Token', 'LotSize', 'Symbol', 'TradingSymbol', 'Instrument', 'TickSize'])
    df.columns = ['exchange', 'token', 'lotsize', 'name', 'brsymbol', 'instrumenttype', 'tick_size']
    df['symbol'] = df['brsymbol']
    def get_openalgo_symbol(broker_symbol):
        if '-EQ' in broker_symbol:
            return broker_symbol.replace('-EQ', '')
        elif '-BE' in broker_symbol:
            return broker_symbol.replace('-BE', '')
        else:
            return broker_symbol
    df['symbol'] = df['brsymbol'].apply(get_openalgo_symbol)
    df['exchange'] = df.apply(lambda row: 'NSE_INDEX' if row['instrumenttype'] == 'INDEX' else 'NSE', axis=1)
    df['brexchange'] = df['exchange']
    df['expiry'] = ''
    df['strike'] = -1
    df['instrumenttype'] = df['instrumenttype'].apply(lambda x: 'EQ' if x in ['EQ', 'BE'] else x)
    df['lotsize'] = pd.to_numeric(df['lotsize'], errors='coerce').fillna(0).astype(int)
    df['tick_size'] = pd.to_numeric(df['tick_size'], errors='coerce').fillna(0).astype(float)
    columns_to_keep = ['symbol', 'brsymbol', 'name', 'exchange', 'brexchange', 'token', 'expiry', 'strike', 'lotsize', 'instrumenttype', 'tick_size']
    df_filtered = df[columns_to_keep]
    df_filtered['symbol'] = df_filtered['symbol'].replace({'NIFTY INDEX': 'NIFTY', 'NIFTY BANK': 'BANKNIFTY', 'MIDCPNIFTY': 'MIDCPNIFTY', 'INDIA VIX': 'INDIAVIX'})
    return df_filtered

# Similar placeholder functions for other exchanges (NFO, CDS, MCX, BSE, BFO) would go here.
# For brevity, they are omitted but would follow the same pattern as process_finvasia_nse_data.

def delete_finvasia_temp_data(output_path):
    output_path_obj = Path(output_path)
    for file_path_obj in output_path_obj.iterdir():
        if file_path_obj.suffix == ".txt" and file_path_obj.is_file():
            file_path_obj.unlink()
            logger.info(f"Deleted {file_path_obj}")

def master_contract_download():
    logger.info("Downloading Finvasia Master Contract")
    output_path = 'tmp'
    try:
        download_and_unzip_finvasia_data(output_path)
        delete_symtoken_table()
        token_df = process_finvasia_nse_data(output_path)
        copy_from_dataframe(token_df)
        # Calls to other processing functions would go here
        delete_finvasia_temp_data(output_path)
        return socketio.emit('master_contract_download', {'status': 'success', 'message': 'Successfully Downloaded'})
    except Exception as e:
        logger.info(f"{str(e)}")
        return socketio.emit('master_contract_download', {'status': 'error', 'message': str(e)})
