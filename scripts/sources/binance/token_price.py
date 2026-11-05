"""Update the Binance Spot NEAR/USDT daily price dataset."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from src.pipelines.binance import run

if __name__ == "__main__":
    print(run())
