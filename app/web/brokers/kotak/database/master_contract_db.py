#database/master_contract_db.py

import http.client
import json
import os

import pandas as pd
import requests
from app.core.models.auth_db import get_auth_token
from sqlmodel import SQLModel, Field, Session, create_engine, select
from sqlalchemy import Index

from app.core.config import settings
from app.db.session import get_db, engine
from app.utils.logging import logger
from app.utils.web.socketio import socketio  # Import SocketIO

class SymToken(SQLModel, table=True):
    __tablename__ = 'symtoken'
    id: int = Field(default=None, primary_key=True)
    symbol: str = Field(nullable=False, index=True)
    brsymbol: str = Field(nullable=False, index=True)
    name: str
    exchange: str = Field(index=True)
    brexchange: str = Field(index=True)
    token: str = Field(index=True)
    expiry: str
    strike: float
    lotsize: int
    instrumenttype: str
    tick_size: float

    __table_args__ = (Index('idx_symbol_exchange', 'symbol', 'exchange'),)

def init_db():
    logger.info("Initializing Master Contract DB")
    SQLModel.metadata.create_all(bind=engine)

def delete_symtoken_table():
    with Session(engine) as session:
        logger.info("Deleting Symtoken Table")
        session.query(SymToken).delete()
        session.commit()

def copy_from_dataframe(df):
    with Session(engine) as session:
        logger.info("Performing Bulk Insert")
        data_dict = df.to_dict(orient='records')
        existing_tokens = {result.token for result in session.exec(select(SymToken.token)).all()}
        filtered_data_dict = [row for row in data_dict if row['token'] not in existing_tokens]
        try:
            if filtered_data_dict:
                session.bulk_insert_mappings(SymToken, filtered_data_dict)
                session.commit()
                logger.info(f"Bulk insert completed successfully with {len(filtered_data_dict)} new records.")
            else:
                logger.info("No new records to insert.")
        except Exception as e:
            logger.error(f"Error during bulk insert: {e}")
            session.rollback()

def download_csv_kotak_data(output_path):

    logger.info("Downloading Master Contract CSV Files")
    # URLs of the CSV files to be downloaded
    csv_urls = get_kotak_master_filepaths()
    logger.info(f"Master contract URLs: {csv_urls}")
    # Create a list to hold the paths of the downloaded files
    downloaded_files = []

    # Iterate through the URLs and download the CSV files
    for key, url in csv_urls.items():
        # Send GET request
        response = requests.get(url,timeout=10)
        # Check if the request was successful
        if response.status_code == 200:
            # Construct the full output path for the file
            file_path = f"{output_path}/{key}.csv"
            # Write the content to the file
            with open(file_path, 'wb') as file:
                file.write(response.content)
            downloaded_files.append(file_path)
        else:
            logger.error(f"Failed to download {key} from {url}. Status code: {response.status_code}")


def process_kotak_nse_csv(path):
    """
    Processes the kotak CSV file to fit the existing database schema and performs exchange name mapping.
    """
    logger.info("Processing kotak NSE CSV Data")
    file_path = f'{path}/NSE_CM.csv'

    df = pd.read_csv(file_path)


    filtereddataframe = pd.DataFrame()

    filtereddataframe['token'] = df['pSymbol']
    filtereddataframe['name'] = df['pDesc']
    filtereddataframe['expiry'] = df['pExpiryDate']
    filtereddataframe['strike'] = df['dStrikePrice;']
    filtereddataframe['lotsize'] = df['lLotSize']
    filtereddataframe['tick_size'] = df['dTickSize ']
    filtereddataframe['brsymbol'] = df['pTrdSymbol']
    filtereddataframe['symbol'] = df['pSymbolName']

    # Filtering the DataFrame based on 'Exchange Instrument type' and assigning values to 'exchange'

    df.loc[df['pGroup'].isin(['EQ', 'BE']), 'instrumenttype'] = 'EQ'
    df.loc[df['pISIN'].isna(), 'exchange'] = 'NSE_INDEX'
    df.loc[df['pGroup'].isin(['EQ', 'BE']), 'exchange'] = 'NSE'
    df.loc[df['pISIN'].isna(), 'instrumenttype'] = 'INDEX'
    df.loc[df['pISIN'].isna(), 'pGroup'] = ''

    filtereddataframe['instrumenttype'] = df['instrumenttype']
    filtereddataframe['exchange'] = df['exchange']
    filtereddataframe['pGroup'] = df['pGroup']

    # Keeping only rows where 'exchange' column has been filled ('NSE' or 'NSE_INDEX')
    df_filtered = filtereddataframe[filtereddataframe['pGroup'].isin(['EQ', 'BE', ''])].copy()

    df_filtered['brexchange'] = 'NSE'

    # List of columns to remove
    columns_to_remove = [
        "pGroup"
    ]

    # Removing the specified columns
    token_df = df_filtered.drop(columns=columns_to_remove)

    return token_df

