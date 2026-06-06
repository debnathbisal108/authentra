from fastapi import APIRouter
from app.api.v1.endpoints import auth, candidates, misc

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(candidates.router, prefix="/candidates", tags=["candidates"])
api_router.include_router(misc.router, prefix="", tags=["misc"])
