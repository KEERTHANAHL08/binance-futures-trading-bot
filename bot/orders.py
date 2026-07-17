from bot.client import BinanceFuturesClient, BinanceError
from bot.logging_config import logger

def get_ticker_price(client: BinanceFuturesClient, symbol: str) -> float:
    """
    Fetches the current ticker price for a specific symbol.
    """
    endpoint = "/fapi/v1/ticker/price"
    params = {"symbol": symbol.upper()}
    try:
        response = client.request("GET", endpoint, params=params, signed=False)
        price = float(response.get("price", 0.0))
        logger.debug(f"Ticker price for {symbol}: {price}")
        return price
    except BinanceError as e:
        logger.error(f"Failed to fetch ticker price for {symbol}: {e}")
        raise

def get_usdt_balance(client: BinanceFuturesClient) -> dict:
    """
    Fetches USDT balance details from the futures account.
    Returns a dictionary with balance information, or raises BinanceError.
    """
    endpoint = "/fapi/v2/balance"
    try:
        balances = client.request("GET", endpoint, signed=True)
        # Search for USDT asset
        for item in balances:
            if item.get("asset") == "USDT":
                logger.debug(f"USDT Balance Info: {item}")
                return {
                    "asset": "USDT",
                    "balance": float(item.get("balance", 0.0)),
                    "available_balance": float(item.get("availableBalance", 0.0)),
                    "max_withdraw": float(item.get("maxWithdrawAmount", 0.0))
                }
        # If USDT is not found, return a default zero balance structure
        return {"asset": "USDT", "balance": 0.0, "available_balance": 0.0, "max_withdraw": 0.0}
    except BinanceError as e:
        logger.error(f"Failed to fetch balance: {e}")
        raise

def place_order(
    client: BinanceFuturesClient,
    symbol: str,
    side: str,
    order_type: str,
    quantity: float,
    price: float | None = None,
    stop_price: float | None = None,
    time_in_force: str = "GTC"
) -> dict:
    """
    Core function to place an order on Binance Futures.
    
    :param client: BinanceFuturesClient instance
    :param symbol: Symbol name (e.g. BTCUSDT)
    :param side: BUY or SELL
    :param order_type: MARKET, LIMIT, or STOP_LIMIT
    :param quantity: Order quantity
    :param price: Price (required for LIMIT / STOP_LIMIT)
    :param stop_price: Stop price (required for STOP_LIMIT)
    :param time_in_force: Time in Force policy (GTC, IOC, etc.)
    :return: Order response dictionary containing status, orderId, etc.
    """
    endpoint = "/fapi/v1/order"
    
    # Base parameters for all orders
    params = {
        "symbol": symbol.upper(),
        "side": side.upper(),
        "quantity": str(quantity),
    }

    # Set parameters depending on order type
    if order_type.upper() == "MARKET":
        params["type"] = "MARKET"
        
    elif order_type.upper() == "LIMIT":
        params["type"] = "LIMIT"
        params["price"] = str(price)
        params["timeInForce"] = time_in_force
        
    elif order_type.upper() == "STOP_LIMIT":
        # In Binance Futures, a Stop Limit order is type STOP
        params["type"] = "STOP"
        params["price"] = str(price)
        params["stopPrice"] = str(stop_price)
        params["timeInForce"] = time_in_force
        
    else:
        raise ValueError(f"Unsupported order type: {order_type}")

    logger.info(f"Placing {order_type.upper()} {side.upper()} order for {quantity} {symbol}...")
    
    try:
        response = client.request("POST", endpoint, params=params, signed=True)
        logger.info(f"Successfully placed order. OrderId: {response.get('orderId')}, Status: {response.get('status')}")
        return response
    except BinanceError as e:
        logger.error(f"Failed to place order: {e}")
        raise
