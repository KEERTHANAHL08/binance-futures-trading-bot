import unittest
from unittest.mock import patch, MagicMock
import hmac
import hashlib
from urllib.parse import parse_qs, urlparse

from bot.validators import validate_order_params, ValidationError
from bot.client import BinanceFuturesClient, BinanceAPIError, BinanceNetworkError
from bot.orders import place_order, get_usdt_balance, get_ticker_price

class TestValidators(unittest.TestCase):
    def test_valid_market_order(self):
        params = validate_order_params("BTCUSDT", "BUY", "MARKET", "0.005")
        self.assertEqual(params["symbol"], "BTCUSDT")
        self.assertEqual(params["side"], "BUY")
        self.assertEqual(params["type"], "MARKET")
        self.assertEqual(params["quantity"], 0.005)

    def test_valid_limit_order(self):
        params = validate_order_params("ETHUSDT", "sell", "limit", 1.5, price="1850.5")
        self.assertEqual(params["symbol"], "ETHUSDT")
        self.assertEqual(params["side"], "SELL")
        self.assertEqual(params["type"], "LIMIT")
        self.assertEqual(params["quantity"], 1.5)
        self.assertEqual(params["price"], 1850.5)

    def test_valid_stop_limit_order(self):
        params = validate_order_params("SOLUSDT", "BUY", "STOP_LIMIT", "10", price="25.5", stop_price="24.0")
        self.assertEqual(params["symbol"], "SOLUSDT")
        self.assertEqual(params["side"], "BUY")
        self.assertEqual(params["type"], "STOP_LIMIT")
        self.assertEqual(params["quantity"], 10.0)
        self.assertEqual(params["price"], 25.5)
        self.assertEqual(params["stopPrice"], 24.0)

    def test_missing_limit_price(self):
        with self.assertRaises(ValidationError) as context:
            validate_order_params("BTCUSDT", "BUY", "LIMIT", "0.01")
        self.assertIn("Price is required for LIMIT orders", str(context.exception))

    def test_missing_stop_limit_params(self):
        with self.assertRaises(ValidationError) as context:
            validate_order_params("BTCUSDT", "BUY", "STOP_LIMIT", "0.01", price="30000")
        self.assertIn("Stop price is required for STOP_LIMIT orders", str(context.exception))

    def test_invalid_quantity(self):
        with self.assertRaises(ValidationError) as context:
            validate_order_params("BTCUSDT", "BUY", "MARKET", "-0.01")
        self.assertIn("Quantity must be greater than zero", str(context.exception))

    def test_invalid_price(self):
        with self.assertRaises(ValidationError) as context:
            validate_order_params("BTCUSDT", "BUY", "LIMIT", "0.01", price="-100")
        self.assertIn("Price must be greater than zero", str(context.exception))

class TestClientAndSigning(unittest.TestCase):
    def setUp(self):
        self.api_key = "test_api_key"
        self.api_secret = "test_api_secret"
        self.client = BinanceFuturesClient(api_key=self.api_key, api_secret=self.api_secret)

    @patch("time.time")
    def test_signature_generation(self, mock_time):
        mock_time.return_value = 1690000000.000 # returns timestamp 1690000000000
        
        # Test signing mechanism
        query_string = "symbol=BTCUSDT&side=BUY&timestamp=1690000000000"
        expected_sig = hmac.new(
            self.api_secret.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()
        
        sig = self.client._sign(query_string)
        self.assertEqual(sig, expected_sig)

    @patch("requests.post")
    def test_signed_request_headers_and_params(self, mock_post):
        # Configure mock response
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.json.return_value = {"orderId": 12345, "status": "NEW"}
        mock_resp.text = '{"orderId": 12345, "status": "NEW"}'
        mock_post.return_value = mock_resp

        # Send request
        params = {"symbol": "BTCUSDT", "side": "BUY", "quantity": "0.001"}
        res = self.client.request("POST", "/fapi/v1/order", params=params, signed=True)

        self.assertEqual(res["orderId"], 12345)
        
        # Verify mock post was called with correct parameters
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        
        # Verify Headers
        self.assertEqual(kwargs["headers"]["X-MBX-APIKEY"], self.api_key)
        
        # Verify params contain symbol, side, quantity, timestamp, signature
        sent_params = kwargs["params"]
        self.assertEqual(sent_params["symbol"], "BTCUSDT")
        self.assertEqual(sent_params["side"], "BUY")
        self.assertEqual(sent_params["quantity"], "0.001")
        self.assertIn("timestamp", sent_params)
        self.assertIn("signature", sent_params)

    @patch("requests.get")
    def test_api_error_handling(self, mock_get):
        # Configure mock response to return HTTP 400 with Binance error details
        mock_resp = MagicMock()
        mock_resp.ok = False
        mock_resp.status_code = 400
        mock_resp.json.return_value = {"code": -2010, "msg": "Account has insufficient balance."}
        mock_resp.text = '{"code": -2010, "msg": "Account has insufficient balance."}'
        mock_get.return_value = mock_resp

        with self.assertRaises(BinanceAPIError) as context:
            self.client.request("GET", "/fapi/v2/balance", signed=True)
            
        self.assertEqual(context.exception.status_code, 400)
        self.assertEqual(context.exception.code, -2010)
        self.assertIn("Account has insufficient balance", str(context.exception))

class TestOrderMethods(unittest.TestCase):
    def setUp(self):
        self.client = MagicMock(spec=BinanceFuturesClient)

    def test_place_market_order(self):
        self.client.request.return_value = {"orderId": 55555, "status": "FILLED", "avgPrice": "29500.0"}
        
        res = place_order(self.client, "BTCUSDT", "BUY", "MARKET", 0.01)
        
        self.assertEqual(res["orderId"], 55555)
        self.client.request.assert_called_once_with(
            "POST", 
            "/fapi/v1/order", 
            params={"symbol": "BTCUSDT", "side": "BUY", "quantity": "0.01", "type": "MARKET"}, 
            signed=True
        )

    def test_place_limit_order(self):
        self.client.request.return_value = {"orderId": 66666, "status": "NEW"}
        
        res = place_order(self.client, "BTCUSDT", "SELL", "LIMIT", 0.05, price=29800.0)
        
        self.assertEqual(res["orderId"], 66666)
        self.client.request.assert_called_once_with(
            "POST", 
            "/fapi/v1/order", 
            params={
                "symbol": "BTCUSDT", 
                "side": "SELL", 
                "quantity": "0.05", 
                "type": "LIMIT", 
                "price": "29800.0", 
                "timeInForce": "GTC"
            }, 
            signed=True
        )

    def test_get_usdt_balance(self):
        self.client.request.return_value = [
            {"asset": "BTC", "balance": "0.5", "availableBalance": "0.5"},
            {"asset": "USDT", "balance": "1050.25", "availableBalance": "900.50", "maxWithdrawAmount": "900.50"}
        ]
        
        bal = get_usdt_balance(self.client)
        self.assertEqual(bal["asset"], "USDT")
        self.assertEqual(bal["balance"], 1050.25)
        self.assertEqual(bal["available_balance"], 900.50)

if __name__ == "__main__":
    unittest.main()
