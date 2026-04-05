"""
Data Collection & Preparation Module (Part 1)

Fetches real stock data using yfinance, cleans it, and computes:
  - Daily Return
  - 7-day Moving Average
  - 52-week High / Low
  - Volatility Score (custom metric)
  - Correlation Matrix between stocks
"""

import os
import json
import sqlite3
import numpy as np
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
from pathlib import Path

DB_PATH = Path(__file__).parent / "stocks.db"

# Top NSE/Indian stocks with their Yahoo Finance tickers
COMPANIES = {
    "RELIANCE": {"name": "Reliance Industries", "sector": "Energy"},
    "TCS":      {"name": "Tata Consultancy Services", "sector": "IT"},
    "INFY":     {"name": "Infosys", "sector": "IT"},
    "HDFCBANK": {"name": "HDFC Bank", "sector": "Banking"},
    "ICICIBANK":{"name": "ICICI Bank", "sector": "Banking"},
    "WIPRO":    {"name": "Wipro", "sector": "IT"},
    "SBIN":     {"name": "State Bank of India", "sector": "Banking"},
    "HINDUNILVR":{"name":"Hindustan Unilever", "sector": "FMCG"},
    "BAJFINANCE":{"name":"Bajaj Finance", "sector": "Finance"},
    "HCLTECH":  {"name": "HCL Technologies", "sector": "IT"},
}

TICKER_MAP = {k: f"{k}.NS" for k in COMPANIES}  # NSE suffix


def get_connection() -> sqlite3.Connection:
    return sqlite3.connect(DB_PATH)


def fetch_stock_data(symbol: str, period: str = "1y") -> pd.DataFrame:
    """Download OHLCV data from Yahoo Finance for an NSE stock."""
    ticker = TICKER_MAP.get(symbol, f"{symbol}.NS")
    try:
        df = yf.download(ticker, period=period, progress=False, auto_adjust=True)
        if df.empty:
            raise ValueError(f"No data for {ticker}")
        # Flatten MultiIndex columns if present
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df.index.name = "Date"
        df = df.reset_index()
        df["Date"] = pd.to_datetime(df["Date"]).dt.date
        df = df.rename(columns={
            "Open": "open", "High": "high", "Low": "low",
            "Close": "close", "Volume": "volume"
        })
        df["symbol"] = symbol
        return df[["Date", "symbol", "open", "high", "low", "close", "volume"]]
    except Exception as e:
        print(f"  ⚠️  Failed to fetch {symbol}: {e}")
        return pd.DataFrame()


def add_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute all required and custom metrics:
      - daily_return      : (close - open) / open
      - ma_7              : 7-day simple moving average of close
      - ma_30             : 30-day simple moving average
      - high_52w          : rolling 52-week high
      - low_52w           : rolling 52-week low
      - volatility_score  : 14-day rolling std of daily_return (custom)
    """
    df = df.copy().sort_values("Date").reset_index(drop=True)

    df["daily_return"]     = (df["close"] - df["open"]) / df["open"]
    df["ma_7"]             = df["close"].rolling(7).mean()
    df["ma_30"]            = df["close"].rolling(30).mean()
    df["high_52w"]         = df["close"].rolling(252, min_periods=1).max()
    df["low_52w"]          = df["close"].rolling(252, min_periods=1).min()
    df["volatility_score"] = df["daily_return"].rolling(14).std()   # Custom metric

    # Round to 4 decimal places
    float_cols = ["open","high","low","close","daily_return",
                  "ma_7","ma_30","high_52w","low_52w","volatility_score"]
    df[float_cols] = df[float_cols].round(4)
    return df


def create_db_schema(conn: sqlite3.Connection):
    conn.execute("DROP TABLE IF EXISTS stock_prices")
    conn.execute("DROP TABLE IF EXISTS companies")
    conn.execute("""
        CREATE TABLE companies (
            symbol      TEXT PRIMARY KEY,
            name        TEXT NOT NULL,
            sector      TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE stock_prices (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            date             TEXT NOT NULL,
            symbol           TEXT NOT NULL,
            open             REAL,
            high             REAL,
            low              REAL,
            close            REAL,
            volume           INTEGER,
            daily_return     REAL,
            ma_7             REAL,
            ma_30            REAL,
            high_52w         REAL,
            low_52w          REAL,
            volatility_score REAL,
            FOREIGN KEY(symbol) REFERENCES companies(symbol)
        )
    """)
    conn.commit()


def save_to_db(conn: sqlite3.Connection, symbol: str, df: pd.DataFrame):
    df["date"] = df["Date"].astype(str)
    rows = df[["date","symbol","open","high","low","close","volume",
               "daily_return","ma_7","ma_30","high_52w","low_52w","volatility_score"]].to_dict("records")
    conn.executemany("""
        INSERT INTO stock_prices
            (date,symbol,open,high,low,close,volume,
             daily_return,ma_7,ma_30,high_52w,low_52w,volatility_score)
        VALUES
            (:date,:symbol,:open,:high,:low,:close,:volume,
             :daily_return,:ma_7,:ma_30,:high_52w,:low_52w,:volatility_score)
    """, rows)
    conn.commit()


def compute_correlation_matrix(conn: sqlite3.Connection) -> dict:
    """
    Custom metric: Pearson correlation of daily returns between all stocks.
    Stored as JSON in a separate table for the /compare endpoint.
    """
    df = pd.read_sql(
        "SELECT symbol, date, daily_return FROM stock_prices WHERE daily_return IS NOT NULL",
        conn
    )
    pivot = df.pivot(index="date", columns="symbol", values="daily_return").dropna()
    corr = pivot.corr().round(4)
    return corr.to_dict()


def initialize_data():
    """Full pipeline: fetch → clean → transform → store."""
    conn = get_connection()
    create_db_schema(conn)

    # Insert company metadata
    for symbol, info in COMPANIES.items():
        conn.execute(
            "INSERT INTO companies (symbol, name, sector) VALUES (?, ?, ?)",
            (symbol, info["name"], info["sector"])
        )
    conn.commit()

    # Fetch + process each stock
    for symbol in COMPANIES:
        print(f"  ↓  Fetching {symbol}...")
        raw_df = fetch_stock_data(symbol, period="1y")
        if raw_df.empty:
            continue
        enriched = add_metrics(raw_df)
        save_to_db(conn, symbol, enriched)

    # Store correlation matrix as a JSON blob
    corr = compute_correlation_matrix(conn)
    conn.execute("DROP TABLE IF EXISTS correlation_cache")
    conn.execute("CREATE TABLE correlation_cache (json TEXT)")
    conn.execute("INSERT INTO correlation_cache VALUES (?)", (json.dumps(corr),))
    conn.commit()
    conn.close()
    print("  ✅ Database ready at", DB_PATH)
