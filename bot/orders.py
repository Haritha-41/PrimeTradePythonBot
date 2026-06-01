"""
Order placement logic layer.

Sits between the CLI and the raw BinanceFuturesClient.  Handles:
- Parameter validation (delegates to validators.py)
- Calling the client
- Formatting and returning a structured OrderResult
- Logging every order attempt and outcome
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from .client import BinanceFuturesClient, BinanceAPIError
from .validators import validate_all
from .logging_config import get_logger

logger = get_logger("orders")


@dataclass
class OrderResult:
    """Structured result returned to the CLI layer after an order attempt."""

    success: bool
    symbol: str
    side: str
    order_type: str
    quantity: float
    price: Optional[float]

    # Populated on success
    order_id: Optional[int] = None
    client_order_id: Optional[str] = None
    status: Optional[str] = None
    executed_qty: Optional[float] = None
    avg_price: Optional[float] = None
    raw_response: Dict[str, Any] = field(default_factory=dict)

    # Populated on failure
    error_message: Optional[str] = None

    def summary_lines(self) -> list[str]:
        """Return a list of human-readable summary lines."""
        lines = [
            "─" * 52,
            f"  Symbol      : {self.symbol}",
            f"  Side        : {self.side}",
            f"  Order Type  : {self.order_type}",
            f"  Quantity    : {self.quantity}",
        ]
        if self.price is not None:
            lines.append(f"  Limit Price : {self.price}")

        if self.success:
            lines += [
                "─" * 52,
                f"  ✅ Order placed successfully",
                f"  Order ID    : {self.order_id}",
                f"  Status      : {self.status}",
                f"  Executed Qty: {self.executed_qty}",
            ]
            if self.avg_price:
                lines.append(f"  Avg Price   : {self.avg_price}")
        else:
            lines += [
                "─" * 52,
                f"  ❌ Order FAILED",
                f"  Reason      : {self.error_message}",
            ]
        lines.append("─" * 52)
        return lines


def place_order(
    client: BinanceFuturesClient,
    symbol: str,
    side: str,
    order_type: str,
    quantity: str | float,
    price: Optional[str | float] = None,
) -> OrderResult:
    """
    Validate inputs, place an order, and return an OrderResult.

    Never raises — all exceptions are caught and stored in OrderResult.error_message.
    """
    # --- Validate ---
    try:
        params = validate_all(symbol, side, order_type, quantity, price)
    except ValueError as exc:
        logger.warning("Input validation failed: %s", exc)
        return OrderResult(
            success=False,
            symbol=str(symbol).upper(),
            side=str(side).upper(),
            order_type=str(order_type).upper(),
            quantity=0.0,
            price=None,
            error_message=str(exc),
        )

    logger.info(
        "Order request | symbol=%s side=%s type=%s qty=%s price=%s",
        params["symbol"],
        params["side"],
        params["order_type"],
        params["quantity"],
        params["price"],
    )

    # --- Place ---
    try:
        response = client.place_order(
            symbol=params["symbol"],
            side=params["side"],
            order_type=params["order_type"],
            quantity=params["quantity"],
            price=params["price"],
        )
    except BinanceAPIError as exc:
        logger.error("Binance API error while placing order: %s", exc)
        return OrderResult(
            success=False,
            **{k: params[k] for k in ("symbol", "side", "order_type", "quantity", "price")},
            error_message=str(exc),
        )
    except Exception as exc:  # network errors, timeouts, etc.
        logger.error("Unexpected error while placing order: %s", exc)
        return OrderResult(
            success=False,
            **{k: params[k] for k in ("symbol", "side", "order_type", "quantity", "price")},
            error_message=f"{type(exc).__name__}: {exc}",
        )

    # --- Parse response ---
    try:
        avg_price_raw = response.get("avgPrice") or response.get("price")
        avg_price = float(avg_price_raw) if avg_price_raw else None
        result = OrderResult(
            success=True,
            symbol=response.get("symbol", params["symbol"]),
            side=response.get("side", params["side"]),
            order_type=response.get("type", params["order_type"]),
            quantity=params["quantity"],
            price=params["price"],
            order_id=response.get("orderId"),
            client_order_id=response.get("clientOrderId"),
            status=response.get("status"),
            executed_qty=float(response.get("executedQty", 0)),
            avg_price=avg_price if avg_price and avg_price > 0 else None,
            raw_response=response,
        )
        logger.info(
            "Order placed | orderId=%s status=%s executedQty=%s",
            result.order_id,
            result.status,
            result.executed_qty,
        )
        return result
    except Exception as exc:
        logger.error("Failed to parse order response: %s | raw=%s", exc, response)
        return OrderResult(
            success=False,
            **{k: params[k] for k in ("symbol", "side", "order_type", "quantity", "price")},
            error_message=f"Response parse error: {exc}",
        )
