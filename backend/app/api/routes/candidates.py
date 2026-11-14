from fastapi import APIRouter
from backend.app.services.data import load_json
router = APIRouter(prefix="/api", tags=["candidates"])
@router.get("/candidates")
def candidates(): return load_json("candidates.json")
