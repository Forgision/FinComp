from fastapi import APIRouter, Request, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime, timedelta
import re

from app.db.connection import get_db # Main DB session
from app.db.traffic_db import IPBan, Error404Tracker, InvalidAPIKeyTracker, logs_session, TrafficLog # Traffic DB session and models
from app.db.settings_db import get_security_settings, set_security_settings
from app.utils.session import check_session_validity_fastapi
from app.utils.web import limiter
from app.web.frontend import templates
from slowapi.errors import RateLimitExceeded
from pydantic import BaseModel

logger = logging.getLogger(__name__)

security_router = APIRouter(prefix="/security", tags=["security"])

# Dependency for logs_session
def get_logs_db():
    try:
        yield logs_session
    finally:
        logs_session.remove()

# Pydantic models for request bodies
class BanIPRequest(BaseModel):
    ip_address: str
    reason: str = "Manual ban"
    duration_hours: int = 24
    permanent: bool = False

class UnbanIPRequest(BaseModel):
    ip_address: str

class BanHostRequest(Baseodel):
    host: str
    reason: str = "Host ban"
    permanent: bool = False

class Clear404TrackerRequest(BaseModel):
    ip_address: str

class SecuritySettingsUpdateRequest(BaseModel):
    threshold_404: int = 20
    ban_duration_404: int = 24
    threshold_api: int = 10
    ban_duration_api: int = 48
    repeat_offender_limit: int = 3

# Main dashboard route
@security_router.get("/", response_class=HTMLResponse)
@limiter.limit("60/minute")
async def security_dashboard(
    request: Request,
    user_data: Any = Depends(check_session_validity_fastapi),
    db: Session = Depends(get_db),
    logs_db: Session = Depends(get_logs_db)
):
    """Display security dashboard with banned IPs and 404 tracking"""
    try:
        # Get security settings
        security_settings = get_security_settings(db)

        # Get all banned IPs
        banned_ips = IPBan.get_all_bans(logs_db)

        # Get suspicious IPs (1+ 404 errors to show all tracking)
        suspicious_ips = Error404Tracker.get_suspicious_ips(logs_db, min_errors=1)

        # Get suspicious API users (1+ invalid API key attempts to show all)
        suspicious_api_users = InvalidAPIKeyTracker.get_suspicious_api_users(logs_db, min_attempts=1)

        # Format data for display
        banned_data = [{
            'ip_address': ban.ip_address,
            'ban_reason': ban.ban_reason,
            'banned_at': ban.banned_at.strftime('%d-%m-%Y %I:%M:%S %p') if ban.banned_at else 'Unknown',
            'expires_at': ban.expires_at.strftime('%d-%m-%Y %I:%M:%S %p') if ban.expires_at else 'Permanent',
            'is_permanent': ban.is_permanent,
            'ban_count': ban.ban_count,
            'created_by': ban.created_by
        } for ban in banned_ips]

        suspicious_data = [{
            'ip_address': tracker.ip_address,
            'error_count': tracker.error_count,
            'first_error_at': tracker.first_error_at.strftime('%d-%m-%Y %I:%M:%S %p') if tracker.first_error_at else 'Unknown',
            'last_error_at': tracker.last_error_at.strftime('%d-%m-%Y %I:%M:%S %p') if tracker.last_error_at else 'Unknown',
            'paths_attempted': tracker.paths_attempted
        } for tracker in suspicious_ips]

        api_abuse_data = [{
            'ip_address': tracker.ip_address,
            'attempt_count': tracker.attempt_count,
            'first_attempt_at': tracker.first_attempt_at.strftime('%d-%m-%Y %I:%M:%S %p') if tracker.first_attempt_at else 'Unknown',
            'last_attempt_at': tracker.last_attempt_at.strftime('%d-%m-%Y %I:%M:%S %p') if tracker.last_attempt_at else 'Unknown',
            'api_keys_tried': tracker.api_keys_tried
        } for tracker in suspicious_api_users]

        return templates.TemplateResponse('security/dashboard.html', {
            "request": request,
            "banned_ips": banned_data,
            "suspicious_ips": suspicious_data,
            "api_abuse_ips": api_abuse_data,
            "security_settings": security_settings
        })
    except Exception as e:
        logger.error(f"Error loading security dashboard: {e}")
        # Return an empty dashboard with error message
        return templates.TemplateResponse('security/dashboard.html', {
            "request": request,
            "banned_ips": [],
            "suspicious_ips": [],
            "api_abuse_ips": [],
            "security_settings": get_security_settings(db), # Still try to get settings if possible
            "error_message": f"Error loading data: {e}"
        })