def process_kotak_bse_csv(path):
    """
    Processes the kotak CSV file to fit the existing database schema and performs exchange name mapping.
    """
    logger.info("Processing kotak BSE CSV Data")
    file_path = f'{path}/BSE_CM.csv'

    df = pd.read_csv(file_path)
    df.columns = df.columns.str.replace(' ', '')
    df.columns = df.columns.str.replace(';', '')
    df.dropna(subset=['pSymbolName'], inplace=True)

    filtereddataframe = pd.DataFrame()

    filtereddataframe['token'] = df['pSymbol']
    filtereddataframe['name'] = df['pDesc']
    filtereddataframe['expiry'] = df['pExpiryDate']
    filtereddataframe['strike'] = df['dStrikePrice']
    filtereddataframe['lotsize'] = df['lLotSize']
    filtereddataframe['tick_size'] = df['dTickSize']
    filtereddataframe['brsymbol'] = df['pTrdSymbol']
    filtereddataframe['symbol'] = df['pSymbolName']

    # Filtering the DataFrame based on 'Exchange Instrument type' and assigning values to 'exchange'

    df['instrumenttype'] = 'EQ'

    df['exchange'] = 'BSE'
    df.loc[df['pISIN'].isna(), 'exchange'] = 'BSE_INDEX'
    df.loc[df['pISIN'].isna(), 'instrumenttype'] = 'INDEX'
    df.loc[df['pISIN'].isna(), 'pGroup'] = ''

    filtereddataframe['instrumenttype'] = df['instrumenttype']
    filtereddataframe['exchange'] = df['exchange']
    filtereddataframe['pGroup'] = df['pGroup']

    # Keeping only rows where 'exchange' column has been filled ('NSE' or 'NSE_INDEX')
    df_filtered = filtereddataframe.copy()

    df_filtered['brexchange'] = 'BSE'

    # List of columns to remove
    columns_to_remove = [
        "pGroup"
    ]

    # Removing the specified columns
    token_df = df_filtered.drop(columns=columns_to_remove)

    return token_df

def combine_details(row):
    base = f"{row['name']}{row['expiry'].replace('-', '')}"
    if row['instrumenttype'] == 'FUT':
        return f"{base}FUT"
    elif row['instrumenttype'] in ['CE', 'PE']:
        row['strike'] = int(row['strike']) if row['strike'].is_integer() else row['strike']
        return f"{base}{row['strike']}{row['instrumenttype']}"
    else:
        return base

def process_kotak_nfo_csv(path):
    """
    Processes the kotak CSV file to fit the existing database schema and performs exchange name mapping.
    """
    logger.info("Processing kotak NFO CSV Data")
    file_path = f'{path}/NSE_FO.csv'

    df = pd.read_csv(file_path, dtype={'pOptionType': 'str'})
    df.columns = df.columns.str.replace(' ', '')
    df.columns = df.columns.str.replace(';', '')
    tokensymbols = pd.DataFrame()
    tokensymbols['token'] = df['pSymbol']
    tokensymbols['name'] = df['pSymbolName']
    df['lExpiryDate'] = df['lExpiryDate']+315513000

    # Convert 'Expiry date' from Unix timestamp to datetime
    tokensymbols['expiry'] = pd.to_datetime(df['lExpiryDate'], unit='s')

    # Format the datetime object to the desired format '15-APR-24'
    tokensymbols['expiry'] = tokensymbols['expiry'].dt.strftime('%d-%b-%y').str.upper()

    tokensymbols['strike'] = df['dStrikePrice']/100
    tokensymbols['strike'] = tokensymbols['strike'].apply(lambda x: int(x) if x.is_integer() else x)

    tokensymbols['lotsize'] = df['lLotSize']
    tokensymbols['tick_size'] = df['dTickSize']
    tokensymbols['brsymbol'] = df['pTrdSymbol']
    tokensymbols['brexchange'] = df['pExchSeg']
    tokensymbols['exchange'] = 'NFO'

    #df1['instrumenttype'] = df['pOptionType'].apply(lambda x: x.replace('XX', 'FUT'))
    tokensymbols['instrumenttype'] = df['pOptionType'].str.replace('XX','FUT')

    #pSymbolName  df['expiry']
    tokensymbols['symbol'] = tokensymbols.apply(combine_details, axis=1)
    return tokensymbols

