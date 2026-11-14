from fastapi import APIRouter
from backend.app.services.data import load_json
router = APIRouter(prefix="/api", tags=["targets"])
@router.get("/targets")
def targets(): return load_json("targets.json")
