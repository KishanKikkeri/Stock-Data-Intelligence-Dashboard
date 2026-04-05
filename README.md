# 📈 Stock Data Intelligence Dashboard
### JarNox Internship Assignment — Full Solution

A mini financial data platform that collects real NSE stock market data,
exposes a REST API via **FastAPI**, and visualises insights in a polished
dark-terminal web dashboard.

---

## ✨ Features

| Part | Feature | Status |
|------|---------|--------|
| 1 | Real data via `yfinance` (NSE stocks, 1 year) | ✅ |
| 1 | Data cleaning & date handling with Pandas | ✅ |
| 1 | Daily Return, 7-day MA, 30-day MA, 52W High/Low | ✅ |
| 1 | **Custom: 14-day Volatility Score** (σ of returns) | ✅ |
| 1 | **Custom: Cross-stock Correlation Matrix** | ✅ |
| 2 | `GET /api/companies` | ✅ |
| 2 | `GET /api/data/{symbol}?days=N` | ✅ |
| 2 | `GET /api/summary/{symbol}` | ✅ |
| 2 | `GET /api/compare?symbol1=X&symbol2=Y` | ✅ |
| 2 | `GET /api/gainers` / `GET /api/losers` | ✅ |
| 2 | `GET /api/sector` | ✅ |
| 2 | Swagger / ReDoc auto-docs | ✅ |
| 3 | Dark financial terminal dashboard | ✅ |
| 3 | Interactive price chart (Close + MA7 + MA30) | ✅ |
| 3 | Time filter: 30D / 60D / 90D / 6M / 1Y | ✅ |
| 3 | Top Gainers / Losers panel | ✅ |
| 3 | Stock comparison with correlation bar | ✅ |
| 3 | Sector-wise performance bars | ✅ |

---

## 🗂 Project Structure

```
stock-dashboard/
├── main.py                  # FastAPI app entry point
├── requirements.txt
├── README.md
├── data/
│   ├── __init__.py
│   ├── data_loader.py       # Part 1 — data pipeline
│   └── stocks.db            # SQLite database (auto-generated)
├── routers/
│   ├── __init__.py
│   ├── stocks.py            # Part 2 — REST API endpoints
│   └── dashboard.py         # Serves the HTML dashboard
├── templates/
│   └── index.html           # Part 3 — frontend dashboard
└── static/                  # (static assets folder, reserved)
```

---

## 🚀 Setup & Run

### 1. Clone and install dependencies

```bash
git clone https://github.com/KishanKikkeri/stock-dashboard.git
cd stock-dashboard

python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

### 2. Start the server

```bash
python main.py
```

On first launch the app will:
1. Download ~1 year of data for **10 NSE stocks** via `yfinance`
2. Clean and compute all metrics
3. Save everything to `data/stocks.db` (SQLite)
4. Start the API server on `http://localhost:8000`

> **Note:** First startup takes ~30-60 seconds depending on internet speed.
> Subsequent starts are instant (data is cached in SQLite).

### 3. Open the dashboard

```
http://localhost:8000/
```

### 4. Explore the API docs

```
http://localhost:8000/docs       # Swagger UI
http://localhost:8000/redoc      # ReDoc
```

---

## 📡 API Reference

### `GET /api/companies`
Returns all available companies with symbol, name, and sector.

```json
[
  { "symbol": "TCS", "name": "Tata Consultancy Services", "sector": "IT" },
  ...
]
```

---

### `GET /api/data/{symbol}?days=30`
Returns the last N days of OHLCV data plus computed metrics.

```json
{
  "symbol": "INFY",
  "days": 30,
  "count": 21,
  "data": [
    {
      "date": "2024-10-01",
      "open": 1850.5,
      "close": 1862.3,
      "daily_return": 0.00638,
      "ma_7": 1855.4,
      "ma_30": 1841.2,
      "volatility_score": 0.0091
    },
    ...
  ]
}
```

---

### `GET /api/summary/{symbol}`
Returns 52-week high/low, averages, and latest close.

```json
{
  "symbol": "TCS",
  "name": "Tata Consultancy Services",
  "high_52w": 4592.0,
  "low_52w": 3311.85,
  "avg_close": 3978.43,
  "avg_daily_return_pct": 0.018,
  "avg_volatility_score": 0.0092
}
```

---

### `GET /api/compare?symbol1=INFY&symbol2=TCS`
Side-by-side comparison plus Pearson correlation of daily returns.

```json
{
  "INFY": { "latest_close": 1862.3, "high_52w": 1998.0, ... },
  "TCS":  { "latest_close": 3891.0, "high_52w": 4592.0, ... },
  "correlation": 0.847,
  "interpretation": "Strong positive correlation"
}
```

---

### `GET /api/gainers` / `GET /api/losers`
Top 5 daily price movers on the latest available trading date.

---

### `GET /api/sector`
Aggregated avg daily return and volatility grouped by sector.

---

## 🧠 Custom Metrics (Part 1 Creativity)

### 1. Volatility Score
```
volatility_score = rolling_std(daily_return, window=14)
```
Measures how erratic a stock's daily returns have been over the past
14 trading sessions. Higher = more volatile / risky.

### 2. Correlation Matrix
Pearson correlation of daily returns between every pair of stocks.
Computed at startup and cached in the database. Used by `/api/compare`.

```python
pivot = df.pivot(index='date', columns='symbol', values='daily_return')
corr_matrix = pivot.corr()
```

---

## 📊 Tech Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.10+ |
| Web Framework | FastAPI 0.111 |
| Server | Uvicorn (ASGI) |
| Database | SQLite (via stdlib `sqlite3`) |
| Data | yfinance, Pandas, NumPy |
| Frontend | HTML5 + Vanilla JS |
| Charts | Chart.js 4 |
| Fonts | IBM Plex Mono, Space Grotesk |
| API Docs | Swagger UI (built into FastAPI) |

---

## 🌐 Stocks Covered

| Symbol | Company | Sector |
|--------|---------|--------|
| RELIANCE | Reliance Industries | Energy |
| TCS | Tata Consultancy Services | IT |
| INFY | Infosys | IT |
| HDFCBANK | HDFC Bank | Banking |
| ICICIBANK | ICICI Bank | Banking |
| WIPRO | Wipro | IT |
| SBIN | State Bank of India | Banking |
| HINDUNILVR | Hindustan Unilever | FMCG |
| BAJFINANCE | Bajaj Finance | Finance |
| HCLTECH | HCL Technologies | IT |

---

## 💡 Design Decisions

- **SQLite over PostgreSQL** — zero-setup, portable, sufficient for this scale.
  Switching to PostgreSQL requires only changing the `get_connection()` call in
  `data_loader.py` and `routers/stocks.py`.
- **yfinance `.NS` suffix** — Yahoo Finance uses `SYMBOL.NS` for NSE-listed stocks.
- **Lifespan handler** — FastAPI's `lifespan` context manager ensures data loads
  once at startup (not on every request).
- **Correlation cache** — computed once at startup and stored as a JSON blob to
  avoid expensive re-computation on every `/compare` call.


---

*Built with ❤️ using FastAPI + yfinance + Chart.js*
