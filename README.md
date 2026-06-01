# Binance Futures Testnet Trading Bot

A Python CLI application for placing **MARKET** and **LIMIT** orders on the [Binance Futures Testnet (USDT-M)](https://testnet.binancefuture.com). Built with a clear separation between the API client layer and the CLI layer, with structured logging.

---

## Setup

Requires **Python 3.10+**.

### 1. Clone / unzip the project

```bash
git clone <repo-url>
cd trading_bot
```

### 2. Create and activate a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Obtain Testnet API credentials

1. Go to [https://testnet.binancefuture.com](https://testnet.binancefuture.com) and log in (Google account accepted).
2. Navigate to **Account → API Management**.
3. Generate an API key/secret pair.

### 5. Configure credentials

```bash
cp .env.example .env
```

Edit `.env`:

```
BINANCE_TESTNET_API_KEY=your_api_key_here
BINANCE_TESTNET_API_SECRET=your_api_secret_here
```

> **Security note:** `.env` is listed in `.gitignore` and should never be committed.

---

## How to Run

All commands follow this pattern:

```
python cli.py [--log-level LEVEL] COMMAND [options]
```

### Check connectivity

```bash
python cli.py ping
```

```
✅  Pong!  Server time: 1748769000000 ms
```

### View account balances

```bash
python cli.py account
```

### Place a MARKET order

```bash
python cli.py place --symbol BTCUSDT --side BUY --type MARKET --qty 0.001
```

```
── Order Request ─────────────────────────────────────
  Symbol      : BTCUSDT
  Side        : BUY
  Order Type  : MARKET
  Quantity    : 0.001
────────────────────────────────────────────────────────
  ✅ Order placed successfully
  Order ID    : 4820371958
  Status      : FILLED
  Executed Qty: 0.001
  Avg Price   : 67542.1
────────────────────────────────────────────────────────
```

### Place a LIMIT order

```bash
python cli.py place --symbol ETHUSDT --side SELL --type LIMIT --qty 0.01 --price 3200
```

```
── Order Request ─────────────────────────────────────
  Symbol      : ETHUSDT
  Side        : SELL
  Order Type  : LIMIT
  Quantity    : 0.01
  Limit Price : 3200.0
────────────────────────────────────────────────────────
  ✅ Order placed successfully
  Order ID    : 2910847365
  Status      : NEW
  Executed Qty: 0.0
────────────────────────────────────────────────────────
```

### Verbose debug logging

```bash
python cli.py --log-level DEBUG place --symbol BTCUSDT --side BUY --type MARKET --qty 0.001
```

---

## Logging

Logs are written to `logs/trading_bot_YYYYMMDD.log` automatically.

- **File handler** — always captures `DEBUG` and above (full request/response detail).
- **Console handler** — shows `INFO` and above by default; use `--log-level DEBUG` for full output.

Sample log entries are provided in `logs/market_order_sample.log` and `logs/limit_order_sample.log`.

---

## Validation & Error Handling

| Scenario | Behaviour |
|---|---|
| Missing `--price` on LIMIT | Clear `ValueError` before any API call |
| `--price` supplied on MARKET | Rejected with explanation |
| Non-numeric quantity / price | Rejected with explanation |
| Quantity ≤ 0 | Rejected with explanation |
| Binance API error (e.g. insufficient margin) | Caught, logged, printed cleanly |
| Network timeout | Caught, logged, printed cleanly |
| Missing API credentials | Immediate exit with setup instructions |

---

## License

MIT
