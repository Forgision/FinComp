import os
import re
import json
import jwt
import base64
import httpx # Import httpx

from fastapi import APIRouter, Request, Depends, Form, HTTPException, status
from starlette.datastructures import UploadFile
from starlette.responses import HTMLResponse, RedirectResponse, JSONResponse
from starlette.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.utils.logging import get_logger # type: ignore
# from app.utils.security import verify_password # type: ignore
# from app.services import user_service # type: ignore
# from app.utils.auth_utils import handle_auth_success, handle_auth_failure # type: ignore
# from app.utils.plugin_loader import load_broker_auth_functions # type: ignore
# from app.utils.httpx_client import get_httpx_client # type: ignore

# Suppress Pylance import errors for internal app modules
# Pylance does not correctly resolve these imports without additional configuration
# in .vscode/settings.json, which the user has declined to modify.
# type: ignore # type: ignore # type: ignore # type: ignore # type: ignore # type: ignore # type: ignore # type: ignore

# Initialize logger
logger = get_logger(__name__)

# Initialize Jinja2Templates
templates = Jinja2Templates(directory="templates")

# Initialize broker_router
broker_router = APIRouter(prefix="/auth/broker")

# Define getKotakOTP (moved to top for better organization and async)
async def getKotakOTP(userid: str, access_token: str):
    logger.debug(f"Attempting to send OTP for Kotak user: {userid}")
    async with get_httpx_client() as client:
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
            logger.info(f"Kotak OTP generation response: {response.text}")
            return True, "OTP sent successfully"
        except httpx.HTTPStatusError as e:
            logger.error(f"Kotak OTP generation failed: {e.response.text}")
            return False, f"Failed to send OTP: {e.response.text}"
        except Exception as e:
            logger.error(f"Error in getKotakOTP: {e}")
            return False, f"Error sending OTP: {str(e)}"

