import json
from crewai.tools import BaseTool

class KiteBacktestingEngineTool(BaseTool):
    name: str = "KiteBacktestingEngine"
    description: str = "Runs a simple backtest simulation on OHLCV data using entry/exit rules."

    def _run(self, candles_json: str, entry_score_threshold: int = 70) -> str:
        candles = json.loads(candles_json) if isinstance(candles_json, str) else candles_json
        closes = [c["close"] for c in candles]
        highs = [c["high"] for c in candles]
        lows = [c["low"] for c in candles]

        if len(closes) < 30:
            return json.dumps({"error": "Insufficient data for backtest"})

        split = int(len(closes) * 0.7)
        trades, wins = [], 0

        for i in range(20, split - 5):
            window = closes[i-20:i]
            avg = sum(window) / 20
            atr_vals = []
            for j in range(1, len(window)):
                tr = max(highs[i-20+j] - lows[i-20+j],
                         abs(highs[i-20+j] - closes[i-20+j-1]),
                         abs(lows[i-20+j] - closes[i-20+j-1]))
                atr_vals.append(tr)
            atr = sum(atr_vals) / len(atr_vals) if atr_vals else closes[i] * 0.02

            if closes[i] > avg:
                entry = closes[i]
                sl = entry - 1.5 * atr
                t1 = entry + 2 * atr
                t2 = entry + 3.236 * atr
                exit_price = closes[i+5] if i+5 < len(closes) else closes[-1]
                pnl = exit_price - entry
                rr = (t1 - entry) / (entry - sl) if entry > sl else 0
                if rr >= 2:
                    trades.append({"entry": entry, "exit": exit_price, "pnl": pnl, "rr": rr})
                    if pnl > 0:
                        wins += 1

        total = len(trades)
        win_rate = round((wins / total * 100), 2) if total > 0 else 0
        total_pnl = sum(t["pnl"] for t in trades)
        gross_profit = sum(t["pnl"] for t in trades if t["pnl"] > 0)
        gross_loss = abs(sum(t["pnl"] for t in trades if t["pnl"] < 0))
        profit_factor = round(gross_profit / gross_loss, 2) if gross_loss > 0 else 0
        max_dd = round(min([t["pnl"] for t in trades], default=0), 2)
        sharpe = round(total_pnl / (len(trades) ** 0.5), 4) if trades else 0

        return json.dumps({
            "total_trades": total,
            "win_rate_pct": win_rate,
            "profit_factor": profit_factor,
            "max_drawdown": max_dd,
            "sharpe_ratio": sharpe,
            "total_pnl": round(total_pnl, 2),
            "confidence": "High" if win_rate > 60 and profit_factor > 1.5 else ("Medium" if win_rate > 50 else "Low")
        })
