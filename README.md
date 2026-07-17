# Simplified Binance Futures Testnet Trading Bot (USDT-M)

A robust, structured Python CLI application to query market information, check balances, and execute orders (MARKET, LIMIT, and STOP_LIMIT) on the **Binance Futures Testnet (USDT-M)**.

---

## Features
- **Direct REST Implementation**: Uses `requests` with standard HMAC-SHA256 signature generation, avoiding heavy third-party library dependencies.
- **Multiple Order Types**:
  - `MARKET` (BUY & SELL)
  - `LIMIT` (BUY & SELL) with Time In Force (`GTC`)
  - `STOP_LIMIT` (BUY & SELL) (In Binance Futures REST API, this executes using `STOP` type with `price` and `stopPrice`).
- **Comprehensive Logging**: Detailed logging of server connection requests, signed payloads, responses, and errors, written to `trading_bot.log`.
- **Command Line Interface (CLI)**: Built with `click` and styled with `rich`, offering commands for direct order execution, balance checks, and ticker price queries.
- **Interactive Assistant UX**: Menu-driven interface that displays wallet balance and current symbol price to guide you safely through placing orders.
- **Robust Validators**: Full parameter checks on quantity, prices, sides, and symbols before hitting the REST API.
- **Test Suite**: Multi-scenario mocked unit tests.

---

## Directory Structure
```
trading_bot/
│
├── bot/
│   ├── __init__.py
│   ├── client.py          # REST client with HMAC-SHA256 signing
│   ├── logging_config.py  # Logger setup for stdout and trading_bot.log
│   ├── orders.py          # High-level trading operations
│   └── validators.py      # Input validations & cleaning
│
├── tests/
│   ├── __init__.py
│   └── test_bot.py        # Mocked unit tests
│
├── .env.example           # API credentials template
├── README.md              # Documentation
├── cli.py                 # Bot CLI entry point
├── requirements.txt       # Dependencies
└── generate_mock_logs.py  # Script to simulate trades & generate test log lines
```

---

## Installation & Setup

### 1. Clone & Set Active Workspace
Ensure the code is placed inside the directory:
`/Users/keerthanahl/.gemini/antigravity-ide/scratch/trading_bot`

We recommend setting this directory as your active IDE workspace.

### 2. Install Dependencies
Make sure you have Python 3.8+ installed. Navigate to the project directory and install the requirements:
```bash
pip install -r requirements.txt
```

### 3. Configure Credentials
Register for a testnet account at [Binance Futures Testnet](https://testnet.binancefuture.com). Generate an API Key and Secret.

Copy the `.env.example` file to `.env`:
```bash
cp .env.example .env
```
Open `.env` and fill in your keys:
```env
BINANCE_API_KEY=your_binance_testnet_api_key_here
BINANCE_API_SECRET=your_binance_testnet_api_secret_here
```

---

## Usage Guide

The application supports multiple CLI subcommands.

### 1. Check Ticker Price
Get the current spot/futures price of any active contract (no credentials required):
```bash
python cli.py price BTCUSDT
```

### 2. Check Wallet Balance
Retrieve USDT-M Futures account balances (requires API credentials):
```bash
python cli.py balance
```

### 3. Place Order via CLI Flags
Place orders directly using CLI options:

*   **MARKET Order:**
    ```bash
    python cli.py place --symbol BTCUSDT --side BUY --type MARKET --quantity 0.005
    ```
*   **LIMIT Order:**
    ```bash
    python cli.py place --symbol BTCUSDT --side BUY --type LIMIT --quantity 0.002 --price 60000.0
    ```
*   **STOP_LIMIT Order (Bonus feature):**
    ```bash
    python cli.py place --symbol BTCUSDT --side SELL --type STOP_LIMIT --quantity 0.002 --price 59000.0 --stop-price 59500.0
    ```

### 4. Interactive Menu Mode (Enhanced UX)
Run the menu-driven prompt system that guides you through checking ticker prices and placing orders safely with visual verification:
```bash
python cli.py interactive
```

---

## Logging

All transaction steps, signature details, and server responses are logged to `trading_bot.log`. 
- **Console Log Level**: `INFO` (clean user notifications)
- **File Log Level**: `DEBUG` (comprehensive REST parameters and raw API responses, including request timestamps and partially masked signature hashes)

You can check out `trading_bot.log` inside the project folder after executing orders. If you don't have credentials yet and want to see how the logs look, you can run the mock logging generator script:
```bash
python generate_mock_logs.py
```

---

## Running Unit Tests

Run the mocked unit test suite to verify internal validation and signing mechanisms:
```bash
python -m unittest tests/test_bot.py
```

---

## Web Dashboard & Render Deployment

We have included a web-based dashboard utilizing FastAPI and vanilla CSS.

### Running Locally
To launch the FastAPI dashboard on your local machine:
```bash
python app.py
```
Open your browser and navigate to `http://127.0.0.1:8000` to interact with the visual interface.

### Deploying to Render
This project includes a `render.yaml` blueprint for automated configuration on Render.

1. Ensure all changes are pushed to your GitHub repository.
2. Log in to your [Render Dashboard](https://dashboard.render.com).
3. Click **New +** at the top right, and select **Blueprint**.
4. Connect your GitHub repository.
5. Render will automatically read `render.yaml` and parse the configuration settings:
   - **Service Type**: Web Service
   - **Runtime**: Python
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app:app --host 0.0.0.0 --port $PORT`
6. Under **Environment Variables**, enter your Binance Futures Testnet credentials:
   - `BINANCE_API_KEY`
   - `BINANCE_API_SECRET`
7. Click **Deploy**. Render will build the environment and host your dashboard on a secure public URL.