# Ban IP route
@security_router.post("/ban", response_model=Dict[str, Any])
@limiter.limit("30/minute")
async def ban_ip(
    request: Request,
    ban_request: BanIPRequest,
    user_data: Any = Depends(check_session_validity_fastapi),
    logs_db: Session = Depends(get_logs_db)
):
    """Manually ban an IP address"""
    ip_address = ban_request.ip_address.strip()
    reason = ban_request.reason.strip()
    duration_hours = ban_request.duration_hours
    permanent = ban_request.permanent

    if not ip_address:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="IP address is required")

    # Prevent banning localhost
    if ip_address in ['127.0.0.1', '::1', 'localhost']:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot ban localhost")

    try:
        success = IPBan.ban_ip(
            logs_db,
            ip_address=ip_address,
            reason=reason,
            duration_hours=duration_hours,
            permanent=permanent,
            created_by='manual'
        )

        if success:
            logger.info(f"Manual IP ban: {ip_address} - {reason}")
            return {'success': True, 'message': f'IP {ip_address} has been banned'}
        else:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail='Failed to ban IP')
    except Exception as e:
        logger.error(f"Error banning IP: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

# Unban IP route
@security_router.post("/unban", response_model=Dict[str, Any])
@limiter.limit("30/minute")
async def unban_ip(
    request: Request,
    unban_request: UnbanIPRequest,
    user_data: Any = Depends(check_session_validity_fastapi),
    logs_db: Session = Depends(get_logs_db)
):
    """Unban an IP address"""
    ip_address = unban_request.ip_address.strip()

    if not ip_address:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="IP address is required")

    try:
        success = IPBan.unban_ip(logs_db, ip_address)

        if success:
            logger.info(f"IP unbanned: {ip_address}")
            return {'success': True, 'message': f'IP {ip_address} has been unbanned'}
        else:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='IP not found in ban list')
    except Exception as e:
        logger.error(f"Error unbanning IP: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

# Ban Host route
@security_router.post("/ban-host", response_model=Dict[str, Any])
@limiter.limit("30/minute")
async def ban_host(
    request: Request,
    ban_host_request: BanHostRequest,
    user_data: Any = Depends(check_session_validity_fastapi),
    logs_db: Session = Depends(get_logs_db)
):
    """Ban by host/domain"""
    host = ban_host_request.host.strip()
    reason = ban_host_request.reason.strip()
    permanent = ban_host_request.permanent

    if not host:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Host is required")

    # Check if this looks like an IP address
    ip_pattern = re.compile(r'^(\d{1,3}\.){3}\d{1,3}$')

    if ip_pattern.match(host):
        # It's an IP address, ban it directly
        try:
            success = IPBan.ban_ip(
                logs_db,
                ip_address=host,
                reason=f"Manual ban: {reason}",
                duration_hours=24 if not permanent else None,
                permanent=permanent,
                created_by='manual'
            )
            if success:
                return {
                    'success': True,
                    'message': f'Banned IP: {host}'
                }
            else:
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f'Failed to ban IP: {host}')
        except Exception as e:
            logger.error(f"Error banning IP (from host ban): {e}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    # Get IPs from recent traffic logs that match this host
    matching_logs = logs_db.query(TrafficLog).filter(
        TrafficLog.host.like(f'%{host}%')
    ).distinct(TrafficLog.client_ip).all()

    if not matching_logs:
        logger.warning(f"Attempted to ban host {host} but no traffic found from it")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'No traffic found from host: {host}. To ban specific IPs, use the IP ban form instead.',
            headers={"Suggestion": 'Use the Manual IP Ban form above to ban specific IP addresses directly.'}
        )

    banned_count = 0
    for log in matching_logs:
        if log.client_ip and log.client_ip not in ['127.0.0.1', '::1']:
            try:
                success = IPBan.ban_ip(
                    logs_db,
                    ip_address=log.client_ip,
                    reason=f"Host ban: {host} - {reason}",
                    duration_hours=24 if not permanent else None,
                    permanent=permanent,
                    created_by='host_ban'
                )
                if success:
                    banned_count += 1
            except Exception as e:
                logger.error(f"Error banning IP {log.client_ip} during host ban: {e}")

    logger.info(f"Host ban completed: {host} - {banned_count} IPs banned")
    return {
        'success': True,
        'message': f'Banned {banned_count} IPs associated with host: {host}'
    }

