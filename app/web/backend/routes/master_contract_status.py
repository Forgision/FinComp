from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.utils.logging import logger
from app.utils.session import check_session_validity_fastapi
from app.db.session import get_db

# Assuming these database functions are now in app.db
from app.db.master_contract_status_db import get_status, check_if_ready
from app.db.token_db_enhanced import get_cache_stats, clear_cache
from app.db.master_contract_cache_hook import get_cache_health, load_symbols_to_cache


master_contract_status_router = APIRouter(
    prefix="/api/master-contract",
    tags=["Master Contract Status"]
)

@master_contract_status_router.get("/status")
async def get_master_contract_status(
    request: Request,
    db: Session = Depends(get_db),
    user: Dict[str, Any] = Depends(check_session_validity_fastapi)
):
    """Get the current master contract download status"""
    try:
        broker = request.session.get('broker')
        if not broker:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="No broker session found"
            )

        status_data = await get_status(db, broker) # Assuming get_status is now async and takes db
        return JSONResponse(content=status_data, status_code=status.HTTP_200_OK)

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.error(f"Error getting master contract status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get master contract status"
        )

@master_contract_status_router.get("/ready")
async def check_master_contract_ready(
    request: Request,
    db: Session = Depends(get_db),
    user: Dict[str, Any] = Depends(check_session_validity_fastapi)
):
    """Check if master contracts are ready for trading"""
    try:
        broker = request.session.get('broker')
        if not broker:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="No broker session found"
            )
            
        is_ready = await check_if_ready(db, broker) # Assuming check_if_ready is now async and takes db
        return JSONResponse(content={
            'ready': is_ready,
            'message': 'Master contracts are ready' if is_ready else 'Master contracts not ready'
        }, status_code=status.HTTP_200_OK)
        
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.error(f"Error checking master contract readiness: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to check master contract readiness"
        )

@master_contract_status_router.get("/cache/status")
async def get_cache_status(
    db: Session = Depends(get_db),
    user: Dict[str, Any] = Depends(check_session_validity_fastapi)
):
    """Get the current symbol cache status and statistics"""
    try:
        cache_info = await get_cache_stats(db) # Assuming get_cache_stats is now async and takes db
        return JSONResponse(content=cache_info, status_code=status.HTTP_200_OK)
        
    except ImportError:
        raise HTTPException(
            status_code=status.HTTP_200_OK,
            detail={
                'status': 'not_available',
                'message': 'Enhanced cache module not available'
            }
        )
    except Exception as e:
        logger.error(f"Error getting cache status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Failed to get cache status: {str(e)}'
        )

@master_contract_status_router.get("/cache/health")
async def get_cache_health_fastapi(
    db: Session = Depends(get_db),
    user: Dict[str, Any] = Depends(check_session_validity_fastapi)
):
    """Get cache health metrics and recommendations"""
    try:
        health_info = await get_cache_health(db) # Assuming get_cache_health is now async and takes db
        return JSONResponse(content=health_info, status_code=status.HTTP_200_OK)
        
    except ImportError:
        raise HTTPException(
            status_code=status.HTTP_200_OK,
            detail={
                'health_score': 0,
                'status': 'not_available',
                'message': 'Cache health monitoring not available'
            }
        )
    except Exception as e:
        logger.error(f"Error getting cache health: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Failed to get cache health: {str(e)}'
        )

@master_contract_status_router.post("/cache/reload")
async def reload_cache_fastapi(
    request: Request,
    db: Session = Depends(get_db),
    user: Dict[str, Any] = Depends(check_session_validity_fastapi)
):
    """Manually trigger cache reload"""
    try:
        broker = request.session.get('broker')
        if not broker:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="No broker session found"
            )
        
        success = await load_symbols_to_cache(db, broker) # Assuming load_symbols_to_cache is now async and takes db
        
        if success:
            return JSONResponse(content={
                'status': 'success',
                'message': f'Cache reloaded successfully for broker: {broker}'
            }, status_code=status.HTTP_200_OK)
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail='Failed to reload cache'
            )
            
    except ImportError:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail='Cache reload functionality not available'
        )
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.error(f"Error reloading cache: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Failed to reload cache: {str(e)}'
        )

@master_contract_status_router.post("/cache/clear")
async def clear_cache_fastapi(
    db: Session = Depends(get_db),
    user: Dict[str, Any] = Depends(check_session_validity_fastapi)
):
    """Manually clear the cache"""
    try:
        await clear_cache(db) # Assuming clear_cache is now async and takes db
        
        return JSONResponse(content={
            'status': 'success',
            'message': 'Cache cleared successfully'
        }, status_code=status.HTTP_200_OK)
        
    except ImportError:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail='Cache clear functionality not available'
        )
    except Exception as e:
        logger.error(f"Error clearing cache: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Failed to clear cache: {str(e)}'
        )