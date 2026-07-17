import os
import sys
from dotenv import load_dotenv
import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt, Confirm

# Add current path to import path to avoid package resolution issues
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from bot.client import BinanceFuturesClient, BinanceAPIError, BinanceNetworkError
from bot.orders import place_order, get_usdt_balance, get_ticker_price
from bot.validators import validate_order_params, ValidationError
from bot.logging_config import logger

# Load environment variables from .env
load_dotenv()

console = Console()

def get_credentials(interactive: bool = False) -> tuple[str, str]:
    """Retrieves Binance API Key and Secret from environment, or prompts user if interactive."""
    api_key = os.getenv("BINANCE_API_KEY")
    api_secret = os.getenv("BINANCE_API_SECRET")
    
    if not api_key or not api_secret:
        if interactive:
            console.print("[yellow]Binance API Credentials not found in environment or .env file.[/yellow]")
            if not api_key:
                api_key = Prompt.ask("Enter your Binance Futures Testnet API Key", password=True)
            if not api_secret:
                api_secret = Prompt.ask("Enter your Binance Futures Testnet API Secret", password=True)
        else:
            console.print("[bold red]Error: Binance API Key or API Secret not found in environment.[/bold red]")
            console.print("Please set them in a [bold].env[/bold] file or export them as environment variables:")
            console.print("  export BINANCE_API_KEY='your_key'")
            console.print("  export BINANCE_API_SECRET='your_secret'")
            sys.exit(1)
            
    return api_key or "", api_secret or ""

@click.group()
def cli():
    """Simplified Binance Futures Testnet Trading Bot."""
    pass

@cli.command()
@click.option("--symbol", "-s", required=True, help="Trading symbol, e.g. BTCUSDT")
@click.option("--side", "-d", required=True, type=click.Choice(["BUY", "SELL"], case_sensitive=False), help="Order side")
@click.option("--type", "-t", "order_type", required=True, type=click.Choice(["MARKET", "LIMIT", "STOP_LIMIT"], case_sensitive=False), help="Order type")
@click.option("--quantity", "-q", required=True, help="Order quantity")
@click.option("--price", "-p", help="Order price (required for LIMIT and STOP_LIMIT)")
@click.option("--stop-price", "stop_price", help="Trigger stop price (required for STOP_LIMIT)")
def place(symbol: str, side: str, order_type: str, quantity: str, price: str | None, stop_price: str | None):
    """Place an order with command line options."""
    # 1. Retrieve credentials
    api_key, api_secret = get_credentials(interactive=False)
    
    # 2. Validate Inputs
    try:
        clean_params = validate_order_params(
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=quantity,
            price=price,
            stop_price=stop_price
        )
    except ValidationError as e:
        console.print(f"[bold red]Validation Error:[/bold red] {e}")
        logger.error(f"CLI Input validation failed: {e}")
        sys.exit(1)
        
    # 3. Print Request Summary
    summary_table = Table(title="Order Execution Request Details", show_header=False, title_justify="left")
    summary_table.add_column("Property", style="cyan")
    summary_table.add_column("Value", style="magenta")
    summary_table.add_row("Symbol", clean_params["symbol"])
    summary_table.add_row("Side", clean_params["side"])
    summary_table.add_row("Type", clean_params["type"])
    summary_table.add_row("Quantity", str(clean_params["quantity"]))
    if "price" in clean_params:
        summary_table.add_row("Price", f"{clean_params['price']} USDT")
    if "stopPrice" in clean_params:
        summary_table.add_row("Stop Price", f"{clean_params['stopPrice']} USDT")
        
    console.print(summary_table)
    
    # 4. Initialize Client & Call API
    client = BinanceFuturesClient(api_key=api_key, api_secret=api_secret)
    
    try:
        res = place_order(
            client=client,
            symbol=clean_params["symbol"],
            side=clean_params["side"],
            order_type=clean_params["type"],
            quantity=clean_params["quantity"],
            price=clean_params.get("price"),
            stop_price=clean_params.get("stopPrice")
        )
        
        # Format and display order placement response
        show_order_success(res)
        
    except (BinanceAPIError, BinanceNetworkError, BinanceError) as e:
        console.print(Panel(f"[bold red]Execution Failed:[/bold red]\n{e}", title="Error Status", border_style="red"))
        sys.exit(1)

@cli.command()
def balance():
    """Retrieve and display USDT Futures balance."""
    api_key, api_secret = get_credentials(interactive=False)
    client = BinanceFuturesClient(api_key=api_key, api_secret=api_secret)
    
    try:
        with console.status("[bold green]Fetching futures balance...") as status:
            bal = get_usdt_balance(client)
            
        bal_table = Table(title="USDT-M Futures Wallet Balance", header_style="bold green")
        bal_table.add_column("Asset")
        bal_table.add_column("Total Balance")
        bal_table.add_column("Available Balance")
        bal_table.add_column("Max Withdraw")
        
        bal_table.add_row(
            bal["asset"],
            f"{bal['balance']:.4f} USDT",
            f"{bal['available_balance']:.4f} USDT",
            f"{bal['max_withdraw']:.4f} USDT"
        )
        console.print(bal_table)
        
    except Exception as e:
        console.print(f"[bold red]Failed to fetch balance:[/bold red] {e}")
        sys.exit(1)

@cli.command()
@click.argument("symbol")
def price(symbol: str):
    """Retrieve the current ticker price of a symbol."""
    client = BinanceFuturesClient()
    try:
        with console.status(f"[bold green]Fetching price for {symbol}...") as status:
            ticker_price = get_ticker_price(client, symbol)
        console.print(f"Current price of [bold cyan]{symbol.upper()}[/bold cyan] is [bold green]{ticker_price:.4f} USDT[/bold green]")
    except Exception as e:
        console.print(f"[bold red]Failed to fetch price:[/bold red] {e}")
        sys.exit(1)

