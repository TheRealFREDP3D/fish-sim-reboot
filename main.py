"""Entry point for the Underwater Neural Ecosystem Simulation"""

import sys
sys.path.insert(0, ".")   # Ensures src/ is findable
from src.fish_sim.main import run_simulation

if __name__ == "__main__":
    run_simulation()