# Clear 404 tracker route
@security_router.post("/clear-404", response_model=Dict[str, Any])
@limiter.limit("10/minute")
async def clear_404_tracker(
    request: Request,
    clear_request: Clear404TrackerRequest,
    user_data: Any = Depends(check_session_validity_fastapi),
    logs_db: Session = Depends(get_logs_db)
):
    """Clear 404 tracker for a specific IP"""
    ip_address = clear_request.ip_address.strip()

    if not ip_address:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="IP address is required")

    try:
        tracker = logs_db.query(Error404Tracker).filter_by(ip_address=ip_address).first()
        if tracker:
            logs_db.delete(tracker)
            logs_db.commit()
            logger.info(f"Cleared 404 tracker for IP: {ip_address}")
            return {'success': True, 'message': f'404 tracker cleared for {ip_address}'}
        else:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='No tracker found for this IP')
    except Exception as e:
        logger.error(f"Error clearing 404 tracker: {e}")
        logs_db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

# Security stats route
@security_router.get("/stats", response_model=Dict[str, Any])
@limiter.limit("60/minute")
async def security_stats(
    request: Request,
    user_data: Any = Depends(check_session_validity_fastapi),
    logs_db: Session = Depends(get_logs_db)
):
    """Get security statistics"""
    try:
        # Count banned IPs
        total_bans = logs_db.query(IPBan).count()
        permanent_bans = logs_db.query(IPBan).filter_by(is_permanent=True).count()
        temp_bans = total_bans - permanent_bans

        # Count suspicious IPs
        suspicious_count = logs_db.query(Error404Tracker).filter(
            Error404Tracker.error_count >= 5
        ).count()

        # Count IPs near threshold (15-19 404s)
        near_threshold = logs_db.query(Error404Tracker).filter(
            Error404Tracker.error_count >= 15,
            Error404Tracker.error_count < 20
        ).count()

        return {
            'total_bans': total_bans,
            'permanent_bans': permanent_bans,
            'temporary_bans': temp_bans,
            'suspicious_ips': suspicious_count,
            'near_threshold': near_threshold
        }
    except Exception as e:
        logger.error(f"Error getting security stats: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

# Update security settings route
@security_router.post("/settings", response_model=Dict[str, Any])
@limiter.limit("10/minute")
async def update_security_settings(
    request: Request,
    settings_update: SecuritySettingsUpdateRequest,
    user_data: Any = Depends(check_session_validity_fastapi),
    db: Session = Depends(get_db)
):
    """Update security threshold settings"""
    threshold_404 = settings_update.threshold_404
    ban_duration_404 = settings_update.ban_duration_404
    threshold_api = settings_update.threshold_api
    ban_duration_api = settings_update.ban_duration_api
    repeat_offender_limit = settings_update.repeat_offender_limit

    # Validate input ranges
    if not (1 <= threshold_404 <= 1000):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='404 threshold must be between 1 and 1000')
    if not (1 <= ban_duration_404 <= 8760):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Ban duration must be between 1 hour and 1 year')
    if not (1 <= threshold_api <= 100):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='API threshold must be between 1 and 100')
    if not (1 <= ban_duration_api <= 8760):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Ban duration must be between 1 hour and 1 year')
    if not (1 <= repeat_offender_limit <= 10):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Repeat offender limit must be between 1 and 10')

    try:
        set_security_settings(
            db,
            threshold_404=threshold_404,
            ban_duration_404=ban_duration_404,
            threshold_api=threshold_api,
            ban_duration_api=ban_duration_api,
            repeat_offender_limit=repeat_offender_limit
        )

        logger.info(f"Security settings updated: 404={threshold_404}/{ban_duration_404}h, API={threshold_api}/{ban_duration_api}h, Repeat={repeat_offender_limit}")

        return {
            'success': True,
            'message': 'Security settings updated successfully',
            'settings': {
                '404_threshold': threshold_404,
                '404_ban_duration': ban_duration_404,
                'api_threshold': threshold_api,
                'api_ban_duration': ban_duration_api,
                'repeat_offender_limit': repeat_offender_limit
            }
        }
    except Exception as e:
        logger.error(f"Error updating security settings: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))