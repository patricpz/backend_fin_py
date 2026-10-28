import time
from fastapi import APIRouter

router = APIRouter(tags=["health"])

START_TIME = time.time()


@router.get("/health")
async def health_check():
    uptime = round(time.time() - START_TIME, 2)
    return {"status": "ok", "uptime": uptime}