@cli.command()
def interactive():
    """Launch the interactive terminal menu."""
    console.print(Panel("[bold green]Binance Futures Testnet Trading Bot[/bold green]\nInteractive order placement assistant.", border_style="green"))
    
    # 1. Retrieve credentials
    api_key, api_secret = get_credentials(interactive=True)
    client = BinanceFuturesClient(api_key=api_key, api_secret=api_secret)
    
    # Check balance first to verify connectivity
    try:
        with console.status("[bold green]Connecting to testnet & loading balance...") as status:
            bal = get_usdt_balance(client)
        console.print(f"Connected. Current Available Wallet Balance: [bold green]{bal['available_balance']:.2f} USDT[/bold green]\n")
    except Exception as e:
        console.print(f"[bold red]Failed to connect with credentials:[/bold red] {e}")
        sys.exit(1)
        
    # 2. Interactive Prompts
    symbol = Prompt.ask("Enter Symbol (e.g. BTCUSDT)", default="BTCUSDT").upper()
    
    # Fetch current price to help user pick values
    try:
        ticker_price = get_ticker_price(client, symbol)
        console.print(f"Current Ticker Price for {symbol}: [bold yellow]{ticker_price:.4f} USDT[/bold yellow]")
    except Exception:
        ticker_price = None
        console.print("[warning]Could not fetch ticker price for this symbol. Proceeding anyway.[/warning]")
        
    side = Prompt.ask("Choose Side", choices=["BUY", "SELL"], default="BUY").upper()
    order_type = Prompt.ask("Choose Order Type", choices=["MARKET", "LIMIT", "STOP_LIMIT"], default="MARKET").upper()
    quantity = Prompt.ask("Enter Quantity (units/contracts)")
    
    price = None
    stop_price = None
    
    if order_type in ("LIMIT", "STOP_LIMIT"):
        price_default = f"{ticker_price:.4f}" if ticker_price else None
        price = Prompt.ask("Enter Price (USDT)", default=price_default)
        
    if order_type == "STOP_LIMIT":
        stop_price = Prompt.ask("Enter Trigger Stop Price (USDT)")
        
    # 3. Validation
    try:
        clean_params = validate_order_params(
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=quantity,
            price=price,
            stop_price=stop_price
        )
    except ValidationError as e:
        console.print(f"\n[bold red]Validation Error:[/bold red] {e}")
        logger.error(f"Interactive validation failed: {e}")
        return
        
    # 4. Confirmation
    console.print("\n[bold]Verify Order Details:[/bold]")
    confirm_table = Table(show_header=False)
    confirm_table.add_column("Property", style="cyan")
    confirm_table.add_column("Value", style="magenta")
    confirm_table.add_row("Symbol", clean_params["symbol"])
    confirm_table.add_row("Side", clean_params["side"])
    confirm_table.add_row("Type", clean_params["type"])
    confirm_table.add_row("Quantity", str(clean_params["quantity"]))
    if "price" in clean_params:
        confirm_table.add_row("Price", f"{clean_params['price']} USDT")
        # Estimate order cost
        est_cost = clean_params["quantity"] * clean_params["price"]
        confirm_table.add_row("Est. Order Size", f"{est_cost:.2f} USDT")
    if "stopPrice" in clean_params:
        confirm_table.add_row("Stop Price", f"{clean_params['stopPrice']} USDT")
        
    console.print(confirm_table)
    
    confirm = Confirm.ask("Do you want to submit this order to the testnet?")
    if not confirm:
        console.print("[yellow]Order cancelled.[/yellow]")
        return
        
    # 5. Place order
    try:
        with console.status("[bold green]Submitting order...") as status:
            res = place_order(
                client=client,
                symbol=clean_params["symbol"],
                side=clean_params["side"],
                order_type=clean_params["type"],
                quantity=clean_params["quantity"],
                price=clean_params.get("price"),
                stop_price=clean_params.get("stopPrice")
            )
        show_order_success(res)
    except Exception as e:
        console.print(Panel(f"[bold red]Failed to execute order:[/bold red]\n{e}", title="API Error Details", border_style="red"))

def show_order_success(res: dict):
    """Formats and prints successful order placement details."""
    order_id = res.get("orderId")
    status = res.get("status")
    symbol = res.get("symbol")
    side = res.get("side")
    order_type = res.get("type")
    orig_qty = res.get("origQty")
    executed_qty = res.get("executedQty")
    
    # avgPrice might be '0.00000' in some limit orders until filled
    avg_price = res.get("avgPrice", "0.0")
    if float(avg_price) == 0.0 and res.get("price"):
        avg_price = f"{res.get('price')} (Limit Price)"
        
    panel_content = (
        f"[bold green]✓ Order Executed / Submitted Successfully![/bold green]\n\n"
        f"[bold]Order ID:[/bold] {order_id}\n"
        f"[bold]Status:[/bold] {status}\n"
        f"[bold]Symbol:[/bold] {symbol}\n"
        f"[bold]Side:[/bold] {side}\n"
        f"[bold]Type:[/bold] {order_type}\n"
        f"[bold]Quantity (Orig / Executed):[/bold] {orig_qty} / {executed_qty}\n"
        f"[bold]Execution Avg Price:[/bold] {avg_price} USDT\n"
    )
    
    console.print(Panel(panel_content, title="Testnet Order Confirmation", border_style="green"))

if __name__ == "__main__":
    cli()