def get_kotak_master_filepaths():
    login_username = settings.API_CLIENT
    if not login_username:
        logger.error("API_CLIENT not set in settings.")
        socketio.emit('master_contract_download', {'status': 'error', 'message': 'API_CLIENT not set in settings.'})
        return {}

    auth_token = get_auth_token(login_username)
    if not auth_token:
        logger.error(f"Auth token not found for user: {login_username}")
        socketio.emit('master_contract_download', {'status': 'error', 'message': f'Auth token not found for user: {login_username}'})
        return {}

    access_token_parts = auth_token.split(":::")
    access_token = access_token_parts[3]
    conn = http.client.HTTPSConnection("gw-napi.kotaksecurities.com")
    payload = ''
    headers = {
    'accept': '*/*',
    'Authorization': f'Bearer {access_token}'
    }
    conn.request("GET", "/Files/1.0/masterscrip/v2/file-paths", payload, headers)
    res = conn.getresponse()

    data = res.read().decode("utf-8")
    data_dict = json.loads(data)

    filepaths_list = data_dict['data']['filesPaths']
    file_dict = {}
    for url in filepaths_list:
        file_name = url.split('/')[-1].upper().replace('.CSV', '').replace('-V1', '')
        file_dict[file_name] = url

    return file_dict


def process_kotak_cds_csv(path):
    """
    Processes the kotak CSV file to fit the existing database schema and performs exchange name mapping.
    """
    logger.info("Processing kotak CDS CSV Data")
    file_path = f'{path}/CDE_FO.csv'

    df = pd.read_csv(file_path, dtype={'pOptionType': 'str'})
    df.columns = df.columns.str.replace(' ', '')
    df.columns = df.columns.str.replace(';', '')
    tokensymbols = pd.DataFrame()
    tokensymbols['token'] = df['pSymbol']
    tokensymbols['name'] = df['pSymbolName']
    df['lExpiryDate'] = df['lExpiryDate']+315513000

    # Convert 'Expiry date' from Unix timestamp to datetime
    tokensymbols['expiry'] = pd.to_datetime(df['lExpiryDate'], unit='s')

    # Format the datetime object to the desired format '15-APR-24'
    tokensymbols['expiry'] = tokensymbols['expiry'].dt.strftime('%d-%b-%y').str.upper()

    tokensymbols['strike'] = df['dStrikePrice']/100
    tokensymbols['strike'] = tokensymbols['strike'].apply(lambda x: int(x) if x.is_integer() else x)

    tokensymbols['lotsize'] = df['lLotSize']
    tokensymbols['tick_size'] = df['dTickSize']
    tokensymbols['brsymbol'] = df['pTrdSymbol']
    tokensymbols['brexchange'] = df['pExchSeg']
    tokensymbols['exchange'] = 'CDS'



    #df1['instrumenttype'] = df['pOptionType'].apply(lambda x: x.replace('XX', 'FUT'))
    tokensymbols['instrumenttype'] = df['pOptionType'].str.replace('XX','FUT')

    #pSymbolName  df['expiry']
    tokensymbols['symbol'] = tokensymbols.apply(combine_details, axis=1)
    return tokensymbols


def process_kotak_mcx_csv(path):
    """
    Processes the kotak CSV file to fit the existing database schema and performs exchange name mapping.
    """
    logger.info("Processing kotak MCX CSV Data")
    file_path = f'{path}/MCX_FO.csv'

    df = pd.read_csv(file_path, dtype={'pOptionType': 'str'})
    df.columns = df.columns.str.replace(' ', '')
    df.columns = df.columns.str.replace(';', '')
    df.dropna(subset=['pOptionType'], inplace=True)
    tokensymbols = pd.DataFrame()
    tokensymbols['token'] = df['pSymbol']
    tokensymbols['name'] = df['pSymbolName']
    df['lExpiryDate'] = df['lExpiryDate']

    # Convert 'Expiry date' from Unix timestamp to datetime
    tokensymbols['expiry'] = pd.to_datetime(df['lExpiryDate'], unit='s')

    # Format the datetime object to the desired format '15-APR-24'
    tokensymbols['expiry'] = tokensymbols['expiry'].dt.strftime('%d-%b-%y').str.upper()

    tokensymbols['strike'] = df['dStrikePrice']/100
    tokensymbols['strike'] = tokensymbols['strike'].apply(lambda x: int(x) if x.is_integer() else x)

    tokensymbols['lotsize'] = df['lLotSize']
    tokensymbols['tick_size'] = df['dTickSize']
    tokensymbols['brsymbol'] = df['pTrdSymbol']
    tokensymbols['brexchange'] = df['pExchSeg']
    tokensymbols['exchange'] = 'MCX'



    #df1['instrumenttype'] = df['pOptionType'].apply(lambda x: x.replace('XX', 'FUT'))
    tokensymbols['instrumenttype'] = df['pOptionType'].str.replace('XX','FUT')

    #pSymbolName  df['expiry']
    tokensymbols['symbol'] = tokensymbols.apply(combine_details, axis=1)
    return tokensymbols


