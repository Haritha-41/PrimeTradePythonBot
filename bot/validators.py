"""
Input validation for Binance Futures order parameters.
All validators raise ValueError with a clear message on failure.
"""

from __future__ import annotations

from typing import Optional


VALID_SIDES = {"BUY", "SELL"}
VALID_ORDER_TYPES = {"MARKET", "LIMIT"}


def validate_symbol(symbol: str) -> str:
    """Normalise and validate the trading symbol."""
    symbol = symbol.strip().upper()
    if not symbol:
        raise ValueError("Symbol must not be empty.")
    if len(symbol) < 3:
        raise ValueError(f"Symbol '{symbol}' looks too short; expected e.g. BTCUSDT.")
    return symbol


def validate_side(side: str) -> str:
    """Ensure side is BUY or SELL (case-insensitive)."""
    side = side.strip().upper()
    if side not in VALID_SIDES:
        raise ValueError(
            f"Invalid side '{side}'. Must be one of: {', '.join(sorted(VALID_SIDES))}."
        )
    return side


def validate_order_type(order_type: str) -> str:
    """Ensure order type is MARKET or LIMIT (case-insensitive)."""
    order_type = order_type.strip().upper()
    if order_type not in VALID_ORDER_TYPES:
        raise ValueError(
            f"Invalid order type '{order_type}'. Must be one of: "
            f"{', '.join(sorted(VALID_ORDER_TYPES))}."
        )
    return order_type


def validate_quantity(quantity: str | float) -> float:
    """Parse and validate the order quantity."""
    try:
        qty = float(quantity)
    except (ValueError, TypeError):
        raise ValueError(f"Quantity '{quantity}' is not a valid number.")
    if qty <= 0:
        raise ValueError(f"Quantity must be greater than zero; got {qty}.")
    return qty


def validate_price(price: Optional[str | float], order_type: str) -> Optional[float]:
    """
    Parse and validate the price.

    - MARKET orders must NOT supply a price.
    - LIMIT orders MUST supply a price > 0.
    """
    if order_type == "MARKET":
        if price is not None and str(price).strip() not in ("", "None"):
            raise ValueError("Price must not be set for MARKET orders.")
        return None

    # LIMIT
    if price is None or str(price).strip() in ("", "None"):
        raise ValueError("Price is required for LIMIT orders.")
    try:
        p = float(price)
    except (ValueError, TypeError):
        raise ValueError(f"Price '{price}' is not a valid number.")
    if p <= 0:
        raise ValueError(f"Price must be greater than zero; got {p}.")
    return p


def validate_all(
    symbol: str,
    side: str,
    order_type: str,
    quantity: str | float,
    price: Optional[str | float] = None,
) -> dict:
    """
    Run all validators and return a cleaned parameter dict.

    Returns:
        {
            "symbol": str,
            "side": str,
            "order_type": str,
            "quantity": float,
            "price": float | None,
        }
    """
    cleaned_order_type = validate_order_type(order_type)
    return {
        "symbol": validate_symbol(symbol),
        "side": validate_side(side),
        "order_type": cleaned_order_type,
        "quantity": validate_quantity(quantity),
        "price": validate_price(price, cleaned_order_type),
    }
