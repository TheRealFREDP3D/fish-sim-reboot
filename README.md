# Underwater Plant Ecosystem Simulation

A sophisticated underwater ecosystem simulation featuring neural network-driven fish, dynamic plant growth, and real-time brain visualization. This project creates a living underwater world where fish evolve, plants grow, and ecological interactions emerge naturally.

![Screenshot](doc/screenshot.png)

## 🌊 Features

[Brain Visualizer](brain_visualizer.py)

### **Neural Fish System**


- **Multiple Fish Species**: Regular fish, cleaner fish (cyan-striped), and predators (red)
- **Neural Network Brains**: Each fish has its own feed-forward neural network that controls all movement and behaviour
- **Real-time Brain Visualization**: Click on any fish to see its neural activations, connection weights, and output gauges in real-time
- **Evolutionary Inheritance**: Fish pass traits and mutated neural weights to offspring through natural selection
- **Life Stages**: Larva → Juvenile → Adult → Elder, each with distinct behaviours and display labels

### **Dynamic Plant Ecosystem**
- **Three Plant Types**: Kelp (deep water), seagrass (mid-depth), and algae (shallow) with unique growth patterns
- **Root Systems**: Complex underground root networks that actively seek nutrient-rich soil cells
- **Soil Nutrient System**: Dynamic soil fertility shaped by fish waste decomposition and plant death
- **Seed Distribution**: Plants reproduce by releasing seeds that drift and settle on suitable terrain
- **Realistic Physics**: Plants sway with simulated water currents, responding to depth and energy level

### **Environmental Systems**
- **Particle Effects**: Sediment, plankton, bubbles, and poop particles create a living underwater atmosphere
- **Light Rays**: Dynamic volumetric lighting effects simulating sunlight penetrating the water surface
- **Camera System**: Smooth camera tracking that follows a selected fish across the scrollable world
- **Terrain Zones**: Procedurally generated beach slope, mid-water shelf, and deep-water floor

### **Ecological Interactions**
- **Cleaner Fish**: Actively seek and consume waste particles, returning nutrients to the soil
- **Predator-Prey Dynamics**: Predators dash at prey; prey detect threats via their neural radar and flee
- **Nutrient Cycling**: Waste decomposition enriches soil, feeding plants that shelter fish
- **Population Balance**: Per-species population caps and energy-based reproduction prevent runaway growth
- **Family Units**: After hatching, parents temporarily stay near offspring until they mature

## 🎮 Controls

| Input | Action |
|---|---|
| **Left Click** | Select a fish to view its brain panel |
| **Left Click** (empty space) | Deselect fish |
| **R** | Regenerate the world |
| **ESC** | Quit |

## 🚀 Installation

### Prerequisites
- Python 3.8 or higher
- pip package manager

