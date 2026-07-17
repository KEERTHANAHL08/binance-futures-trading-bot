import hmac
import hashlib
import time
import requests
from urllib.parse import urlencode
from bot.logging_config import logger

class BinanceError(Exception):
    """Base exception for all Binance API client errors."""
    pass

class BinanceNetworkError(BinanceError):
    """Exception raised for network or connection issues."""
    pass

class BinanceAPIError(BinanceError):
    """Exception raised when the Binance API returns a structured error."""
    def __init__(self, status_code: int, code: int, message: str, response_body: str):
        self.status_code = status_code
        self.code = code
        self.message = message
        self.response_body = response_body
        super().__init__(f"Binance API Error {code}: {message} (HTTP {status_code})")

class BinanceFuturesClient:
    """Binance Futures REST API Client wrapper."""
    
    def __init__(
        self, 
        api_key: str | None = None, 
        api_secret: str | None = None, 
        base_url: str = "https://testnet.binancefuture.com"
    ):
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = base_url.rstrip('/')
        
    def _get_timestamp(self) -> int:
        """Returns the current timestamp in milliseconds."""
        return int(time.time() * 1000)

    def _sign(self, query_string: str) -> str:
        """Generates an HMAC-SHA256 signature for the given query string."""
        if not self.api_secret:
            raise BinanceError("API Secret Key is required to sign requests.")
        return hmac.new(
            self.api_secret.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()

    def request(self, method: str, endpoint: str, params: dict | None = None, signed: bool = False) -> dict:
        """
        Sends an HTTP request to the Binance Futures Testnet API.
        
        :param method: HTTP method (GET, POST, DELETE)
        :param endpoint: REST endpoint path (e.g. /fapi/v1/order)
        :param params: Key-value dictionary of parameters
        :param signed: True if the request requires HMAC-SHA256 signature
        :return: Parsed JSON response
        """
        url = f"{self.base_url}{endpoint}"
        req_params = params.copy() if params else {}
        
        headers = {}
        if self.api_key:
            headers["X-MBX-APIKEY"] = self.api_key

        if signed:
            if not self.api_key or not self.api_secret:
                raise BinanceError("Both API Key and API Secret are required for signed requests.")
            req_params["timestamp"] = self._get_timestamp()
            # Generate the URL-encoded query string for signing
            query_string = urlencode(req_params)
            signature = self._sign(query_string)
            req_params["signature"] = signature

        # Mask keys in logs
        log_params = req_params.copy()
        if "signature" in log_params:
            log_params["signature"] = log_params["signature"][:8] + "..."
            
        logger.debug(f"Request: {method} {url} - Params: {log_params}")
        
        try:
            if method.upper() == "GET":
                response = requests.get(url, params=req_params, headers=headers, timeout=15)
            elif method.upper() == "POST":
                # For Binance, sending as query parameters is safe and prevents content-type discrepancies
                response = requests.post(url, params=req_params, headers=headers, timeout=15)
            elif method.upper() == "DELETE":
                response = requests.delete(url, params=req_params, headers=headers, timeout=15)
            else:
                raise BinanceError(f"Unsupported HTTP method: {method}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error during {method} {url}: {e}")
            raise BinanceNetworkError(f"Network request failed: {e}")

        logger.debug(f"Response Status: {response.status_code}")
        
        # Check for empty response body (can happen with DELETE or 204 status codes)
        if not response.text.strip():
            if response.ok:
                return {}
            raise BinanceError(f"Empty error response from server (HTTP {response.status_code})")

        # Parse JSON response
        try:
            response_json = response.json()
        except ValueError:
            logger.error(f"Failed to parse JSON response: {response.text}")
            raise BinanceError(f"Invalid JSON response from server (HTTP {response.status_code}): {response.text}")

        # If server returns an error, raise BinanceAPIError
        if not response.ok:
            error_code = response_json.get("code", 0)
            error_msg = response_json.get("msg", "Unknown error")
            logger.error(f"API Error - HTTP {response.status_code}: code={error_code}, msg={error_msg}")
            raise BinanceAPIError(
                status_code=response.status_code,
                code=error_code,
                message=error_msg,
                response_body=response.text
            )

        logger.debug(f"Response JSON: {response_json}")
        return response_json
