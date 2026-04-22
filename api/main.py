"""
Blinkit Scout — FastAPI Backend
Wraps the Selenium scraper and exposes a /scrape POST endpoint.
Run: uvicorn main:app --reload --port 8000
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any
import asyncio
import logging
from scraper import run_scrape  # the actual scraping logic

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("blinkit-scout")

app = FastAPI(
    title="Blinkit Scout API",
    description="Scrapes Blinkit search results with inventory counts",
    version="1.0.0"
)

# Allow your frontend origin (update in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # tighten to your Vercel URL in prod
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


class ScrapeRequest(BaseModel):
    keyword: str
    pincode: str


class ScrapeResponse(BaseModel):
    keyword: str
    pincode: str
    products: List[Dict[str, Any]]
    total: int


@app.get("/")
async def root():
    return {"status": "ok", "service": "Blinkit Scout API"}


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.post("/scrape", response_model=ScrapeResponse)
async def scrape(req: ScrapeRequest):
    keyword = req.keyword.strip()
    pincode = req.pincode.strip()

    if not keyword:
        raise HTTPException(status_code=400, detail="keyword is required")
    if not pincode or not pincode.isdigit() or len(pincode) != 6:
        raise HTTPException(status_code=400, detail="pincode must be a 6-digit number")

    logger.info(f"Scraping: keyword='{keyword}' pin='{pincode}'")

    try:
        # Run selenium in thread pool so we don't block the event loop
        loop = asyncio.get_event_loop()
        products = await loop.run_in_executor(None, run_scrape, keyword, pincode)
        logger.info(f"Done. Found {len(products)} products.")
        return ScrapeResponse(
            keyword=keyword,
            pincode=pincode,
            products=products,
            total=len(products)
        )
    except Exception as e:
        logger.error(f"Scrape failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
