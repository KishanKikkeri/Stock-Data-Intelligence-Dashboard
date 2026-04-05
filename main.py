"""
Stock Data Intelligence Dashboard
JarNox Internship Assignment
"""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn

from routers import stocks, dashboard
from data.data_loader import initialize_data


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize stock data on startup."""
    print("📦 Loading stock market data...")
    initialize_data()
    print("✅ Data loaded successfully!")
    yield


app = FastAPI(
    title="Stock Data Intelligence Dashboard",
    description="A mini financial data platform for NSE/BSE stock market analysis.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

app.include_router(stocks.router, prefix="/api", tags=["Stock Data"])
app.include_router(dashboard.router, tags=["Dashboard"])


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
