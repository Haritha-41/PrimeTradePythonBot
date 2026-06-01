"""
Binance Futures Testnet REST client.

Wraps all direct HTTP communication with the Binance Futures Testnet API,
including HMAC-SHA256 request signing, error normalisation, and structured
logging of every outbound request and inbound response.
"""

from __future__ import annotations

import hashlib
import hmac
import time
from typing import Any, Dict, Optional
from urllib.parse import urlencode

import requests

from .logging_config import get_logger

logger = get_logger("client")

TESTNET_BASE_URL = "https://testnet.binancefuture.com"
DEFAULT_TIMEOUT = 10  # seconds


class BinanceAPIError(Exception):
    """Raised when the Binance API returns an error payload."""

    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message
        super().__init__(f"Binance API error {code}: {message}")


class BinanceFuturesClient:
    """
    Thin, authenticated client for Binance USDT-M Futures Testnet.

    Args:
        api_key:    Testnet API key.
        api_secret: Testnet API secret.
        base_url:   Override base URL (defaults to testnet).
        timeout:    HTTP request timeout in seconds.
    """

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        base_url: str = TESTNET_BASE_URL,
        timeout: int = DEFAULT_TIMEOUT,
    ):
        if not api_key or not api_secret:
            raise ValueError("api_key and api_secret must both be non-empty strings.")
        self.api_key = api_key
        self._api_secret = api_secret
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._session = requests.Session()
        self._session.headers.update(
            {
                "X-MBX-APIKEY": self.api_key,
                "Content-Type": "application/x-www-form-urlencoded",
            }
        )
        logger.info("BinanceFuturesClient initialised (base_url=%s)", self.base_url)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _sign(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Append a timestamp and HMAC-SHA256 signature to *params* in-place."""
        params["timestamp"] = int(time.time() * 1000)
        query_string = urlencode(params)
        signature = hmac.new(
            self._api_secret.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        params["signature"] = signature
        return params

    def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        signed: bool = False,
    ) -> Dict[str, Any]:
        """
        Execute an HTTP request, log it, and return the parsed JSON response.

        Raises:
            BinanceAPIError: on a non-2xx Binance error payload.
            requests.RequestException: on network / timeout failures.
        """
        params = params or {}
        if signed:
            params = self._sign(params)

        url = f"{self.base_url}{endpoint}"
        safe_params = {k: v for k, v in params.items() if k != "signature"}
        logger.debug("REQUEST  %s %s  params=%s", method.upper(), endpoint, safe_params)

        try:
            if method.upper() in ("GET", "DELETE"):
                response = self._session.request(
                    method, url, params=params, timeout=self.timeout
                )
            else:
                response = self._session.request(
                    method, url, data=params, timeout=self.timeout
                )
        except requests.exceptions.Timeout:
            logger.error("Request timed out: %s %s", method.upper(), url)
            raise
        except requests.exceptions.ConnectionError as exc:
            logger.error("Connection error: %s", exc)
            raise

        logger.debug(
            "RESPONSE %s %s  status=%s  body=%s",
            method.upper(),
            endpoint,
            response.status_code,
            response.text[:500],
        )

        try:
            data: Dict[str, Any] = response.json()
        except ValueError:
            response.raise_for_status()
            raise RuntimeError(f"Non-JSON response: {response.text[:200]}")

        # Binance error payloads carry a negative 'code' field
        if isinstance(data, dict) and "code" in data and int(data["code"]) < 0:
            raise BinanceAPIError(code=int(data["code"]), message=data.get("msg", ""))

        response.raise_for_status()
        return data

    # ------------------------------------------------------------------
    # Public API methods
    # ------------------------------------------------------------------

    def get_server_time(self) -> int:
        """Return the Binance server timestamp in milliseconds."""
        data = self._request("GET", "/fapi/v1/time")
        return data["serverTime"]

    def get_exchange_info(self, symbol: Optional[str] = None) -> Dict[str, Any]:
        """Fetch exchange metadata (optionally filtered to one symbol)."""
        params = {}
        if symbol:
            params["symbol"] = symbol.upper()
        return self._request("GET", "/fapi/v1/exchangeInfo", params=params)

    def get_account(self) -> Dict[str, Any]:
        """Fetch account information (balances, positions)."""
        return self._request("GET", "/fapi/v2/account", signed=True)

    def place_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        quantity: float,
        price: Optional[float] = None,
        time_in_force: str = "GTC",
        reduce_only: bool = False,
    ) -> Dict[str, Any]:
        """
        Place a new futures order.

        Args:
            symbol:        e.g. 'BTCUSDT'
            side:          'BUY' or 'SELL'
            order_type:    'MARKET' or 'LIMIT'
            quantity:      Contract quantity (base asset).
            price:         Limit price (required for LIMIT orders).
            time_in_force: 'GTC', 'IOC', or 'FOK' (LIMIT only).
            reduce_only:   If True, order may only reduce an existing position.

        Returns:
            Raw Binance order response dict.
        """
        params: Dict[str, Any] = {
            "symbol": symbol.upper(),
            "side": side.upper(),
            "type": order_type.upper(),
            "quantity": quantity,
        }
        if reduce_only:
            params["reduceOnly"] = "true"
        if order_type.upper() == "LIMIT":
            if price is None:
                raise ValueError("price is required for LIMIT orders.")
            params["price"] = price
            params["timeInForce"] = time_in_force

        logger.info(
            "Placing %s %s order | symbol=%s qty=%s price=%s",
            side.upper(),
            order_type.upper(),
            symbol.upper(),
            quantity,
            price if price else "MARKET",
        )
        return self._request("POST", "/fapi/v1/order", params=params, signed=True)

    def get_order(self, symbol: str, order_id: int) -> Dict[str, Any]:
        """Query a specific order by symbol and orderId."""
        params = {"symbol": symbol.upper(), "orderId": order_id}
        return self._request("GET", "/fapi/v1/order", params=params, signed=True)

    def cancel_order(self, symbol: str, order_id: int) -> Dict[str, Any]:
        """Cancel an open order."""
        params = {"symbol": symbol.upper(), "orderId": order_id}
        logger.info("Cancelling orderId=%s on %s", order_id, symbol.upper())
        return self._request("DELETE", "/fapi/v1/order", params=params, signed=True)
