import base64
import http.client
import json

import jwt
from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, RedirectResponse
from starlette.templating import Jinja2Templates

from app.core.services.limiter_service import limiter
from app.utils.auth_utils import handle_auth_failure, handle_auth_success
from app.core.config import settings
from app.utils.logging import get_logger
from app.utils.session import check_session_validity_fastapi

# Initialize logger and templates
logger = get_logger(__name__)
templates = Jinja2Templates(directory="app/frontend/templates")

# Configuration
BROKER_API_KEY = settings.BROKER_API_KEY
LOGIN_RATE_LIMIT_MIN = settings.LOGIN_RATE_LIMIT_MIN
LOGIN_RATE_LIMIT_HOUR = settings.LOGIN_RATE_LIMIT_HOUR

broker_router = APIRouter()

@broker_router.api_route("/{broker}/callback", methods=["GET", "POST"], dependencies=[Depends(check_session_validity_fastapi)])
@limiter.limit(LOGIN_RATE_LIMIT_MIN)
@limiter.limit(LOGIN_RATE_LIMIT_HOUR)
async def broker_callback(request: Request, broker: str):
    logger.info(f"Broker callback initiated for: {broker}")
    logger.debug(f"Session contents: {request.session}")

    user = request.session.get("user")
    if not user and broker != 'compositedge':
        logger.warning(f"User not in session for {broker} callback, redirecting to login")
        return RedirectResponse(url="/login")

    if request.session.get("logged_in"):
        request.session["broker"] = broker
        return RedirectResponse(url="/dashboard")

    broker_auth_functions = request.app.broker_auth_functions
    auth_function = broker_auth_functions.get(f"{broker}_auth")

    if not auth_function:
        return JSONResponse(content={"error": "Broker authentication function not found."}, status_code=404)

    feed_token = None
    auth_token = None
    error_message = "Invalid request"
    forward_url = "broker.html"
    user_id = None

    form_data = await request.form()

    if broker == "fivepaisa":
        if request.method == "GET":
            return templates.TemplateResponse("5paisa.html", {"request": request})
        elif request.method == "POST":
            clientcode = form_data.get("clientid")
            broker_pin = form_data.get("pin")
            totp_code = form_data.get("totp")
            auth_token, error_message = auth_function(clientcode, broker_pin, totp_code)
            forward_url = "5paisa.html"

    elif broker == "angel":
        if request.method == "GET":
            return templates.TemplateResponse("angel.html", {"request": request})
        elif request.method == "POST":
            clientcode = form_data.get("clientid")
            broker_pin = form_data.get("pin")
            totp_code = form_data.get("totp")
            user_id = clientcode
            auth_token, feed_token, error_message = auth_function(clientcode, broker_pin, totp_code)
            forward_url = "angel.html"

    elif broker == "aliceblue":
        if request.method == "GET":
            return templates.TemplateResponse("aliceblue.html", {"request": request})
        elif request.method == "POST":
            userid = form_data.get("userid")
            from app.utils.httpx_client import get_httpx_client
            client = get_httpx_client()
            payload = {"userId": userid}
            headers = {'Content-Type': 'application/json'}
            try:
                url = "https://ant.aliceblueonline.com/rest/AliceBlueAPIService/api/customer/getAPIEncpkey"
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                data_dict = response.json()
                if data_dict.get("stat") == "Ok" and data_dict.get("encKey"):
                    enc_key = data_dict["encKey"]
                    auth_token, error_message = auth_function(userid, enc_key)
                    if auth_token:
                        return await handle_auth_success(request, auth_token, user, broker)
                    else:
                        return await handle_auth_failure(request, error_message, forward_url="aliceblue.html")
                else:
                    error_msg = data_dict.get("emsg", "Failed to get encryption key")
                    return await handle_auth_failure(request, f"Failed to get encryption key: {error_msg}", forward_url="aliceblue.html")
            except Exception as e:
                return JSONResponse(content={"error": f"Authentication error: {str(e)}"}, status_code=500)

    elif broker == "compositedge":
        session_data_str = ""
        if request.method == "POST":
            content_type = request.headers.get("content-type", "")
            if "application/x-www-form-urlencoded" in content_type:
                body = await request.body()
                raw_data = body.decode("utf-8")
                if raw_data.startswith("session="):
                    from urllib.parse import unquote
                    session_data_str = unquote(raw_data[8:])
                else:
                    session_data_str = raw_data
            else:
                 body = await request.body()
                 session_data_str = body.decode("utf-8")
        else: # GET
            session_data_str = request.query_params.get("session")

        if not session_data_str:
            return JSONResponse(content={"error": "No session data received"}, status_code=400)

        try:
            session_json = json.loads(session_data_str)
            if isinstance(session_json, str):
                session_json = json.loads(session_json)
        except json.JSONDecodeError as e:
            return JSONResponse(content={"error": f"Invalid JSON: {e}", "raw_data": session_data_str}, status_code=400)

        access_token = session_json.get("accessToken")
        if not access_token:
            return JSONResponse(content={"error": "No access token found"}, status_code=400)

        auth_token, feed_token, user_id, error_message = auth_function(access_token)
        if not user:
            from app.db.models.user_db import find_user_by_username
            admin_user = find_user_by_username()
            if admin_user:
                user = admin_user.username
                request.session["user"] = user
            else:
                return await handle_auth_failure(request, "No admin user found.", forward_url="broker.html")

    elif broker == "tradejini":
        if request.method == "GET":
            return templates.TemplateResponse("tradejini.html", {"request": request})
        elif request.method == "POST":
            password = form_data.get("password")
            twofa = form_data.get("twofa")
            twofatype = form_data.get("twofatype")
            auth_token, error_message = auth_function(password=password, twofa=twofa, twofa_type=twofatype)
            if auth_token:
                return await handle_auth_success(request, auth_token, user, broker)
            else:
                return templates.TemplateResponse("tradejini.html", {"request": request, "error": error_message})

    # ... other brokers
    else:
        code = request.query_params.get("code") or request.query_params.get("request_token")
        logger.debug(f"Generic broker ({broker}) - The code is {code}")
        auth_token, error_message = auth_function(code)
        forward_url = "broker.html"


    if auth_token:
        request.session["broker"] = broker
        if broker == "zerodha":
            auth_token = f"{BROKER_API_KEY}:{auth_token}"

        return await handle_auth_success(request, auth_token, user, broker, feed_token=feed_token, user_id=user_id)
    else:
        return await handle_auth_failure(request, error_message, forward_url=forward_url)


