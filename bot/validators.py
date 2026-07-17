class ValidationError(ValueError):
    """Exception raised when user input or command line validation fails."""
    pass

def validate_symbol(symbol: str) -> str:
    """Validates and clean the trading symbol."""
    if not symbol:
        raise ValidationError("Symbol cannot be empty.")
    
    cleaned = symbol.strip().upper()
    if not cleaned.isalnum():
        raise ValidationError(f"Symbol '{symbol}' must be alphanumeric.")
    return cleaned

def validate_side(side: str) -> str:
    """Validates and clean the order side."""
    if not side:
        raise ValidationError("Side cannot be empty.")
    
    cleaned = side.strip().upper()
    if cleaned not in ("BUY", "SELL"):
        raise ValidationError(f"Side must be 'BUY' or 'SELL', got '{side}'.")
    return cleaned

def validate_order_type(order_type: str) -> str:
    """Validates and clean the order type."""
    if not order_type:
        raise ValidationError("Order type cannot be empty.")
    
    cleaned = order_type.strip().upper()
    if cleaned not in ("MARKET", "LIMIT", "STOP_LIMIT"):
        raise ValidationError(f"Order type must be 'MARKET', 'LIMIT', or 'STOP_LIMIT', got '{order_type}'.")
    return cleaned

def validate_quantity(quantity: str | float) -> float:
    """Validates and clean the quantity."""
    try:
        val = float(quantity)
    except (ValueError, TypeError):
        raise ValidationError(f"Quantity must be a numeric value, got '{quantity}'.")
    
    if val <= 0:
        raise ValidationError(f"Quantity must be greater than zero, got '{val}'.")
    return val

def validate_price(price: str | float) -> float:
    """Validates and clean the price."""
    try:
        val = float(price)
    except (ValueError, TypeError):
        raise ValidationError(f"Price must be a numeric value, got '{price}'.")
    
    if val <= 0:
        raise ValidationError(f"Price must be greater than zero, got '{val}'.")
    return val

def validate_order_params(
    symbol: str, 
    side: str, 
    order_type: str, 
    quantity: str | float, 
    price: str | float | None = None, 
    stop_price: str | float | None = None
) -> dict:
    """
    Validates all inputs for placing an order and returns a dictionary 
    of cleaned and typed parameters.
    """
    params = {
        "symbol": validate_symbol(symbol),
        "side": validate_side(side),
        "type": validate_order_type(order_type),
        "quantity": validate_quantity(quantity)
    }
    
    if params["type"] == "LIMIT":
        if price is None:
            raise ValidationError("Price is required for LIMIT orders.")
        params["price"] = validate_price(price)
        
    elif params["type"] == "STOP_LIMIT":
        if price is None:
            raise ValidationError("Price is required for STOP_LIMIT orders.")
        if stop_price is None:
            raise ValidationError("Stop price is required for STOP_LIMIT orders.")
        params["price"] = validate_price(price)
        params["stopPrice"] = validate_price(stop_price)
        
    return params
