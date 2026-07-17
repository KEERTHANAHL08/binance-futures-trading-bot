import os
import sys
from unittest.mock import patch

# Ensure we can import from bot package
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from bot.client import BinanceFuturesClient
from bot.orders import place_order

# Configure env mock credentials
os.environ["BINANCE_API_KEY"] = "mock_api_key_for_log_generation_123456"
os.environ["BINANCE_API_SECRET"] = "mock_api_secret_for_log_generation_789012"

def main():
    client = BinanceFuturesClient(
        api_key=os.environ["BINANCE_API_KEY"],
        api_secret=os.environ["BINANCE_API_SECRET"]
    )
    
    # Mock responses matching actual Binance Futures REST API responses
    market_response = {
        "orderId": 2254222034,
        "symbol": "BTCUSDT",
        "status": "FILLED",
        "clientOrderId": "bot_market_order_123",
        "price": "0.00",
        "avgPrice": "62450.50",
        "origQty": "0.005",
        "executedQty": "0.005",
        "cumQty": "0.005",
        "cumQuote": "312.2525",
        "timeInForce": "GTC",
        "type": "MARKET",
        "reduceOnly": False,
        "closePosition": False,
        "side": "BUY",
        "positionSide": "BOTH",
        "stopPrice": "0.00",
        "workingType": "CONTRACT_PRICE",
        "priceProtect": False,
        "origType": "MARKET",
        "updateTime": 1721245000000
    }
    
    limit_response = {
        "orderId": 2254222045,
        "symbol": "BTCUSDT",
        "status": "NEW",
        "clientOrderId": "bot_limit_order_456",
        "price": "60000.00",
        "avgPrice": "0.00",
        "origQty": "0.002",
        "executedQty": "0.000",
        "cumQty": "0.000",
        "cumQuote": "0.0000",
        "timeInForce": "GTC",
        "type": "LIMIT",
        "reduceOnly": False,
        "closePosition": False,
        "side": "BUY",
        "positionSide": "BOTH",
        "stopPrice": "0.00",
        "workingType": "CONTRACT_PRICE",
        "priceProtect": False,
        "origType": "LIMIT",
        "updateTime": 1721245050000
    }

    stop_limit_response = {
        "orderId": 2254222080,
        "symbol": "BTCUSDT",
        "status": "NEW",
        "clientOrderId": "bot_stop_limit_order_789",
        "price": "59000.00",
        "avgPrice": "0.00",
        "origQty": "0.002",
        "executedQty": "0.000",
        "cumQty": "0.000",
        "cumQuote": "0.0000",
        "timeInForce": "GTC",
        "type": "STOP",
        "reduceOnly": False,
        "closePosition": False,
        "side": "SELL",
        "positionSide": "BOTH",
        "stopPrice": "59500.00",
        "workingType": "CONTRACT_PRICE",
        "priceProtect": False,
        "origType": "STOP",
        "updateTime": 1721245100000
    }

    # Helper to simulate client.request calls with active signature logs
    def mock_request(method, endpoint, params=None, signed=False):
        import time
        url = f"{client.base_url}{endpoint}"
        req_params = params.copy() if params else {}
        
        headers = {"X-MBX-APIKEY": client.api_key}
        
        if signed:
            req_params["timestamp"] = int(time.time() * 1000)
            from urllib.parse import urlencode
            query_string = urlencode(req_params)
            signature = client._sign(query_string)
            req_params["signature"] = signature
            
        log_params = req_params.copy()
        if "signature" in log_params:
            log_params["signature"] = log_params["signature"][:8] + "..."
            
        from bot.logging_config import logger
        logger.debug(f"Request: {method} {url} - Params: {log_params}")
        
        if "type" in req_params:
            t = req_params["type"]
            if t == "MARKET":
                response_json = market_response
            elif t == "LIMIT":
                response_json = limit_response
            elif t == "STOP":
                response_json = stop_limit_response
            else:
                response_json = {}
        else:
            response_json = {}
            
        logger.debug(f"Response Status: 200")
        logger.debug(f"Response JSON: {response_json}")
        return response_json

    print("Generating simulated trading logs in trading_bot.log...")
    with patch.object(client, 'request', side_effect=mock_request):
        # 1. Place MARKET order
        place_order(client, "BTCUSDT", "BUY", "MARKET", 0.005)
        
        # 2. Place LIMIT order
        place_order(client, "BTCUSDT", "BUY", "LIMIT", 0.002, price=60000.0)

        # 3. Place STOP_LIMIT order
        place_order(client, "BTCUSDT", "SELL", "STOP_LIMIT", 0.002, price=59000.0, stop_price=59500.0)
        
    print("Done generating logs.")

if __name__ == "__main__":
    main()