def process_kotak_bfo_csv(path):
    """
    Processes the kotak CSV file to fit the existing database schema and performs exchange name mapping.
    """
    logger.info("Processing kotak BFO CSV Data")
    file_path = f'{path}/BSE_FO.csv'

    df = pd.read_csv(file_path, dtype={'pOptionType': 'str'})
    df.columns = df.columns.str.replace(' ', '')
    df.columns = df.columns.str.replace(';', '')
    df.dropna(subset=['pOptionType'], inplace=True)
    tokensymbols = pd.DataFrame()
    tokensymbols['token'] = df['pSymbol']
    tokensymbols['name'] = df['pSymbolName']
    df['lExpiryDate'] = df['lExpiryDate']

    # Convert 'Expiry date' from Unix timestamp to datetime
    tokensymbols['expiry'] = pd.to_datetime(df['lExpiryDate'], unit='s')

    # Format the datetime object to the desired format '15-APR-24'
    tokensymbols['expiry'] = tokensymbols['expiry'].dt.strftime('%d-%b-%y').str.upper()

    tokensymbols['strike'] = df['dStrikePrice']/100
    tokensymbols['strike'] = tokensymbols['strike'].apply(lambda x: int(x) if x.is_integer() else x)

    tokensymbols['lotsize'] = df['lLotSize']
    tokensymbols['tick_size'] = df['dTickSize']
    tokensymbols['brsymbol'] = df['pTrdSymbol']
    tokensymbols['brexchange'] = df['pExchSeg']
    tokensymbols['exchange'] = 'BFO'



    #df1['instrumenttype'] = df['pOptionType'].apply(lambda x: x.replace('XX', 'FUT'))
    tokensymbols['instrumenttype'] = df['pOptionType'].str.replace('XX','FUT')

    #pSymbolName  df['expiry']
    tokensymbols['symbol'] = tokensymbols.apply(combine_details, axis=1)
    return tokensymbols

def delete_kotak_temp_data(output_path):
    # Check each file in the directory
    for filename in os.listdir(output_path):
        # Construct the full file path
        file_path = os.path.join(output_path, filename)
        # If the file is a CSV, delete it
        if filename.endswith(".csv") and os.path.isfile(file_path):
            os.remove(file_path)
            logger.info(f"Deleted {file_path}")

def master_contract_download():
    logger.info("Downloading Master Contract")

    output_path = 'tmp'
    try:
        download_csv_kotak_data(output_path)
        delete_symtoken_table()
        token_df = process_kotak_nse_csv(output_path)
        copy_from_dataframe(token_df)
        token_df = process_kotak_nfo_csv(output_path)
        copy_from_dataframe(token_df)
        token_df = process_kotak_bse_csv(output_path)
        copy_from_dataframe(token_df)
        token_df = process_kotak_cds_csv(output_path)
        copy_from_dataframe(token_df)
        token_df = process_kotak_mcx_csv(output_path)
        copy_from_dataframe(token_df)
        token_df = process_kotak_bfo_csv(output_path)
        copy_from_dataframe(token_df)
        delete_kotak_temp_data(output_path)
        #token_df['token'] = pd.to_numeric(token_df['token'], errors='coerce').fillna(-1).astype(int)

        #token_df = token_df.drop_duplicates(subset='symbol', keep='first')

        return socketio.emit('master_contract_download', {'status': 'success', 'message': 'Successfully Downloaded'})


    except Exception as e:
        logger.info(f"{str(e)}")
        return socketio.emit('master_contract_download', {'status': 'error', 'message': str(e)})



def search_symbols(symbol, exchange):
    with Session(engine) as session:
        statement = select(SymToken).where(SymToken.symbol.like(f'%{symbol}%')).where(SymToken.exchange == exchange)
        return session.exec(statement).all()
