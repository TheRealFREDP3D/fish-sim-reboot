"""Entry point for the Underwater Neural Ecosystem Simulation"""

import sys
from src.fish_sim.main import run_simulation

if __name__ == "__main__":
    sys.path.insert(0, ".")   # Ensures src/ is findable
    run_simulation()
