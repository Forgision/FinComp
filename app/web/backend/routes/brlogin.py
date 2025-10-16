from fastapi import APIRouter, Request, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from starlette.background import BackgroundTask

from app.core.config import settings
from app.web.services.auth_service import load_broker_auth_functions, handle_auth_success, handle_auth_failure
from app.web.services.limiter import limiter
from app.utils.logging import logger
from app.web.services.utils import get_httpx_client
from urllib.parse import unquote

import http.client
import json
import jwt
import base64
import hashlib

# Initialize logger

BROKER_API_KEY = settings.BROKER_API_KEY
LOGIN_RATE_LIMIT_MIN = settings.LOGIN_RATE_LIMIT_MIN
LOGIN_RATE_LIMIT_HOUR = settings.LOGIN_RATE_LIMIT_HOUR

# Initialize FastAPI Router
brlogin_router = APIRouter(prefix="/brlogin", tags=["brlogin"])

# Initialize Jinja2Templates
templates = Jinja2Templates(directory="app/web/frontend/templates")

@brlogin_router.exception_handler(429)
async def ratelimit_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={"detail": "Rate limit exceeded"}
    )

@brlogin_router.api_route('/{broker}/callback', methods=['POST','GET'])
@limiter.limit(LOGIN_RATE_LIMIT_MIN)
@limiter.limit(LOGIN_RATE_LIMIT_HOUR)
async def broker_callback(broker: str, request: Request, para: str = None):
    logger.info(f'Broker callback initiated for: {broker}')
    logger.debug(f'Session contents: {dict(request.session)}')
    logger.info(f'Session has user key: {"user" in request.session}')
    
    # Special handling for Compositedge - it comes from external OAuth and might lose session
    if broker == 'compositedge' and 'user' not in request.session:
        # For Compositedge OAuth callback, we'll handle authentication differently
        # The session will be established after successful auth token validation
        logger.info("Compositedge callback without session - will establish session after auth")
    else:
        # Check if user is not in session first for other brokers
        if 'user' not in request.session:
            logger.warning(f'User not in session for {broker} callback, redirecting to login')
            return RedirectResponse(url="/auth/login", status_code=status.HTTP_302_FOUND)

    if request.session.get('logged_in'):
        # Store broker in session and g
        request.session['broker'] = broker
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)

    broker_auth_functions = await load_broker_auth_functions()
    auth_function = broker_auth_functions.get(f'{broker}_auth')

    if not auth_function:
        return JSONResponse(content={"error": "Broker authentication function not found."}, status_code=status.HTTP_404_NOT_FOUND)
    
    # Initialize feed_token to None by default
    feed_token = None
    auth_token = None
    error_message = None
    user_id = None
    
    if broker == 'fivepaisa':
        if request.method == 'GET':
            return templates.TemplateResponse('5paisa.html', {"request": request})
        
        elif request.method == 'POST':
            form = await request.form()
            clientcode = form.get('clientid')
            broker_pin = form.get('pin')
            totp_code = form.get('totp')

            auth_token, error_message = await auth_function(clientcode, broker_pin, totp_code)
            forward_url = '5paisa.html'
        
    elif broker == 'angel':
        if request.method == 'GET':
            return templates.TemplateResponse('angel.html', {"request": request})
        
        elif request.method == 'POST':
            form = await request.form()
            clientcode = form.get('clientid')
            broker_pin = form.get('pin')
            totp_code = form.get('totp')
            #to store user_id in the DB
            user_id = clientcode
            auth_token, feed_token, error_message = await auth_function(clientcode, broker_pin, totp_code)
            forward_url = 'angel.html'
    
    elif broker == 'aliceblue':
        if request.method == 'GET':
            return templates.TemplateResponse('aliceblue.html', {"request": request})
        
        elif request.method == 'POST':
            logger.info('Aliceblue Login Flow initiated')
            form = await request.form()
            userid = form.get('userid')
            # Step 1: Get encryption key
            client = get_httpx_client()
            
            # AliceBlue API expects only userId in the encryption key request
            # Do not include API key in this initial request
            payload = {
                "userId": userid
            }
            headers = {
                'Content-Type': 'application/json'
            }
            try:
                # Get encryption key
                url = "https://ant.aliceblueonline.com/rest/AliceBlueAPIService/api/customer/getAPIEncpkey"
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                data_dict = response.json()
                logger.debug(f'Aliceblue response data: {data_dict}')
                
                # Check if we successfully got the encryption key
                if data_dict.get('stat') == 'Ok' and data_dict.get('encKey'):
                    enc_key = data_dict['encKey']
                    # Step 2: Authenticate with encryption key
                    auth_token, error_message = await auth_function(userid, enc_key)
                    
                    if auth_token:
                        return await handle_auth_success(auth_token, request.session['user'], broker)
                    else:
                        return await handle_auth_failure(error_message, forward_url='aliceblue.html', request=request)
                else:
                    # Failed to get encryption key
                    error_msg = data_dict.get('emsg', 'Failed to get encryption key')
                    return await handle_auth_failure(f"Failed to get encryption key: {error_msg}", forward_url='aliceblue.html', request=request)
            except Exception as e:
                return JSONResponse(content={"error": f"Authentication error: {str(e)}"}, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
    elif broker=='fivepaisaxts':
        code = 'fivepaisaxts'
        logger.debug(f'FivePaisaXTS broker - code: {code}')
               
        # Fetch auth token, feed token and user ID
        auth_token, feed_token, user_id, error_message = await auth_function(code)
        forward_url = 'broker.html'


    elif broker=='compositedge':
        # For Compositedge, check if we need to handle a special case where session might be lost
        if 'user' not in request.session:
            # Check if this is coming from a valid OAuth callback
            # Log the issue but try to continue if we have valid data
            logger.warning("Session 'user' key missing in Compositedge callback, attempting to recover")
            
        try:
            # Get the raw data from the request
            if request.method == 'POST':
                # Handle form data
                if request.headers.get('Content-Type') == 'application/x-www-form-urlencoded':
                    raw_data = (await request.body()).decode('utf-8')
                    
                    # Extract session data from form
                    if raw_data.startswith('session='):
                        session_data = unquote(raw_data[8:])  # Remove 'session=' and URL decode
                        
                    else:
                        session_data = raw_data
                else:
                    session_data = (await request.body()).decode('utf-8')
                
            else:
                session_data = request.query_params.get('session')
                
                
            if not session_data:
                
                return JSONResponse(content={"error": "No session data received"}, status_code=status.HTTP_400_BAD_REQUEST)

            # Parse the session data
            try:
                             
                # Try to clean the data if it's malformed
                if isinstance(session_data, str):
                    # Remove any leading/trailing whitespace
                    session_data = session_data.strip()
                    
                    session_json = json.loads(session_data)
                    
                    # Handle double-encoded JSON
                    if isinstance(session_json, str):
                        session_json = json.loads(session_json)
                        
                else:
                    session_json = session_data
                    
                    
            except json.JSONDecodeError as e:
                
                return JSONResponse(content={
                    "error": f"Invalid JSON format: {str(e)}",
                    "raw_data": session_data
                }, status_code=status.HTTP_400_BAD_REQUEST)

            # Extract access token
            access_token = session_json.get('accessToken')
            #print(f'Access token is {access_token}')
            
            if not access_token:
                
                return JSONResponse(content={"error": "No access token found"}, status_code=status.HTTP_400_BAD_REQUEST)
                
            # Fetch auth token, feed token and user ID
            auth_token, feed_token, user_id, error_message = await auth_function(access_token)

            #print(f'Auth token is {auth_token}')
            #print(f'Feed token is {feed_token}')
            #print(f'User ID is {user_id}')
            forward_url = 'broker.html'

        except Exception as e:
            #print(f"Error in compositedge callback: {str(e)}")
            return JSONResponse(content={"error": f"Error processing request: {str(e)}"}, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

    elif broker=='fyers':
        code = request.query_params.get('auth_code')
        logger.debug(f'Fyers broker - The code is {code}')
        auth_token, error_message = await auth_function(code)
        forward_url = 'broker.html'

    elif broker=='tradejini':
        if request.method == 'GET':
            return templates.TemplateResponse('tradejini.html', {"request": request})
        
        elif request.method == 'POST':
            form = await request.form()
            password = form.get('password')
            twofa = form.get('twofa')
            twofatype = form.get('twofatype')
            
            # Get auth token using individual token service
            auth_token, error_message = await auth_function(password=password, twofa=twofa, twofa_type=twofatype)
            
            if auth_token:
                return await handle_auth_success(auth_token, request.session['user'], broker)
            else:
                return templates.TemplateResponse('tradejini.html', {"request": request, "error": error_message})
        
        forward_url = 'broker.html'
       
    elif broker=='icici':
        full_url = str(request.url)
        logger.debug(f'ICICI broker - Full URL: {full_url}')
        code = request.query_params.get('apisession')
        logger.debug(f'ICICI broker - The code is {code}')
        auth_token, error_message = await auth_function(code)
        forward_url = 'broker.html'

    elif broker=='ibulls':
        code = 'ibulls'
        logger.debug(f'Indiabulls broker - code: {code}')
               
        # Fetch auth token, feed token and user ID
        auth_token, feed_token, user_id, error_message = await auth_function(code)
        forward_url = 'broker.html'

    elif broker=='iifl':
        code = 'iifl'
        logger.debug(f'IIFL broker - The code is {code}')
               
        # Fetch auth token, feed token and user ID
        auth_token, feed_token, user_id, error_message = await auth_function(code)
        forward_url = 'broker.html'

    elif broker=='dhan':
        code = 'dhan'
        logger.debug(f'Dhan broker - The code is {code}')
        auth_token, error_message = await auth_function(code)
        
        # Validate authentication by testing funds API before proceeding
        if auth_token:
            # Import the funds function to test authentication
            from app.web.broker.dhan.api.funds import test_auth_token
            is_valid, validation_error = test_auth_token(auth_token)
            
            if not is_valid:
                logger.error(f"Dhan authentication validation failed: {validation_error}")
                return await handle_auth_failure(f"Authentication validation failed: {validation_error}", forward_url='broker.html', request=request)
            
            logger.info("Dhan authentication validation successful")
        
        forward_url = 'broker.html'
    elif broker=='indmoney':
        code = 'indmoney'
        logger.debug(f'IndMoney broker - The code is {code}')
        auth_token, error_message = await auth_function(code)
        
       
        forward_url = 'broker.html'

    elif broker=='dhan_sandbox':
        code = 'dhan_sandbox'
        logger.debug(f'Dhan Sandbox broker - The code is {code}')
        auth_token, error_message = await auth_function(code)
        forward_url = 'broker.html'
        

    elif broker == 'groww':
        code = 'groww'
        logger.debug(f'Groww broker - The code is {code}')
        auth_token, error_message = await auth_function(code)
        forward_url = 'broker.html'

    elif broker == 'wisdom':
        code = 'wisdom'
        logger.debug(f'Wisdom broker - The code is {code}')
        auth_token, feed_token, user_id, error_message = await auth_function(code)
        forward_url = 'broker.html'

    elif broker == 'zebu':
        if request.method == 'GET':
            return templates.TemplateResponse('zebu.html', {"request": request})
        
        elif request.method == 'POST':
            form = await request.form()
            userid = form.get('userid')
            password = form.get('password')
            totp_code = form.get('totp')

            auth_token, error_message = await auth_function(userid, password, totp_code)
            forward_url = 'zebu.html'

    elif broker == 'shoonya':
        if request.method == 'GET':
            return templates.TemplateResponse('shoonya.html', {"request": request})
        
        elif request.method == 'POST':
            form = await request.form()
            userid = form.get('userid')
            password = form.get('password')
            totp_code = form.get('totp')

            auth_token, error_message = await auth_function(userid, password, totp_code)
            forward_url = 'shoonya.html'

    elif broker == 'firstock':
        if request.method == 'GET':
            return templates.TemplateResponse('firstock.html', {"request": request})
        
        elif request.method == 'POST':
            form = await request.form()
            userid = form.get('userid')
            password = form.get('password')
            totp_code = form.get('totp')

            auth_token, error_message = await auth_function(userid, password, totp_code)
            forward_url = 'firstock.html'

    elif broker == 'flattrade':
        code = request.query_params.get('code')
        client = request.query_params.get('client')  # Flattrade returns client ID as well
        logger.debug(f'Flattrade broker - The code is {code} for client {client}')
        auth_token, error_message = await auth_function(code)  # Only pass the code parameter
        forward_url = 'broker.html'

    elif broker=='kotak':
        logger.debug(f"Kotak broker - The Broker is {broker}")
        if request.method == 'GET':
            return templates.TemplateResponse('kotak.html', {"request": request})
        
        elif request.method == 'POST':
            form = await request.form()
            otp = form.get('otp')
            token = form.get('token')
            sid = form.get('sid')
            userid = form.get('userid')
            access_token = form.get('access_token')
            hsServerId = form.get('hsServerId')
            
            auth_token, error_message = await auth_function(otp,token,sid,userid,access_token,hsServerId)
            forward_url = 'kotak.html'

    elif broker == 'paytm':
         request_token = request.query_params.get('requestToken')
         logger.debug(f'Paytm broker - The request token is {request_token}')
         auth_token, error_message = await auth_function(request_token)
         forward_url = 'broker.html'

    elif broker == 'pocketful':
        # Handle the OAuth2 authorization code from the callback
        auth_code = request.query_params.get('code')
        state = request.query_params.get('state')
        error = request.query_params.get('error')
        error_description = request.query_params.get('error_description')
        
        # Check if there was an error in the OAuth process
        if error:
            error_msg = f"OAuth error: {error}. {error_description if error_description else ''}"
            logger.error(error_msg)
            return await handle_auth_failure(error_msg, forward_url='broker.html', request=request)
        
        # Check if authorization code was provided
        if not auth_code:
            error_msg = "Authorization code not provided"
            logger.error(error_msg)
            return await handle_auth_failure(error_msg, forward_url='broker.html', request=request)
            
        logger.debug(f'Pocketful broker - Received authorization code: {auth_code}')
        # Exchange auth code for access token and fetch client_id
        auth_token, feed_token, user_id, error_message = await auth_function(auth_code, state)
        forward_url = 'broker.html'
        
    elif broker == 'definedge':
        if request.method == 'GET':
            # Trigger OTP generation on page load
            api_token = settings.BROKER_API_KEY
            api_secret = settings.BROKER_API_SECRET
            
            # Import the step1 function to trigger OTP
            from app.web.broker.definedge.api.auth_api import login_step1
            
            try:
                step1_response = await login_step1(api_token, api_secret)
                if step1_response and 'otp_token' in step1_response:
                    # Store OTP token in session for later use
                    request.session['definedge_otp_token'] = step1_response['otp_token']
                    otp_message = step1_response.get('message', 'OTP has been sent successfully')
                    logger.info(f"Definedge OTP triggered: {otp_message}")
                    return templates.TemplateResponse('definedgeotp.html', {"request": request, "otp_message": otp_message, "otp_sent": True})
                else:
                    error_msg = "Failed to send OTP. Please check your API credentials."
                    logger.error(f"Definedge OTP generation failed: {step1_response}")
                    return templates.TemplateResponse('definedgeotp.html', {"request": request, "error_message": error_msg, "otp_sent": False})
            except Exception as e:
                error_msg = f"Error sending OTP: {str(e)}"
                logger.error(f"Definedge OTP generation error: {e}")
                return templates.TemplateResponse('definedgeotp.html', {"request": request, "error_message": error_msg, "otp_sent": False})

        elif request.method == 'POST':
            form = await request.form()
            action = form.get('action')
            
            # Handle OTP resend request
            if action == 'resend':
                api_token = settings.BROKER_API_KEY
                api_secret = settings.BROKER_API_SECRET
                
                from app.web.broker.definedge.api.auth_api import login_step1
                
                try:
                    step1_response = await login_step1(api_token, api_secret)
                    if step1_response and 'otp_token' in step1_response:
                        request.session['definedge_otp_token'] = step1_response['otp_token']
                        otp_message = "OTP has been resent successfully"
                        logger.info(f"Definedge OTP resent successfully")
                        return JSONResponse(content={'status': 'success', 'message': otp_message})
                    else:
                        return JSONResponse(content={'status': 'error', 'message': 'Failed to resend OTP'})
                except Exception as e:
                    logger.error(f"Definedge OTP resend error: {e}")
                    return JSONResponse(content={'status': 'error', 'message': str(e)})
            
            # Handle OTP verification
            else:
                otp_code = form.get('otp')
                otp_token = request.session.get('definedge_otp_token')
                
                if not otp_token:
                    # Need to regenerate OTP token
                    return templates.TemplateResponse('definedgeotp.html',
                                                 {"request": request, "error_message": "Session expired. Please refresh the page to get a new OTP.",
                                                  "otp_sent": False})
                
                # Get api_secret for authentication
                api_secret = settings.BROKER_API_SECRET
                
                # Use authenticate_broker for OTP verification
                from app.web.broker.definedge.api.auth_api import authenticate_broker
                
                try:
                    # Call authenticate_broker with OTP token and code
                    auth_token, feed_token, user_id, error_message = await authenticate_broker(otp_token, otp_code, api_secret)
                    
                    if auth_token:
                        # Clear the OTP token from session
                        request.session.pop('definedge_otp_token', None)
                        
                except Exception as e:
                    logger.error(f"Definedge OTP verification error: {e}")
                    auth_token = None
                    feed_token = None
                    user_id = None
                    error_message = str(e)
                
                forward_url = 'definedgeotp.html'

    else:
        code = request.query_params.get('code') or request.query_params.get('request_token')
        logger.debug(f'Generic broker - The code is {code}')
        auth_token, error_message = await auth_function(code)
        forward_url = 'broker.html'
    
    if auth_token:
        # Store broker in session
        request.session['broker'] = broker
        logger.info(f'Successfully connected broker: {broker}')
        if broker == 'zerodha':
            auth_token = f'{BROKER_API_KEY}:{auth_token}'
        if broker == 'dhan':
            auth_token = f'{auth_token}'
        
        # For brokers that have user_id and feed_token from authenticate_broker
        if broker =='angel' or broker == 'compositedge' or broker == 'pocketful' or broker == 'definedge':
            # For Compositedge, handle missing session user
            if broker == 'compositedge' and 'user' not in request.session:
                # Get the admin user from the database
                from app.db.user_db import find_user_by_username
                admin_user = await find_user_by_username()
                if admin_user:
                    # Use the admin user's username
                    username = admin_user.username
                    request.session['user'] = username
                    logger.info(f"Compositedge callback: Set session user to {username}")
                else:
                    logger.error("No admin user found in database for Compositedge callback")
                    return await handle_auth_failure("No user account found. Please login first.", forward_url='broker.html', request=request)
            
            # Pass the feed token and user_id to handle_auth_success
            return await handle_auth_success(auth_token, request.session['user'], broker, feed_token=feed_token, user_id=user_id)
        else:
            # Pass just the feed token to handle_auth_success (other brokers don't have user_id)
            return await handle_auth_success(auth_token, request.session['user'], broker, feed_token=feed_token)
    else:
        return await handle_auth_failure(error_message, forward_url=forward_url, request=request)

@brlogin_router.api_route('/{broker}/loginflow', methods=['POST','GET'])
@limiter.limit(LOGIN_RATE_LIMIT_MIN)
@limiter.limit(LOGIN_RATE_LIMIT_HOUR)
async def broker_loginflow(broker: str, request: Request):
    # Check if user is not in session first
    if 'user' not in request.session:
        return RedirectResponse(url="/auth/login", status_code=status.HTTP_302_FOUND)

    if broker == 'kotak':
        # Get form data
        form = await request.form()
        mobile_number = form.get('mobilenumber', '')
        password = form.get('password')

        # Strip any existing prefix and add +91
        mobile_number = mobile_number.replace('+91', '').strip()
        if not mobile_number.startswith('+91'):
            mobile_number = f'+91{mobile_number}'
        
        # First get the access token
        api_secret = settings.BROKER_API_SECRET
        auth_string = base64.b64encode(f"{BROKER_API_KEY}:{api_secret}".encode()).decode('utf-8')
        # Define the connection
        client = get_httpx_client()

        # Define the payload
        payload = json.dumps({
            'grant_type': 'client_credentials'
        })

        # Define the headers with Basic Auth
        headers = {
            'accept': '*/*',
            'Content-Type': 'application/json',
            'Authorization': f'Basic {auth_string}'
        }

        # Make API request
        try:
            response = await client.post("https://napi.kotaksecurities.com/oauth2/token", content=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
        except Exception as e:
            logger.error(f"Error getting Kotak access token: {e}")
            return templates.TemplateResponse('kotak.html', {"request": request, "error_message": "Failed to get access token."})

        if 'access_token' in data:
            access_token = data['access_token']
            # Login with mobile number and password
            payload = json.dumps({
                "mobileNumber": mobile_number,
                "password": password
            })
            headers = {
                'accept': '*/*',
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {access_token}'
            }
            try:
                response = await client.post("https://gw-napi.kotaksecurities.com/login/1.0/login/v2/validate", content=payload, headers=headers)
                response.raise_for_status()
                data = response.json()
            except Exception as e:
                logger.error(f"Error validating Kotak login: {e}")
                return templates.TemplateResponse('kotak.html', {"request": request, "error_message": "Failed to validate login."})

            data_dict = data

            if 'data' in data_dict:
                token = data_dict['data']['token']
                sid = data_dict['data']['sid']
                hsServerId = data_dict['data']['hsServerId']
                decode_jwt = jwt.decode(token, options={"verify_signature": False})
                userid = decode_jwt.get("sub")

                para = {
                    "access_token": access_token,
                    "token": token,
                    "sid": sid,
                    "hsServerId": hsServerId,
                    "userid": userid
                }
                await getKotakOTP(userid, access_token)
                return templates.TemplateResponse('kotakotp.html', {"request": request, "para": para})
            else:
                error_message = data_dict.get('message', 'Unknown error occurred')
                return templates.TemplateResponse('kotak.html', {"request": request, "error_message": error_message})
        else:
            error_message = data.get('message', 'Unknown error occurred')
            return templates.TemplateResponse('kotak.html', {"request": request, "error_message": error_message})
        
    return JSONResponse(content={"detail": "Not Found"}, status_code=status.HTTP_404_NOT_FOUND)


async def getKotakOTP(userid: str, access_token: str):
    client = get_httpx_client()
    payload = json.dumps({
    "userId": userid,
    "sendEmail": True,
    "isWhitelisted": True
    })
    headers = {
    'accept': '*/*',
    'Content-Type': 'application/json',
    'Authorization': f'Bearer {access_token}'
    }
    try:
        response = await client.post("https://gw-napi.kotaksecurities.com/login/1.0/login/otp/generate", content=payload, headers=headers)
        response.raise_for_status()
        data = response.json()
        logger.debug(f"Kotak OTP generation response: {data}")
        return 'success'
    except Exception as e:
        logger.error(f"Error generating Kotak OTP: {e}")
        return 'failure'