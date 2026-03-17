# Underwater Plant Ecosystem Simulation

> "Evolving neural fish in a living underwater ecosystem — built from scratch in pure Python + Pygame"

![Python](https://img.shields.io/badge/Python-3.8+-blue)
![Pygame](https://img.shields.io/badge/Pygame-2.5+-green)
![License](https://img.shields.io/badge/License-MIT-yellow)
![Activity](https://img.shields.io/github/commit-activity/m/TheRealFREDP3D/fish-sim-reboot)

A sophisticated underwater ecosystem simulation featuring neural network-driven fish, dynamic plant growth, real-time brain visualization, and a full day/night + seasonal cycle system.

![Screenshot](doc/screenshot.png)

## 🌊 Features

### 🌙 Day/Night & Season System *(new)*

- **Day/Night Cycle**: Full 24-hour cycle with smooth dawn, midday, dusk, and night phases
- **Dynamic Sky**: Sky colour shifts from deep blue-black at midnight → orange/pink at dawn → brilliant blue midday → amber dusk → starry night
- **Stars**: Twinkling star field visible at night that twinkles and parallaxes across the world
- **Volumetric Lighting**: Light rays appear during the day and fade to nothing at night
- **Night Overlay**: Dark ambient overlay deepens as the sun sets, giving a genuine sense of depth
- **Bioluminescence**: Fish and plant tips glow faintly at night — common fish in cool white, cleaners in teal, predators in red
- **Four Seasons**: Spring → Summer → Autumn → Winter cycling every 7 in-game days
  - **Spring**: Nutrient upwelling, peak mating drive, high plant growth
  - **Summer**: Peak predator activity, strongest sunlight, fastest fish metabolism
  - **Autumn**: Heavy seed dispersal, amber sky tint, falling leaf particles
  - **Winter**: Reduced metabolism (fish become sluggish), plants enter partial dormancy, snow crystal particles
- **Plankton Diel Migration**: Plankton migrate toward the surface during the day and sink to depth at night, just as they do in real oceans
- **Time Controls**: Press **T** to cycle through 1× / 3× / 6× speed; press **P** to pause

![Brain Visualizer](doc/Animation.gif)

### **Neural Fish System**
- **Multiple Fish Species**: Regular fish, cleaner fish (cyan-striped), and predators (red)
- **Neural Network Brains**: Each fish has its own feed-forward neural network that controls all movement and behaviour
- **Real-time Brain Visualization**: Click on any fish to see its neural activations, connection weights, and output gauges in real-time
- **Evolutionary Inheritance**: Fish pass traits and mutated neural weights to offspring through natural selection
- **Life Stages**: Larva → Juvenile → Adult → Elder, each with distinct behaviours and display labels
- **Seasonal Behaviour**: Mating drives surge in Spring, fish slow and conserve energy in Winter, predators peak in Summer



### **Dynamic Plant Ecosystem**
- **Three Plant Types**: Kelp (deep water), seagrass (mid-depth), and algae (shallow) with unique growth patterns
- **Root Systems**: Complex underground root networks that actively seek nutrient-rich soil cells
- **Soil Nutrient System**: Dynamic soil fertility shaped by fish waste decomposition and plant death
- **Photosynthesis**: Plants only convert nutrients efficiently during daylight; winter reduces photosynthesis further
- **Seed Distribution**: Plants reproduce by releasing seeds that drift and settle on suitable terrain; seed dispersal spikes in Autumn
- **Realistic Physics**: Plants sway with simulated water currents, responding to depth and energy level

### **Environmental Systems**
- **Particle Effects**: Sediment, plankton, bubbles, leaf particles (Autumn), and snow crystals (Winter)
- **Light Rays**: Dynamic volumetric lighting that fades at dusk and is absent at night
- **Camera System**: Smooth camera tracking that follows a selected fish across the scrollable world
- **Terrain Zones**: Procedurally generated beach slope, mid-water shelf, and deep-water floor

### **Ecological Interactions**
- **Cleaner Fish**: Actively seek and consume waste particles, returning nutrients to the soil
- **Predator-Prey Dynamics**: Predators dash at prey; prey detect threats via their neural radar and flee; predators hibernate slightly in Winter
- **Nutrient Cycling**: Waste decomposition enriches soil, feeding plants that shelter fish
- **Population Balance**: Per-species population caps and energy-based reproduction prevent runaway growth
- **Family Units**: After hatching, parents temporarily stay near offspring until they mature

## 🎮 Controls

| Input | Action |
|---|---|
| **Left Click** | Select a fish to view its brain panel |
| **Left Click** (empty space) | Deselect fish |
| **T** | Cycle time speed (1× → 3× → 6× → 1×) |
| **P** | Pause / resume the simulation |
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
├── main.py                  # Main simulation entry point, game loop, and HUD
├── config.py                # All configuration constants (including time/season)
├── requirements.txt         # Python dependencies (pygame)
│
├── time_system.py           # ★ NEW: Day/night cycle, seasons, light level, bioluminescence
│
├── world.py                 # World generation, terrain, sky, stars, season particles
├── camera.py                # Smooth camera system with world-space transforms
│
├── fish_system.py           # Fish population manager (spawning, mating, death)
├── fish_base.py             # Base NeuralFish class — radar, neural forward pass, steering
├── predator_fish.py         # Predator subclass with dash mechanics and seasonal activity
├── cleaner_fish.py          # Cleaner subclass with poop-seeking and hiding behaviour
├── fish_physics.py          # Steering physics (seek, bounce bounds, Euler integration)
├── fish_traits.py           # Heritable genetic traits with blend/mutate helpers
├── neural_net.py            # Feed-forward neural network (14 → 12 → 6 → 2)
│
├── plants.py                # Plant rendering and PlantManager (seeds, bubbles, updates)
├── plant_development.py     # Staged plant life cycle with photosynthesis rate support
├── roots.py                 # Root network — directed graph seeking nutrient cells
├── seeds.py                 # Seed dispersal physics and trait inheritance
├── soil.py                  # Soil grid with nutrient diffusion and organic rendering
│
├── particles.py             # Sediment and plankton with diel vertical migration
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

### **Evolution**
Fish do not train via gradient descent. Instead, when two fish mate, the offspring inherits a blend of both parents' weights with random Gaussian mutations applied at configurable rate and strength (`MUTATION_RATE`, `MUTATION_STRENGTH` in `config.py`).

## 🌞 Day/Night & Season System

### **TimeSystem**
The `TimeSystem` class in `time_system.py` is the master clock that drives all time-dependent behaviour:

- `light_level` — smooth 0→1→0 over the course of a day; governs sky colour, ray brightness, night overlay, and bioluminescence
- `photosynthesis_rate` — `light_level × season_modifier`; controls how efficiently plants convert nutrients
- `plankton_depth_bias` — +1 at noon (surface), –1 at midnight (deep); drives diel vertical migration
- `metabolism_modifier` — Summer 1.2×, Winter 0.6×; scales fish energy drain
- `mating_drive_modifier` — Spring 1.5×, Winter 0.4×; lowers the energy threshold for mating
- `seed_dispersal_modifier` — Autumn 2.0×; more seeds, shorter cooldown between seed releases
- `nutrient_upwelling` — Spring adds a slow background trickle of soil nutrients
- `predator_activity_modifier` — Summer 1.3×, Winter 0.6×; scales predator seek force

### **Tuning Time**
All thresholds in `config.py`:

| Constant | Default | Effect |
|---|---|---|
| `DAY_DURATION` | 120 s | Real seconds per in-game day |
| `SEASON_DURATION` | 840 s | Real seconds per season (7 days) |
| `DAWN_START / DAWN_END` | 0.18 / 0.27 | Dawn window as fraction of day |
| `DUSK_START / DUSK_END` | 0.73 / 0.82 | Dusk window as fraction of day |

## 🌱 Plant Growth System

### **Root Network**
- Roots grow as a directed graph from the plant base downward into soil cells
- Each growth step selects the nutrient-richest reachable neighbour with a weighted random choice
- Nutrients flow up the graph toward the root origin, then are delivered to the plant
- In winter, photosynthesis drops to 30% efficiency; plants enter partial dormancy

### **Plant Life Cycle**
1. **Germinating** — Root establishment, minimal visual presence
2. **Seedling** — Partial height, limited blades visible
3. **Mature** — Full size; fish can hide nearby to reduce predator detection range; bioluminescent tip at night
4. **Flowering** — Seed production phase, glowing tip visible
5. **Dying** — Energy depleted or max age reached, colour fades
6. **Decomposing** — Returns nutrients to surrounding soil cells

## 🔧 Configuration

All tuneable parameters live in `config.py`. Key areas:

| Section | Key Constants |
|---|---|
| World size | `WORLD_WIDTH`, `WORLD_HEIGHT`, `SCREEN_WIDTH`, `SCREEN_HEIGHT` |
| Time & Season | `DAY_DURATION`, `SEASON_DURATION`, `DAWN_START`, `DAWN_END`, `DUSK_START`, `DUSK_END` |
| Fish behaviour | `FISH_HUNGER_THRESHOLD`, `FISH_MATING_THRESHOLD`, `FISH_MAX_ENERGY` |
| Life stages | `FISH_LARVA_DURATION`, `FISH_JUVENILE_DURATION`, `FISH_ADULT_DURATION`, `FISH_ELDER_DURATION` |
| Populations | `FISH_MAX_POPULATION`, `CLEANER_FISH_MAX_POPULATION`, `PREDATOR_MAX_POPULATION` |
| Evolution | `MUTATION_RATE`, `MUTATION_STRENGTH` |
| Predator | `PREDATOR_DASH_DURATION`, `PREDATOR_DASH_COOLDOWN` |
| Visual FX | `STAR_COUNT`, `BIOLUM_COLORS`, `SEASONAL_PARTICLE_CHANCE` |

## 📊 Performance

- **Target FPS**: 60
- **World Size**: 4000 × 1200 pixels (camera scrolls)
- **Max Populations**: 40 common fish · 15 cleaner fish · 4 predators
- **Particle Count**: ~720 environmental particles (sediment + plankton)
- **Rendering**: Particle batching, camera-based culling, and soil diffusion slicing keep frame time low

## 🤝 Contributing

Contributions are welcome! Some ideas for extension:

- Statistics dashboard showing population curves and trait evolution over time
- NEAT (NeuroEvolution of Augmenting Topologies) — fish brains that grow new connections
- Save/load ecosystem state across sessions
- Ocean currents that push particles and seeds
- Coral reef structures providing permanent shelter

## 📄 License

This project is open source and available under the MIT License.

---

**Dive in and watch the ecosystem evolve through day and night!** 🐠🌿🌙
