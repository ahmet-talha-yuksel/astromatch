from fastapi import APIRouter
from .routes import health, targets, candidates
router = APIRouter()
router.include_router(health.router)
router.include_router(targets.router)
router.include_router(candidates.router)