@broker_router.api_route("/{broker}/loginflow", methods=["GET", "POST"], dependencies=[Depends(check_session_validity_fastapi)])
async def broker_loginflow(request: Request, broker: str):
    if broker == "kotak":
        form_data = await request.form()
        mobile_number = form_data.get("mobilenumber", "").replace("+91", "").strip()
        if not mobile_number.startswith("+91"):
            mobile_number = f"+91{mobile_number}"
        password = form_data.get("password")

        api_secret = settings.BROKER_API_SECRET
        auth_string = base64.b64encode(f"{BROKER_API_KEY}:{api_secret}".encode()).decode("utf-8")
        conn = http.client.HTTPSConnection("napi.kotaksecurities.com")
        payload = json.dumps({"grant_type": "client_credentials"})
        headers = {
            "accept": "*/*",
            "Content-Type": "application/json",
            "Authorization": f"Basic {auth_string}",
        }
        conn.request("POST", "/oauth2/token", payload, headers)
        res = conn.getresponse()
        data = json.loads(res.read().decode("utf-8"))

        if "access_token" in data:
            access_token = data["access_token"]
            conn_gw = http.client.HTTPSConnection("gw-napi.kotaksecurities.com")
            payload_validate = json.dumps({"mobileNumber": mobile_number, "password": password})
            headers_validate = {
                "accept": "*/*",
                "Content-Type": "application/json",
                "Authorization": f"Bearer {access_token}",
            }
            conn_gw.request("POST", "/login/1.0/login/v2/validate", payload_validate, headers_validate)
            res_validate = conn_gw.getresponse()
            data_validate = json.loads(res_validate.read().decode("utf-8"))

            if "data" in data_validate:
                token = data_validate["data"]["token"]
                sid = data_validate["data"]["sid"]
                hsServerId = data_validate["data"]["hsServerId"]
                decode_jwt = jwt.decode(token, options={"verify_signature": False})
                userid = decode_jwt.get("sub")

                para = {
                    "access_token": access_token,
                    "token": token,
                    "sid": sid,
                    "hsServerId": hsServerId,
                    "userid": userid,
                }
                getKotakOTP(userid, access_token)
                return templates.TemplateResponse("kotakotp.html", {"request": request, "para": para})
            else:
                error_message = data_validate.get("message", "Unknown error")
                return templates.TemplateResponse("kotak.html", {"request": request, "error_message": error_message})

    return JSONResponse(content={"error": "Flow not implemented"}, status_code=501)


def getKotakOTP(userid, access_token):
    conn = http.client.HTTPSConnection("gw-napi.kotaksecurities.com")
    payload = json.dumps({"userId": userid, "sendEmail": True, "isWhitelisted": True})
    headers = {
        "accept": "*/*",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}",
    }
    conn.request("POST", "/login/1.0/login/otp/generate", payload, headers)
    res = conn.getresponse()
    res.read()
    return "success"