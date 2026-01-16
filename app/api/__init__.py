from fastapi import APIRouter

router = APIRouter()

# Import and include route modules
from app.api import ai_routes
from app.api import news_routes
from app.api import gif_routes
from app.api import activecampaign_routes

router.include_router(ai_routes.router, prefix="/ai", tags=["AI"])
router.include_router(news_routes.router, prefix="/news", tags=["News"])
router.include_router(gif_routes.router, tags=["GIFs"])
router.include_router(activecampaign_routes.router, prefix="/activecampaign", tags=["ActiveCampaign"])

