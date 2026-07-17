import os
import sys
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

# Ensure we import our bot package modules correctly
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from bot.client import BinanceFuturesClient, BinanceAPIError, BinanceNetworkError, BinanceError
from bot.orders import place_order, get_usdt_balance, get_ticker_price
from bot.validators import validate_order_params, ValidationError

load_dotenv()

app = FastAPI(
    title="Binance Futures Testnet Trading Dashboard",
    description="A sleek web interface to manage positions and execute orders on Binance Futures Testnet (USDT-M)."
)

# Add CORS middleware to support local development configurations
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request schema for placing an order
class OrderRequest(BaseModel):
    symbol: str
    side: str
    type: str
    quantity: float
    price: float | None = None
    stop_price: float | None = None

def get_client() -> BinanceFuturesClient:
    """Helper to initialize client with active environment variables."""
    api_key = os.getenv("BINANCE_API_KEY")
    api_secret = os.getenv("BINANCE_API_SECRET")
    
    if not api_key or not api_secret:
        raise HTTPException(
            status_code=401, 
            detail="Binance API credentials missing. Please set BINANCE_API_KEY and BINANCE_API_SECRET in environment configuration."
        )
    return BinanceFuturesClient(api_key=api_key, api_secret=api_secret)

@app.get("/", response_class=HTMLResponse)
async def read_index():
    """Serves the main HTML dashboard template."""
    index_path = os.path.join(os.path.dirname(__file__), "templates", "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return HTMLResponse("<h2>Error: Dashboard UI template index.html not found!</h2>", status_code=404)

@app.get("/api/config")
async def get_config():
    """Returns current server credentials state for UI configuration checks."""
    api_key = os.getenv("BINANCE_API_KEY")
    api_secret = os.getenv("BINANCE_API_SECRET")
    return {
        "authenticated": bool(api_key and api_secret),
        "api_key_masked": f"{api_key[:6]}...{api_key[-4:]}" if api_key else None
    }

@app.get("/api/balance")
async def fetch_balance():
    """Retrieves available USDT wallet balances."""
    try:
        client = get_client()
        bal = get_usdt_balance(client)
        return bal
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/price/{symbol}")
async def fetch_price(symbol: str):
    """Retrieves the latest ticker price for a specific symbol."""
    try:
        client = BinanceFuturesClient()  # Public pricing query does not require signing keys
        price = get_ticker_price(client, symbol)
        return {"symbol": symbol.upper(), "price": price}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/order")
async def execute_order(req: OrderRequest):
    """Validates and executes a trade order on the Binance Futures Testnet."""
    # 1. Clean and validate request inputs
    try:
        clean_params = validate_order_params(
            symbol=req.symbol,
            side=req.side,
            order_type=req.type,
            quantity=req.quantity,
            price=req.price,
            stop_price=req.stop_price
        )
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
        
    # 2. Authenticate and execute order via client
    try:
        client = get_client()
        res = place_order(
            client=client,
            symbol=clean_params["symbol"],
            side=clean_params["side"],
            order_type=clean_params["type"],
            quantity=clean_params["quantity"],
            price=clean_params.get("price"),
            stop_price=clean_params.get("stopPrice")
        )
        return res
    except BinanceAPIError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except (BinanceNetworkError, BinanceError) as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/logs")
async def get_logs(limit: int = 50):
    """Reads and returns the last N lines of trading_bot.log."""
    log_file = "trading_bot.log"
    if not os.path.exists(log_file):
        return {"logs": ["No logs generated yet."]}
    try:
        with open(log_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
        # Extract the last N lines, strip spacing
        recent_lines = [line.strip() for line in lines[-limit:]]
        return {"logs": recent_lines}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read log file: {e}")

if __name__ == "__main__":
    import uvicorn
    # Port is read dynamically to integrate with Render's PORT routing
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=True)
