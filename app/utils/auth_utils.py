import importlib
from threading import Thread
from fastapi import Request
from starlette.responses import RedirectResponse
from ..web.frontend import templates
from .session import get_session_expiry_time, set_session_login_time
from .logging import logger
from ..db.auth_db import upsert_auth, get_feed_token as db_get_feed_token
from ..db.master_contract_status_db import init_broker_status, update_status


def mask_api_credential(credential, show_chars=4):
    """
    Mask API credentials for display purposes, showing only the first few characters.
    
    Args:
        credential (str): The credential to mask
        show_chars (int): Number of characters to show from the beginning
    
    Returns:
        str: Masked credential string
    """
    if not credential or len(credential) <= show_chars:
        return '*' * 8  # Return generic mask for short/empty credentials
    
    return credential[:show_chars] + '*' * (len(credential) - show_chars)

def async_master_contract_download(broker):
    """
    Asynchronously download the master contract and emit a WebSocket event upon completion,
    with the 'broker' parameter specifying the broker for which to download the contract.
    """
    # Update status to downloading
    update_status(broker, 'downloading', 'Master contract download in progress')
    
    # Dynamically construct the module path based on the broker
    module_path = f'broker.{broker}.database.master_contract_db'
    
    # Dynamically import the module
    try:
        master_contract_module = importlib.import_module(module_path)
    except ImportError as error:
        logger.error(f"Error importing {module_path}: {error}")
        update_status(broker, 'error', f'Failed to import master contract module: {str(error)}')
        return {'status': 'error', 'message': 'Failed to import master contract module'}

    # Use the dynamically imported module's master_contract_download function
    try:
        master_contract_status = master_contract_module.master_contract_download()
        
        # Most brokers return the socketio.emit result, we need to check completion
        # by looking at the module's actual completion
        
        # Try to get the symbol count from the database
        try:
            from database.token_db import get_symbol_count
            total_symbols = get_symbol_count()
        except:
            total_symbols = None
            
        # Since socketio.emit doesn't return a meaningful value, we check if no exception was raised
        update_status(broker, 'success', 'Master contract download completed successfully', total_symbols)
        logger.info(f"Master contract download completed for {broker}")
        
        # Load symbols into memory cache after successful download
        try:
            from database.master_contract_cache_hook import hook_into_master_contract_download
            logger.info(f"Loading symbols into memory cache for broker: {broker}")
            hook_into_master_contract_download(broker)
        except Exception as cache_error:
            logger.error(f"Failed to load symbols into cache: {cache_error}")
            # Don't fail the whole process if cache loading fails
            
    except Exception as e:
        logger.error(f"Error during master contract download for {broker}: {str(e)}")
        update_status(broker, 'error', f'Master contract download error: {str(e)}')
        return {'status': 'error', 'message': str(e)}
    
    logger.info("Master Contract Database Processing Completed")
    
    return master_contract_status

async def handle_auth_success(request: Request, db, auth_token, user_session_key, broker, feed_token=None, user_id=None):
    """
    Handles common tasks after successful authentication.
    - Sets session parameters
    - Stores auth token in the database
    - Initiates asynchronous master contract download
    """
    # Set session parameters
    request.session['logged_in'] = True
    request.session['AUTH_TOKEN'] = auth_token
    if feed_token:
        request.session['FEED_TOKEN'] = feed_token
    if user_id:
        request.session['USER_ID'] = user_id
    request.session['user_session_key'] = user_session_key
    request.session['broker'] = broker
    
    # Set session expiry and login time
    set_session_login_time(request)
    
    logger.info(f"User {user_session_key} logged in successfully with broker {broker}")

    # Store auth token in database
    inserted_id = upsert_auth(db, user_session_key, auth_token, broker, feed_token=feed_token, user_id=user_id)
    if inserted_id:
        logger.info(f"Database record upserted with ID: {inserted_id}")
        # Initialize master contract status for this broker
        init_broker_status(broker)
        thread = Thread(target=async_master_contract_download, args=(broker,))
        thread.start()
        return RedirectResponse(url='/dashboard', status_code=302)
    else:
        logger.error(f"Failed to upsert auth token for user {user_session_key}")
        return templates.TemplateResponse('broker.html', {"request": request, "error_message": "Failed to store authentication token. Please try again."})

async def handle_auth_failure(request: Request, error_message, forward_url='broker.html'):
    """
    Handles common tasks after failed authentication.
    """
    logger.error(f"Authentication error: {error_message}")
    return templates.TemplateResponse(forward_url, {"request": request, "error_message": error_message})

def get_feed_token(request: Request):
    """
    Get the feed token from session or database.
    Returns None if feed token doesn't exist or broker doesn't support it.
    """
    if 'FEED_TOKEN' in request.session:
        return request.session['FEED_TOKEN']
    
    # If not in session but user is logged in, try to get from database
    if 'logged_in' in request.session and request.session['logged_in'] and 'user_session_key' in request.session:
        return db_get_feed_token(request.session['user_session_key'])
    
    return None