@broker_router.post("/{broker}/loginflow")
async def broker_loginflow(
    broker: str,
    request: Request,
    mobile_number: str = Form(..., alias="mobilenumber"),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    # Check if user is not in session
    if 'user' not in request.session:
        return RedirectResponse(url="/auth/login", status_code=status.HTTP_302_FOUND)

    if broker == 'kotak':
        # Strip any existing prefix and add +91
        mobile_number = mobile_number.replace('+91', '').strip()
        if not mobile_number.startswith('+91'):
            mobile_number = f'+91{mobile_number}'
        
        # First get the access token
        api_secret = settings.BROKER_API_SECRET
        auth_string = base64.b64encode(f"{settings.BROKER_API_KEY}:{api_secret}".encode()).decode('utf-8')

        async with get_httpx_client() as client:
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

            try:
                # Make API request to get access token
                response = await client.post("https://napi.kotaksecurities.com/oauth2/token", content=payload, headers=headers)
                response.raise_for_status()
                data = response.json()

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
                    response = await client.post("https://gw-napi.kotaksecurities.com/login/1.0/login/v2/validate", content=payload, headers=headers)
                    response.raise_for_status()
                    data_dict = response.json()

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
                        return templates.TemplateResponse("kotakotp.html", {"request": request, "para": para})
                    else:
                        error_message = data_dict.get('message', 'Unknown error occurred')
                        return templates.TemplateResponse("kotak.html", {"request": request, "error_message": error_message})
                else:
                    error_message = data.get('message', 'Failed to get access token')
                    return templates.TemplateResponse("kotak.html", {"request": request, "error_message": error_message})

            except httpx.HTTPStatusError as e:
                logger.error(f"Kotak API request failed: {e.response.text}")
                return templates.TemplateResponse("kotak.html", {"request": request, "error_message": f"API Error: {e.response.text}"})
            except Exception as e:
                logger.error(f"Error in Kotak login flow: {e}")
                return templates.TemplateResponse("kotak.html", {"request": request, "error_message": f"An unexpected error occurred: {str(e)}"})
    
    return RedirectResponse(url=f"/auth/broker/{broker}/callback", status_code=status.HTTP_302_FOUND)

@broker_router.post("/{broker}/verifyotp")
async def verify_otp(
    broker: str,
    request: Request,
    otp: str = Form(...),
    access_token: str = Form(...),
    token: str = Form(...),
    sid: str = Form(...),
    hsServerId: str = Form(...),
    userid: str = Form(...),
    db: Session = Depends(get_db)
):
    if broker == 'kotak':
        async with get_httpx_client() as client:
            payload = json.dumps({
                "userId": userid,
                "otp": otp
            })
            headers = {
                'accept': '*/*',
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {access_token}'
            }
            try:
                response = await client.post("https://gw-napi.kotaksecurities.com/login/1.0/login/otp/verify", content=payload, headers=headers)
                response.raise_for_status()
                data_dict = response.json()

                if data_dict.get('status') == 'success':
                    # Assuming OTP is verified, proceed to handle_auth_success
                    # Construct broker_response as expected by handle_auth_success
                    broker_response = {
                        "access_token": access_token,
                        "request_token": token,  # Using token as request_token for consistency
                        "sid": sid,
                        "hsServerId": hsServerId,
                        "user_id": userid,
                        "broker": broker,
                    }
                    return await handle_auth_success(broker, broker_response, request, db)
                else:
                    error_message = data_dict.get('message', 'OTP verification failed')
                    para = {
                        "access_token": access_token,
                        "token": token,
                        "sid": sid,
                        "hsServerId": hsServerId,
                        "userid": userid
                    }
                    return templates.TemplateResponse("kotakotp.html", {"request": request, "error_message": error_message, "para": para})
            except httpx.HTTPStatusError as e:
                logger.error(f"Kotak OTP verification failed: {e.response.text}")
                para = {
                    "access_token": access_token,
                    "token": token,
                    "sid": sid,
                    "hsServerId": hsServerId,
                    "userid": userid
                }
                return templates.TemplateResponse("kotakotp.html", {"request": request, "error_message": f"API Error: {e.response.text}", "para": para})
            except Exception as e:
                logger.error(f"Error in Kotak OTP verification flow: {e}")
                para = {
                    "access_token": access_token,
                    "token": token,
                    "sid": sid,
                    "hsServerId": hsServerId,
                    "userid": userid
                }
                return templates.TemplateResponse("kotakotp.html", {"request": request, "error_message": f"An unexpected error occurred: {str(e)}", "para": para})

    return RedirectResponse(url=f"/auth/broker/{broker}/callback", status_code=status.HTTP_302_FOUND)


# TODO: Implement rate limiting for FastAPI.
# The original Flask app used `limiter.limiter`. This needs to be replaced with FastAPI-compatible rate limiting.

@broker_router.get("/", response_class=RedirectResponse)
async def broker_root(request: Request):
    # This acts as a placeholder or entry point, typically redirecting to the dashboard
    if request.session.get('logged_in'):
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
    return RedirectResponse(url="/auth/login", status_code=status.HTTP_302_FOUND) # Updated redirect path

@broker_router.api_route("/{broker}/callback", methods=["GET", "POST"])
async def broker_callback(broker: str, request: Request, db: Session = Depends(get_db)):
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
        # Store broker in session
        request.session['broker'] = broker
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)

    # Load broker authentication functions dynamically
    broker_auth_functions = load_broker_auth_functions()
    auth_function = broker_auth_functions.get(f'{broker}_auth')

    if not auth_function:
        return JSONResponse(content={"error": "Broker authentication function not found."}, status_code=status.HTTP_404_NOT_FOUND)
    
    # Initialize feed_token and user_id to None by default
    feed_token = None
    user_id = None
    auth_token = None
    error_message = None
    forward_url = 'broker.html' # Default forward URL for templates

    if broker == 'fivepaisa':
        if request.method == 'GET':
            return templates.TemplateResponse('5paisa.html', {"request": request})
        
        elif request.method == 'POST':
            form = await request.form()
            clientcode = str(form.get('clientid'))
            broker_pin = str(form.get('pin'))
            totp_code = str(form.get('totp'))
            
            # to store user_id in the DB
            user_id = clientcode
            
            auth_token, feed_token, error_message = await auth_function(clientcode, broker_pin, totp_code)

    elif broker == 'angel':
        if request.method == 'GET':
            return templates.TemplateResponse('angel.html', {"request": request})
        
        elif request.method == 'POST':
            form = await request.form()
            clientcode = str(form.get('clientid'))
            broker_pin = str(form.get('pin'))
            totp_code = str(form.get('totp'))
            
            # to store user_id in the DB
            user_id = clientcode
            
            auth_token, feed_token, error_message = await auth_function(clientcode, broker_pin, totp_code)

    elif broker == 'aliceblue':
        if request.method == 'GET':
            return templates.TemplateResponse('aliceblue.html', {"request": request})
        
        elif request.method == 'POST':
            logger.info('Aliceblue Login Flow initiated')
            form = await request.form()
            userid = str(form.get('userid'))

            # Use httpx_client within an async context
            async with get_httpx_client() as client:
            
                payload = {
                    "userId": userid
                }
                headers = {
                    'Content-Type': 'application/json'
                }
                try:
                    url = "https://ant.aliceblueonline.com/rest/AliceBlueAPIService/api/customer/getAPIEncpkey"
                    response = await client.post(url, json=payload, headers=headers)
                    response.raise_for_status()
                    data_dict = response.json()
                    logger.debug(f'Aliceblue response data: {data_dict}')
                    
                    if data_dict.get('stat') == 'Ok' and data_dict.get('encKey'):
                        enc_key = data_dict['encKey']
                        auth_token, error_message = await auth_function(userid, enc_key)
                        
                        if auth_token:
                            return await handle_auth_success(auth_token, request.session['user'], broker, db)
                        else:
                            return await handle_auth_failure(error_message, request, forward_url='aliceblue.html')
                    else:
                        error_msg = data_dict.get('emsg', 'Failed to get encryption key')
                        return await handle_auth_failure(f"Failed to get encryption key: {error_msg}", request, forward_url='aliceblue.html')
                except Exception as e:
                    return JSONResponse(content={"error": f"Authentication error: {str(e)}"}, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
    elif broker=='fivepaisaxts':
        code = 'fivepaisaxts'
        logger.debug(f'FivePaisaXTS broker - code: {code}')
               
        auth_token, feed_token, user_id, error_message = await auth_function(code)

    elif broker=='compositedge':
        if 'user' not in request.session:
            logger.warning("Session 'user' key missing in Compositedge callback, attempting to recover")
            
        raw_data = None # Initialize raw_data here for the outer scope
        try:
            if request.method == 'POST':
                content_type = request.headers.get('Content-Type')
                if content_type and 'application/x-www-form-urlencoded' in content_type:
                    form = await request.form()
                    raw_data_form = form.get('session') # Assuming 'session' is the form field name
                    if raw_data_form:
                        # Check if it's an UploadFile or a plain string
                        if isinstance(raw_data_form, UploadFile):
                            raw_data = (await raw_data_form.read()).decode('utf-8')
                        elif isinstance(raw_data_form, str):
                            raw_data = raw_data_form
                        else: # raw_data_form is None or an unexpected type
                            raw_data = (await request.body()).decode('utf-8') # Fallback to raw body
                    else:
                        raw_data = (await request.body()).decode('utf-8') # Fallback if 'session' not in form
                else: # Assume application/json or other body content
                    raw_data = (await request.body()).decode('utf-8')
            else: # GET request
                raw_data = request.query_params.get('session')
                
            if not raw_data:
                return JSONResponse(content={"error": "No session data received"}, status_code=status.HTTP_400_BAD_REQUEST)

            # Process raw_data now that it's confirmed to exist
            raw_data_str = str(raw_data).strip()
            session_json = json.loads(raw_data_str)
            # If it's a string after first json.loads, it might be double-encoded
            if isinstance(session_json, str):
                session_json = json.loads(session_json)
                
            if not isinstance(session_json, dict):
                logger.error(f"Parsed session_json is not a dictionary: {type(session_json)}")
                return JSONResponse(content={"error": "Invalid session data format after JSON parsing"}, status_code=status.HTTP_400_BAD_REQUEST)

            access_token = session_json.get('accessToken')
            
            if not access_token:
                return JSONResponse(content={"error": "Access token not found in session data"}, status_code=status.HTTP_400_BAD_REQUEST)
                
            # auth_function is defined earlier in the outer scope, so it's accessible here.
            auth_token, feed_token, user_id, error_message = await auth_function(access_token)

        except json.JSONDecodeError as e:
            logger.error(f"JSONDecodeError in compositedge callback: {e}, raw_data: {raw_data}")
            return JSONResponse(content={
                "error": f"Invalid JSON format: {str(e)}",
                "raw_data_received": raw_data
            }, status_code=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"General error in compositedge callback: {str(e)}")
            return JSONResponse(content={"error": f"Error processing request: {str(e)}"}, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

    elif broker=='fyers':
        code = request.query_params.get('auth_code')
        logger.debug(f'Fyers broker - The code is {code}')
        auth_token, error_message = await auth_function(code)

    elif broker=='tradejini':
        if request.method == 'GET':
            return templates.TemplateResponse('tradejini.html', {"request": request})
        
        elif request.method == 'POST':
            form = await request.form()
            password = form.get('password')
            twofa = form.get('twofa')
            twofatype = form.get('twofatype')
            
            auth_token, error_message = await auth_function(password=password, twofa=twofa, twofa_type=twofatype)
            
            if auth_token:
                return await handle_auth_success(auth_token, request.session['user'], broker, db)
            else:
                return templates.TemplateResponse('tradejini.html', {"request": request, "error": error_message})
        
    elif broker=='icici':
        code = request.query_params.get('apisession')
        logger.debug(f'ICICI broker - The code is {code}')
        auth_token, error_message = await auth_function(code)

    elif broker=='ibulls':
        code = 'ibulls'
        logger.debug(f'Indiabulls broker - code: {code}')
            
        auth_token, feed_token, user_id, error_message = await auth_function(code)

    elif broker=='iifl':
        code = 'iifl'
        logger.debug(f'IIFL broker - The code is {code}')
            
        auth_token, feed_token, user_id, error_message = await auth_function(code)

    elif broker=='dhan':
        code = 'dhan'
        logger.debug(f'Dhan broker - The code is {code}')
        auth_token, error_message = await auth_function(code)
        
        if auth_token:
            from broker.dhan.api.funds import test_auth_token # Assuming this path will be valid in FastAPI context # type: ignore # type: ignore
            is_valid, validation_error = await test_auth_token(auth_token)
            
            if not is_valid:
                logger.error(f"Dhan authentication validation failed: {validation_error}")
                return await handle_auth_failure(f"Authentication validation failed: {validation_error}", request, forward_url='broker.html')
            
            logger.info("Dhan authentication validation successful")
        
    elif broker=='indmoney':
        code = 'indmoney'
        logger.debug(f'IndMoney broker - The code is {code}')
        auth_token, error_message = await auth_function(code)
        
    elif broker=='dhan_sandbox':
        code = 'dhan_sandbox'
        logger.debug(f'Dhan Sandbox broker - The code is {code}')
        auth_token, error_message = await auth_function(code)
        
    elif broker == 'groww':
        code = 'groww'
        logger.debug(f'Groww broker - The code is {code}')
        auth_token, error_message = await auth_function(code)

    elif broker == 'wisdom':
        code = 'wisdom'
        logger.debug(f'Wisdom broker - The code is {code}')
        auth_token, feed_token, user_id, error_message = await auth_function(code)

    elif broker == 'zebu':
        if request.method == 'GET':
            return templates.TemplateResponse('zebu.html', {"request": request})
        
        elif request.method == 'POST':
            form = await request.form()
            userid = form.get('userid')
            password = form.get('password')
            totp_code = form.get('totp')

            auth_token, error_message = await auth_function(userid, password, totp_code)

    elif broker == 'shoonya':
        if request.method == 'GET':
            return templates.TemplateResponse('shoonya.html', {"request": request})
        
        elif request.method == 'POST':
            form = await request.form()
            userid = form.get('userid')
            password = form.get('password')
            totp_code = form.get('totp')

            auth_token, error_message = await auth_function(userid, password, totp_code)

    elif broker == 'firstock':
        if request.method == 'GET':
            return templates.TemplateResponse('firstock.html', {"request": request})
        
        elif request.method == 'POST':
            form = await request.form()
            userid = form.get('userid')
            password = form.get('password')
            totp_code = form.get('totp')

            auth_token, error_message = await auth_function(userid, password, totp_code)

    elif broker == 'flattrade':
        code = request.query_params.get('code')
        client = request.query_params.get('client')
        logger.debug(f'Flattrade broker - The code is {code} for client {client}')
        auth_token, error_message = await auth_function(code)

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

    elif broker == 'paytm':
        request_token = request.query_params.get('requestToken')
        logger.debug(f'Paytm broker - The request token is {request_token}')
        auth_token, error_message = await auth_function(request_token)

    elif broker == 'pocketful':
        auth_code = request.query_params.get('code')
        state = request.query_params.get('state')
        error = request.query_params.get('error')
        error_description = request.query_params.get('error_description')
        
        if error:
            error_msg = f"OAuth error: {error}. {error_description if error_description else ''}"
            logger.error(error_msg)
            return await handle_auth_failure(error_msg, request, forward_url='broker.html')
        
        if not auth_code:
            error_msg = "Authorization code not provided"
            logger.error(error_msg)
            return await handle_auth_failure(error_msg, request, forward_url='broker.html')
            
        logger.debug(f'Pocketful broker - Received authorization code: {auth_code}')
        auth_token, feed_token, user_id, error_message = await auth_function(auth_code, state)
        
    elif broker == 'definedge':
        if request.method == 'GET':
            api_token = settings.BROKER_API_KEY
            api_secret = settings.BROKER_API_SECRET
            
            from broker.definedge.api.auth_api import login_step1 # Assuming this path will be valid in FastAPI context # type: ignore
            
            try:
                step1_response = await login_step1(api_token, api_secret)
                if step1_response and 'otp_token' in step1_response:
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
            
            if action == 'resend':
                api_token = settings.BROKER_API_KEY
                api_secret = settings.BROKER_API_SECRET
                
                from broker.definedge.api.auth_api import login_step1 # type: ignore # type: ignore
                
                try:
                    step1_response = await login_step1(api_token, api_secret)
                    if step1_response and 'otp_token' in step1_response:
                        request.session['definedge_otp_token'] = step1_response['otp_token']
                        otp_message = "OTP has been resent successfully"
                        logger.info(f"Definedge OTP resent successfully")
                        return JSONResponse(content={'status': 'success', 'message': otp_message})
                    else:
                        return JSONResponse(content={'status': 'error', 'message': 'Failed to resend OTP'}, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
                except Exception as e:
                    logger.error(f"Definedge OTP resend error: {e}")
                    return JSONResponse(content={'status': 'error', 'message': str(e)}, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            else:
                otp_code = form.get('otp')
                otp_token = request.session.get('definedge_otp_token')
                
                if not otp_token:
                    return templates.TemplateResponse('definedgeotp.html', {
                                                "request": request,
                                                "error_message":"Session expired. Please refresh the page to get a new OTP.",
                                                "otp_sent": False})
                
                api_secret = settings.BROKER_API_SECRET
                
                from broker.definedge.api.auth_api import authenticate_broker # type: ignore # type: ignore
                
                try:
                    auth_token, feed_token, user_id, error_message = await authenticate_broker(otp_token, otp_code, api_secret)
                    
                    if auth_token:
                        request.session.pop('definedge_otp_token', None)
                        
                except Exception as e:
                    logger.error(f"Definedge OTP verification error: {e}")
                    auth_token = None
                    feed_token = None
                    user_id = None
                    error_message = str(e)
                
    else:
        code = request.query_params.get('code') or request.query_params.get('request_token')
        logger.debug(f'Generic broker - The code is {code}')
        auth_token, error_message = await auth_function(code)
    
    if auth_token:
        request.session['broker'] = broker
        logger.info(f'Successfully connected broker: {broker}')
        if broker == 'zerodha':
            auth_token = f'{settings.BROKER_API_KEY}:{auth_token}'
        if broker == 'dhan':
            auth_token = f'{auth_token}'
        
        if broker =='angel' or broker == 'compositedge' or broker == 'pocketful' or broker == 'definedge':
            if broker == 'compositedge' and 'user' not in request.session:
                admin_user = user_service.get_user_by_username(db, username="admin") # Corrected function call and added username parameter
                if admin_user:
                    username = admin_user.username
                    request.session['user'] = username
                    logger.info(f"Compositedge callback: Set session user to {username}")
                else:
                    logger.error("No admin user found in database for Compositedge callback")
                    return await handle_auth_failure("No user account found. Please login first.", request, forward_url='broker.html')
            
            return await handle_auth_success(auth_token, request.session['user'], broker, db, feed_token=feed_token, user_id=user_id)
        else:
            return await handle_auth_success(auth_token, request.session['user'], broker, db, feed_token=feed_token)
    else:
        return await handle_auth_failure(error_message, request, forward_url=forward_url)

@broker_router.api_route("/{broker}/loginflow", methods=["POST", "GET"])
async def broker_loginflow(broker: str, request: Request):
    # Check if user is not in session first
    if 'user' not in request.session:
        return RedirectResponse(url="/auth/login", status_code=status.HTTP_302_FOUND)

    if broker == 'kotak':
        if request.method == 'POST':
            form = await request.form()
            mobile_number = str(form.get('mobilenumber', ''))
            password = str(form.get('password', ''))

            # Strip any existing prefix and add +91
            mobile_number = mobile_number.replace('+91', '').strip()
            if not mobile_number.startswith('+91'):
                mobile_number = f'+91{mobile_number}'
            
            # Use httpx_client within an async context
            async with get_httpx_client() as client:
                # First get the access token
                api_secret = settings.BROKER_API_SECRET
                auth_string = base64.b64encode(f"{settings.BROKER_API_KEY}:{api_secret}".encode()).decode('utf-8')
                
                payload = json.dumps({
                    'grant_type': 'client_credentials'
                })
                headers = {
                    'accept': '*/*',
                    'Content-Type': 'application/json',
                    'Authorization': f'Basic {auth_string}'
                }
                
                try:
                    response = await client.post("https://napi.kotaksecurities.com/oauth2/token", content=payload, headers=headers)
                    response.raise_for_status()
                    data = response.json()

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
                        response = await client.post("https://gw-napi.kotaksecurities.com/login/1.0/login/v2/validate", content=payload, headers=headers)
                        response.raise_for_status()
                        data_dict = response.json()

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
                        error_message = data.get('message', 'Failed to get access token')
                        return templates.TemplateResponse('kotak.html', {"request": request, "error_message": error_message})
                except Exception as e:
                    logger.error(f"Kotak loginflow error: {e}")
                    return templates.TemplateResponse('kotak.html', {"request": request, "error_message": str(e)})
        else: # GET request for kotak
            return templates.TemplateResponse('kotak.html', {"request": request})
    
    return HTMLResponse(content="Unsupported broker or method for loginflow", status_code=status.HTTP_400_BAD_REQUEST)


@broker_router.post("/{broker}/verifyotp")
async def verify_otp(
    broker: str,
    request: Request,
    otp: str = Form(...),
    access_token: str = Form(...),
    token: str = Form(...),
    sid: str = Form(...),
    hsServerId: str = Form(...),
    userid: str = Form(...),
    db: Session = Depends(get_db)
):
    if broker == 'kotak':
        async with get_httpx_client() as client:
            payload = json.dumps({
                "userId": userid,
                "otp": otp
            })
            headers = {
                'accept': '*/*',
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {access_token}'
            }
            try:
                response = await client.post("https://gw-napi.kotaksecurities.com/login/1.0/login/otp/verify", content=payload, headers=headers)
                response.raise_for_status()
                data_dict = response.json()

                if data_dict.get('status') == 'success':
                    # Assuming OTP is verified, proceed to handle_auth_success
                    # Construct broker_response as expected by handle_auth_success
                    broker_response = {
                        "access_token": access_token,
                        "request_token": token,  # Using token as request_token for consistency
                        "sid": sid,
                        "hsServerId": hsServerId,
                        "user_id": userid,
                        "broker": broker,
                    }
                    return await handle_auth_success(broker, broker_response, request, db)
                else:
                    error_message = data_dict.get('message', 'OTP verification failed')
                    para = {
                        "access_token": access_token,
                        "token": token,
                        "sid": sid,
                        "hsServerId": hsServerId,
                        "userid": userid
                    }
                    return templates.TemplateResponse("kotakotp.html", {"request": request, "error_message": error_message, "para": para})
            except httpx.HTTPStatusError as e:
                logger.error(f"Kotak OTP verification failed: {e.response.text}")
                para = {
                    "access_token": access_token,
                    "token": token,
                    "sid": sid,
                    "hsServerId": hsServerId,
                    "userid": userid
                }
                return templates.TemplateResponse("kotakotp.html", {"request": request, "error_message": f"API Error: {e.response.text}", "para": para})
            except Exception as e:
                logger.error(f"Error in Kotak OTP verification flow: {e}")
                para = {
                    "access_token": access_token,
                    "token": token,
                    "sid": sid,
                    "hsServerId": hsServerId,
                    "userid": userid
                }
                return templates.TemplateResponse("kotakotp.html", {"request": request, "error_message": f"An unexpected error occurred: {str(e)}", "para": para})

    return RedirectResponse(url=f"/auth/broker/{broker}/callback", status_code=status.HTTP_302_FOUND)