### Setup
1. Clone the repository:
```bash
git clone https://github.com/TheRealFREDP3D/fish-sim-reboot.git
cd fish-sim-reboot
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the simulation:
```bash
python main.py
```

## 📁 Project Structure
```
fish-sim-reboot/
├── main.py                  # Main simulation entry point and game loop
├── config.py                # All configuration constants and the FishState enum
├── requirements.txt         # Python dependencies (pygame)
│
├── world.py                 # World generation, terrain, and volumetric lighting
├── camera.py                # Smooth camera system with world-space transforms
│
├── fish_system.py           # Fish population manager (spawning, mating, death)
├── fish_base.py             # Base NeuralFish class — radar, neural forward pass, steering
├── predator_fish.py         # Predator subclass with dash mechanics and hunt logic
├── cleaner_fish.py          # Cleaner subclass with poop-seeking and hiding behaviour
├── fish_physics.py          # Steering physics (seek, bounce bounds, Euler integration)
├── fish_traits.py           # Heritable genetic traits with blend/mutate helpers
├── neural_net.py            # Feed-forward neural network (14 → 12 → 6 → 2)
│
├── plants.py                # Plant rendering and PlantManager (seeds, bubbles, updates)
├── plant_development.py     # Staged plant life cycle (germinating → decomposing)
├── roots.py                 # Root network — directed graph seeking nutrient cells
├── seeds.py                 # Seed dispersal physics and trait inheritance
├── soil.py                  # Soil grid with nutrient diffusion and organic rendering
│
├── particles.py             # Sediment and plankton particle system
├── family.py                # Temporary family units that dissolve on offspring maturity
├── environment_objects.py   # PoopParticle and FishEgg objects
│
└── brain_visualizer.py      # Sliding brain panel: network graph, gauges, sparklines
```

## 🧠 Neural Network Architecture

Each fish runs a feed-forward neural network every frame to determine its movement:
```
Inputs (14)  →  Hidden 1 (12)  →  Hidden 2 (6)  →  Outputs (2)
```

### **Input Layer (14 neurons)**

| # | Input | Description |
|---|---|---|
| 0–2 | Food radar | Left / Centre / Right sector intensity |
| 3–5 | Threat radar | Left / Centre / Right (hidden fish are invisible) |
| 6–8 | Mate radar | Left / Centre / Right (same species, opposite sex) |
| 9 | Energy | Normalised current energy |
| 10 | Stamina | Normalised current stamina |
| 11 | Depth | Normalised water depth position |
| 12 | Speed | Normalised current velocity magnitude |
| 13 | Safety | Proximity to nearest plant (hiding cover) |

### **Output Layer (2 neurons)**
| # | Output | Range | Effect |
|---|---|---|---|
| 0 | Steer | –1 → +1 | Rotational heading offset |
| 1 | Thrust | –1 → +1 | Forward force magnitude |

All activations use **tanh**, keeping values in [–1, 1]. The brain panel visualises live activations using a cyan (positive) → grey (neutral) → magenta (negative) colour scale.

### **Evolution**
Fish do not train via gradient descent. Instead, when two fish mate, the offspring inherits a blend of both parents' weights with random Gaussian mutations applied at configurable rate and strength (`MUTATION_RATE`, `MUTATION_STRENGTH` in `config.py`).

## 🌱 Plant Growth System

### **Root Network**
- Roots grow as a directed graph from the plant base downward into soil cells
- Each growth step selects the nutrient-richest reachable neighbour with a weighted random choice
- Nutrients flow up the graph toward the root origin, then are delivered to the plant

### **Plant Life Cycle**
1. **Germinating** — Root establishment, minimal visual presence
2. **Seedling** — Partial height, limited blades visible
3. **Mature** — Full size; fish can hide nearby to reduce predator detection range
4. **Flowering** — Seed production phase, glowing tip visible
5. **Dying** — Energy depleted or max age reached, colour fades
6. **Decomposing** — Returns nutrients to surrounding soil cells

## 🔧 Configuration

All tuneable parameters live in `config.py`. Key areas:

| Section | Key Constants |
|---|---|
| World size | `WORLD_WIDTH`, `WORLD_HEIGHT`, `SCREEN_WIDTH`, `SCREEN_HEIGHT` |
| Fish behaviour | `FISH_HUNGER_THRESHOLD`, `FISH_MATING_THRESHOLD`, `FISH_MAX_ENERGY` |
| Life stages | `FISH_LARVA_DURATION`, `FISH_JUVENILE_DURATION`, `FISH_ADULT_DURATION`, `FISH_ELDER_DURATION` |
| Populations | `FISH_MAX_POPULATION`, `CLEANER_FISH_MAX_POPULATION`, `PREDATOR_MAX_POPULATION` |
| Evolution | `MUTATION_RATE`, `MUTATION_STRENGTH` |
| Predator | `PREDATOR_DASH_DURATION`, `PREDATOR_DASH_COOLDOWN` |
| Cleaner | `CLEANER_FISH_CLEANING_ENERGY_THRESHOLD` |
| Plants | `PLANT_MAX_AGE`, `SEED_PRODUCTION_ENERGY`, `FLOWERING_DURATION` |

## 📊 Performance

- **Target FPS**: 60
- **World Size**: 4000 × 1200 pixels (camera scrolls)
- **Max Populations**: 40 common fish · 15 cleaner fish · 4 predators
- **Particle Count**: ~720 environmental particles (sediment + plankton)
- **Rendering**: Particle batching, camera-based culling, and soil diffusion slicing keep frame time low

## 🤝 Contributing

Contributions are welcome! Some ideas for extension:

- Additional fish species with unique neural input/output layouts
- More plant varieties and depth niches (coral, tube worms)
- Seasonal cycles affecting nutrient availability and light intensity
- Save/load of evolved fish brains
- Performance profiling and potential numpy acceleration for the neural forward pass

## 📄 License

This project is open source and available under the MIT License.

---

**Dive in and watch the ecosystem evolve!** 🐠🌿