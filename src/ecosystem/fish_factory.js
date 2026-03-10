
const SPECIES_VARIANTS = {
  NEON_TETRA: {
    name: "Neon Tetra",
    colors: ["#00f2ff", "#ff0000", "#ffffff"],
    sizeRange: [0.5, 0.8],
    speed: 1.5,
    schooling: true
  },
  GOLDEN_CARP: {
    name: "Golden Carp",
    colors: ["#ffd700", "#ff8c00"],
    sizeRange: [1.2, 2.0],
    speed: 0.8,
    schooling: false
  },
  EMERALD_GUPPY: {
    name: "Emerald Guppy",
    colors: ["#50c878", "#0040ff"],
    sizeRange: [0.7, 1.1],
    speed: 1.2,
    schooling: true
  }
};

function createFish(speciesType) {
  const config = SPECIES_VARIANTS[speciesType] || SPECIES_VARIANTS.NEON_TETRA;
  
  return {
    species: config.name,
    bodyColor: config.colors[0],
    accentColor: config.colors[1],
    scale: Math.random() * (config.sizeRange[1] - config.sizeRange[0]) + config.sizeRange[0],
    velocity: config.speed,
    isSchooling: config.schooling,

  };
}

