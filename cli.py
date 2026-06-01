#!/usr/bin/env python3
"""
cli.py — Command-line entry point for the Binance Futures Testnet Trading Bot.

Usage examples:
    python cli.py place --symbol BTCUSDT --side BUY  --type MARKET --qty 0.001
    python cli.py place --symbol ETHUSDT --side SELL --type LIMIT  --qty 0.01 --price 3200
    python cli.py account
    python cli.py ping
"""

from __future__ import annotations

import argparse
import os
import sys

from dotenv import load_dotenv

from bot.logging_config import setup_logging, get_logger
from bot.client import BinanceFuturesClient, BinanceAPIError
from bot.orders import place_order

# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------

load_dotenv()  # reads .env file if present

logger = get_logger("cli")


def _build_client() -> BinanceFuturesClient:
    """Construct a BinanceFuturesClient from environment variables."""
    api_key = os.getenv("BINANCE_TESTNET_API_KEY", "").strip()
    api_secret = os.getenv("BINANCE_TESTNET_API_SECRET", "").strip()

    if not api_key or not api_secret:
        print(
            "❌  Missing credentials.\n"
            "    Set BINANCE_TESTNET_API_KEY and BINANCE_TESTNET_API_SECRET\n"
            "    in your environment or in a .env file.",
            file=sys.stderr,
        )
        sys.exit(1)

    return BinanceFuturesClient(api_key=api_key, api_secret=api_secret)


# ---------------------------------------------------------------------------
# Sub-command handlers
# ---------------------------------------------------------------------------

def cmd_ping(args: argparse.Namespace, client: BinanceFuturesClient) -> int:
    """Check connectivity and print server time."""
    try:
        server_time = client.get_server_time()
        print(f"✅  Pong!  Server time: {server_time} ms")
        return 0
    except Exception as exc:
        print(f"❌  Ping failed: {exc}", file=sys.stderr)
        logger.error("Ping failed: %s", exc)
        return 1


def cmd_account(args: argparse.Namespace, client: BinanceFuturesClient) -> int:
    """Fetch and display key account information."""
    try:
        data = client.get_account()
        print("\n── Account Info ──────────────────────────────────────")
        print(f"  Can Trade  : {data.get('canTrade')}")
        print(f"  Total Wallet Balance (USDT): {data.get('totalWalletBalance')}")
        print(f"  Available Balance (USDT)  : {data.get('availableBalance')}")
        assets = [a for a in data.get("assets", []) if float(a.get("walletBalance", 0)) > 0]
        if assets:
            print("\n  Non-zero balances:")
            for a in assets:
                print(f"    {a['asset']:10s}  wallet={a['walletBalance']}  available={a['availableBalance']}")
        print("─" * 52)
        return 0
    except BinanceAPIError as exc:
        print(f"❌  API error: {exc}", file=sys.stderr)
        logger.error("Account fetch failed: %s", exc)
        return 1
    except Exception as exc:
        print(f"❌  Error: {exc}", file=sys.stderr)
        logger.error("Account fetch failed: %s", exc)
        return 1


def cmd_place(args: argparse.Namespace, client: BinanceFuturesClient) -> int:
    """Place a Market or Limit order and print the result."""
    print("\n── Order Request ─────────────────────────────────────")
    print(f"  Symbol      : {args.symbol.upper()}")
    print(f"  Side        : {args.side.upper()}")
    print(f"  Order Type  : {args.type.upper()}")
    print(f"  Quantity    : {args.qty}")
    if args.price:
        print(f"  Limit Price : {args.price}")
    print("─" * 52)

    result = place_order(
        client=client,
        symbol=args.symbol,
        side=args.side,
        order_type=args.type,
        quantity=args.qty,
        price=args.price,
    )

    for line in result.summary_lines():
        print(line)

    return 0 if result.success else 1


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="trading_bot",
        description="Binance Futures Testnet Trading Bot",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python cli.py ping
  python cli.py account
  python cli.py place --symbol BTCUSDT --side BUY  --type MARKET --qty 0.001
  python cli.py place --symbol ETHUSDT --side SELL --type LIMIT  --qty 0.01 --price 3200
        """,
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Console log verbosity (default: INFO). File always logs at DEBUG.",
    )

    sub = parser.add_subparsers(dest="command", metavar="COMMAND")
    sub.required = True

    # --- ping ---
    sub.add_parser("ping", help="Check API connectivity and print server time.")

    # --- account ---
    sub.add_parser("account", help="Display account balances.")

    # --- place ---
    place_p = sub.add_parser("place", help="Place a MARKET or LIMIT order.")
    place_p.add_argument("--symbol", required=True, help="Trading pair, e.g. BTCUSDT")
    place_p.add_argument(
        "--side", required=True, choices=["BUY", "SELL", "buy", "sell"],
        help="Order direction."
    )
    place_p.add_argument(
        "--type", required=True, choices=["MARKET", "LIMIT", "market", "limit"],
        help="Order type."
    )
    place_p.add_argument("--qty", required=True, type=float, help="Order quantity.")
    place_p.add_argument(
        "--price", type=float, default=None,
        help="Limit price (required for LIMIT orders, ignored for MARKET)."
    )

    return parser


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    setup_logging(log_level=args.log_level)
    logger.debug("CLI invoked with args: %s", vars(args))

    client = _build_client()

    dispatch = {
        "ping": cmd_ping,
        "account": cmd_account,
        "place": cmd_place,
    }

    handler = dispatch.get(args.command)
    if handler is None:
        parser.print_help()
        sys.exit(1)

    exit_code = handler(args, client)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
