"""
Part 2 — REST API Endpoints

GET /api/companies                         → list all companies
GET /api/data/{symbol}                     → last 30 days OHLCV + metrics
GET /api/summary/{symbol}                  → 52-week high, low, avg close, volatility
GET /api/compare?symbol1=INFY&symbol2=TCS  → side-by-side performance + correlation
GET /api/gainers                           → top 5 daily gainers
GET /api/losers                            → top 5 daily losers
GET /api/sector                            → sector-wise average return
"""

import json
import sqlite3
from typing import Optional
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query

DB_PATH = Path(__file__).parent.parent / "data" / "stocks.db"

router = APIRouter()


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ──────────────────────────────────────────────────────────
# GET /api/companies
# ──────────────────────────────────────────────────────────
@router.get("/companies", summary="List all available companies")
def get_companies():
    """Returns metadata for every company in the database."""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT symbol, name, sector FROM companies ORDER BY symbol"
        ).fetchall()
    return [dict(r) for r in rows]


# ──────────────────────────────────────────────────────────
# GET /api/data/{symbol}
# ──────────────────────────────────────────────────────────
@router.get("/data/{symbol}", summary="Last 30 days of stock data")
def get_stock_data(symbol: str, days: int = Query(30, ge=1, le=365)):
    """
    Returns the last *days* (default 30) records for a given stock symbol,
    including OHLCV data and all computed metrics.
    """
    symbol = symbol.upper()
    with get_conn() as conn:
        exists = conn.execute(
            "SELECT 1 FROM companies WHERE symbol = ?", (symbol,)
        ).fetchone()
        if not exists:
            raise HTTPException(status_code=404, detail=f"Symbol '{symbol}' not found.")

        rows = conn.execute(
            """
            SELECT date, symbol, open, high, low, close, volume,
                   daily_return, ma_7, ma_30, high_52w, low_52w, volatility_score
            FROM stock_prices
            WHERE symbol = ?
            ORDER BY date DESC
            LIMIT ?
            """,
            (symbol, days),
        ).fetchall()

    data = [dict(r) for r in rows]
    data.reverse()          # chronological order
    return {"symbol": symbol, "days": days, "count": len(data), "data": data}


