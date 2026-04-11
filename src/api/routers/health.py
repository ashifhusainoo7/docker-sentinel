from fastapi import APIRouter, Response

from src.services.metrics import get_metrics

router = APIRouter()


@router.get("/health")
async def health_check():
    return {"status": "healthy", "service": "docker-sentinel-api"}


@router.get("/metrics")
async def prometheus_metrics():
    return Response(content=get_metrics(), media_type="text/plain")
