"""Update the DeFiLlama NEAR Intents holders revenue dataset."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from src.pipelines.defillama import run_series

if __name__ == "__main__":
    print(run_series("near_intents_holders_revenue_buyback"))
