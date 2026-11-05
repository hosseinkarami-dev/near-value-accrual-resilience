"""Update daily and current NEAR network metrics from DeFiLlama."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from src.pipelines.defillama_network import run_network_metrics


if __name__ == "__main__":
    print(run_network_metrics())