# ──────────────────────────────────────────────────────────
# GET /api/summary/{symbol}
# ──────────────────────────────────────────────────────────
@router.get("/summary/{symbol}", summary="52-week summary for a stock")
def get_summary(symbol: str):
    """
    Returns:
      - 52-week high and low
      - Average close price
      - Average daily return
      - Average volatility score (custom metric)
      - Latest close price
    """
    symbol = symbol.upper()
    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT
                MAX(high_52w)           AS high_52w,
                MIN(low_52w)            AS low_52w,
                ROUND(AVG(close), 2)    AS avg_close,
                ROUND(AVG(daily_return)*100, 4) AS avg_daily_return_pct,
                ROUND(AVG(volatility_score), 6) AS avg_volatility
            FROM stock_prices
            WHERE symbol = ?
            """,
            (symbol,),
        ).fetchone()
        if not row or row["high_52w"] is None:
            raise HTTPException(status_code=404, detail=f"No data for '{symbol}'.")

        latest = conn.execute(
            "SELECT close, date FROM stock_prices WHERE symbol = ? ORDER BY date DESC LIMIT 1",
            (symbol,),
        ).fetchone()

        company = conn.execute(
            "SELECT name, sector FROM companies WHERE symbol = ?", (symbol,)
        ).fetchone()

    return {
        "symbol": symbol,
        "name": company["name"] if company else symbol,
        "sector": company["sector"] if company else "N/A",
        "latest_close": latest["close"],
        "latest_date": latest["date"],
        "high_52w": row["high_52w"],
        "low_52w": row["low_52w"],
        "avg_close": row["avg_close"],
        "avg_daily_return_pct": row["avg_daily_return_pct"],
        "avg_volatility_score": row["avg_volatility"],
    }


# ──────────────────────────────────────────────────────────
# GET /api/compare
# ──────────────────────────────────────────────────────────
@router.get("/compare", summary="Compare two stocks")
def compare_stocks(
    symbol1: str = Query(..., description="First stock symbol, e.g. INFY"),
    symbol2: str = Query(..., description="Second stock symbol, e.g. TCS"),
):
    """
    Side-by-side performance comparison + Pearson correlation of daily returns.
    """
    s1, s2 = symbol1.upper(), symbol2.upper()

    def fetch_summary(symbol):
        with get_conn() as conn:
            row = conn.execute(
                """
                SELECT
                    MAX(high_52w) AS high_52w,
                    MIN(low_52w)  AS low_52w,
                    ROUND(AVG(close), 2) AS avg_close,
                    ROUND(AVG(daily_return)*100, 4) AS avg_daily_return_pct,
                    ROUND(AVG(volatility_score), 6) AS avg_volatility
                FROM stock_prices WHERE symbol = ?
                """,
                (symbol,),
            ).fetchone()
            latest = conn.execute(
                "SELECT close FROM stock_prices WHERE symbol = ? ORDER BY date DESC LIMIT 1",
                (symbol,),
            ).fetchone()
        if not row or row["high_52w"] is None:
            raise HTTPException(status_code=404, detail=f"No data for '{symbol}'.")
        return {**dict(row), "latest_close": latest["close"]}

    # Fetch correlation from cache
    with get_conn() as conn:
        cache = conn.execute("SELECT json FROM correlation_cache").fetchone()
    corr_val = None
    if cache:
        corr_matrix = json.loads(cache["json"])
        corr_val = corr_matrix.get(s1, {}).get(s2)

    return {
        symbol1: fetch_summary(s1),
        symbol2: fetch_summary(s2),
        "correlation": corr_val,
        "interpretation": (
            "Strong positive correlation" if corr_val and corr_val > 0.7
            else "Moderate correlation" if corr_val and corr_val > 0.4
            else "Weak or no correlation"
        ),
    }


# ──────────────────────────────────────────────────────────
# GET /api/gainers  &  GET /api/losers
# ──────────────────────────────────────────────────────────
@router.get("/gainers", summary="Top 5 daily gainers")
def get_gainers():
    """Returns the 5 stocks with the highest daily_return on the latest available date."""
    return _top_movers(order="DESC")


@router.get("/losers", summary="Top 5 daily losers")
def get_losers():
    """Returns the 5 stocks with the lowest daily_return on the latest available date."""
    return _top_movers(order="ASC")


def _top_movers(order: str):
    with get_conn() as conn:
        latest_date = conn.execute(
            "SELECT MAX(date) AS d FROM stock_prices"
        ).fetchone()["d"]
        rows = conn.execute(
            f"""
            SELECT sp.symbol, c.name, sp.close, sp.daily_return
            FROM stock_prices sp
            JOIN companies c ON sp.symbol = c.symbol
            WHERE sp.date = ?
            ORDER BY sp.daily_return {order}
            LIMIT 5
            """,
            (latest_date,),
        ).fetchall()
    return {"date": latest_date, "data": [dict(r) for r in rows]}


# ──────────────────────────────────────────────────────────
# GET /api/sector
# ──────────────────────────────────────────────────────────
@router.get("/sector", summary="Sector-wise average daily return")
def get_sector_performance():
    """Custom analysis: aggregate average daily return grouped by sector."""
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT c.sector,
                   ROUND(AVG(sp.daily_return)*100, 4) AS avg_return_pct,
                   ROUND(AVG(sp.volatility_score), 6) AS avg_volatility,
                   COUNT(DISTINCT sp.symbol) AS num_stocks
            FROM stock_prices sp
            JOIN companies c ON sp.symbol = c.symbol
            WHERE sp.daily_return IS NOT NULL
            GROUP BY c.sector
            ORDER BY avg_return_pct DESC
            """,
        ).fetchall()
    return [dict(r) for r in rows]
