import pygame
import math
import random
from neural_net import NeuralNet
from fish_traits import FishTraits
from fish_physics import SteeringPhysics
from config import *
from family import Family


class PoopParticle:
    def __init__(self, x, y):
        self.x, self.y = x, y
        self.vy = random.uniform(0.5, 1.2)
        c_var = random.randint(-10, 10)
        self.color = (90 + c_var, 60 + c_var, 30)
        self.size = random.uniform(2, 4)
        self.rot = random.uniform(0, 360)

    def update(self, dt, world):
        self.y += self.vy * 40 * dt
        self.rot += dt * 50
        ty = world.get_terrain_height(self.x)
        if self.y >= ty:
            cell = world.soil_grid.get_cell_at_pixel(self.x, self.y)
            if cell:
                cell.nutrient = min(SOIL_MAX_NUTRIENT, cell.nutrient + 0.35)
            return False
        return True

    def draw(self, screen, camera):
        pos = camera.apply((self.x, self.y))
        pts = []
        for i in range(5):
            angle = math.radians(self.rot + i * 72)
            dist = self.size * (0.8 + 0.4 * math.sin(i))
            pts.append(
                (pos[0] + math.cos(angle) * dist, pos[1] + math.sin(angle) * dist)
            )
        pygame.draw.polygon(screen, self.color, pts)


class FishEgg:
    def __init__(
        self,
        x,
        y,
        traits,
        parent1=None,
        parent2=None,
        is_cleaner=False,
        is_predator=False,
    ):
        self.x, self.y = x, y
        self.traits = traits
        self.parent1 = parent1
        self.parent2 = parent2
        self.is_cleaner = is_cleaner
        self.is_predator = is_predator
        self.timer = FISH_EGG_HATCH_TIME
        self.pulse_offset = random.uniform(0, math.pi * 2)

    def update(self, dt, world):
        self.timer -= dt
        ty = world.get_terrain_height(self.x)
        if self.y < ty - 4:
            self.y += 15 * dt
        return self.timer <= 0

    def draw(self, screen, camera):
        time = pygame.time.get_ticks() * 0.001
        pulse = (math.sin(time * 3 + self.pulse_offset) + 1) * 0.5
        base_color = (200, 200, 255) if self.is_cleaner else (255, 180, 100)
        if self.is_predator:
            base_color = (255, 100, 100)
        surf = pygame.Surface((20, 20), pygame.SRCALPHA)
        pygame.draw.circle(surf, (*base_color, 80), (10, 10), 6 + pulse * 2)
        pygame.draw.circle(surf, (255, 255, 255, 150), (10, 10), 7 + pulse, 1)
        core_color = tuple(min(255, c + 50) for c in base_color)
        pygame.draw.circle(surf, core_color, (10, 8), 2 + pulse)
        pos = camera.apply((self.x, self.y))
        screen.blit(surf, (int(pos[0] - 10), int(pos[1] - 10)))


class NeuralFish:
    INPUT_COUNT = 14
    OUTPUT_COUNT = 2

    def __init__(self, world, traits=None, brain=None, is_cleaner=False):
        self.world = world
        self.is_cleaner = is_cleaner
        self.is_predator = False
        self.traits = traits if traits else FishTraits()
        self.brain = (
            brain if brain else NeuralNet(self.INPUT_COUNT, 12, self.OUTPUT_COUNT)
        )
        start_x = random.uniform(100, WORLD_WIDTH - 100)
        start_y = random.uniform(WATER_LINE_Y + 100, WORLD_HEIGHT - 200)
        self.physics = SteeringPhysics(start_x, start_y, FISH_MAX_SPEED, FISH_MAX_FORCE)
        self.age = 0.0
        self.energy = FISH_MAX_ENERGY * 0.8
        self.stamina = 100.0
        self.state = FishState.RESTING
        self.sex = random.choice(["M", "F"])
        self.mating_cooldown = 20.0
        self.is_mature = False
        self.is_hidden = False
        self.is_pregnant = False
        self.pregnancy_traits = None
        self.pregnancy_partner = None
        self.security_level = 0.0
        self.family = None

        # Store last neural activity for visualization
        self.last_inputs = [0.0] * self.INPUT_COUNT
        self.last_hidden = [0.0] * self.brain.hidden2_size
        self.last_outputs = [0.0] * self.OUTPUT_COUNT

        # Initialize fonts
        self.font_title = pygame.font.Font(None, 32)
        self.font_normal = pygame.font.Font(None, 24)
        self.font_small = pygame.font.Font(None, 18)

    @property
    def pos(self):
        return self.physics.pos

    def get_radar_inputs(self, all_fish, targets, plant_manager):
        radar = [0.0] * 9
        self.is_hidden = False
        min_plant_dist = 9999
        self.closest_plant = None
        for plant in plant_manager.plants:
            dist_to_base = self.physics.pos.distance_to((plant.x, plant.base_y))
            if dist_to_base < min_plant_dist:
                min_plant_dist = dist_to_base
                self.closest_plant = plant
            if dist_to_base < 60:
                self.is_hidden = True
                self.security_level = max(0, 1.0 - (min_plant_dist / 160.0))

        def fill_radar(objects, offset, is_threat_radar=False):
            for obj in objects:
                if is_threat_radar and getattr(obj, "is_hidden", False):
                    continue
                ox = getattr(
                    obj, "x", obj.physics.pos.x if hasattr(obj, "physics") else 0
                )
                oy = getattr(
                    obj, "y", obj.physics.pos.y if hasattr(obj, "physics") else 0
                )
                dist = self.physics.pos.distance_to((ox, oy))
                detection_range = FISH_SENSOR_RANGE
                if is_threat_radar and self.is_hidden:
                    detection_range *= 0.5
                if dist < detection_range and dist > 0:
                    angle = math.atan2(dy, dx) - self.physics.heading
                    angle = (angle + math.pi) % (2 * math.pi) - math.pi
                    if abs(angle) < FISH_SENSOR_ARC:
                        sector = int(
                            (angle + FISH_SENSOR_ARC) / (2 * FISH_SENSOR_ARC) * 3
                        )
                        sector = max(0, min(2, sector))
                        radar[offset + sector] += 1.0 - (dist / detection_range)

        fill_radar(targets, 0)
        threats = [f for f in all_fish if getattr(f, "is_predator", False)]
        fill_radar(threats, 3, is_threat_radar=True)
        mates = [
            f
            for f in all_fish
            if f.is_cleaner == self.is_cleaner
            and f.is_predator == self.is_predator
            and f.sex != self.sex
            and f.is_mature
        ]
        fill_radar(mates, 6)
        return [min(1.0, v) for v in radar]

    def update(self, dt, all_fish, targets, particle_system, plant_manager):
        self.age += dt
        self.energy -= 0.1 * dt
        self.mating_cooldown = max(0, self.mating_cooldown - dt)
        self.is_mature = self.age > (FISH_LARVA_DURATION + FISH_JUVENILE_DURATION)

        radar = self.get_radar_inputs(all_fish, targets, plant_manager)

        # State determination
        threat_level = sum(radar[3:6])
        if threat_level > 0.3:
            self.state = FishState.FLEEING
        elif self.is_pregnant:
            self.state = FishState.NESTING
        elif self.energy < FISH_HUNGER_THRESHOLD:
            self.state = FishState.HUNTING
        elif (
            self.is_mature
            and self.energy > FISH_MATING_THRESHOLD
            and self.mating_cooldown <= 0
        ):
            self.state = FishState.MATING
        else:
            self.state = FishState.RESTING

        # Neural Forward Pass
        stats = [
            self.energy / FISH_MAX_ENERGY,
            self.stamina / 100.0,
            (self.physics.pos.y - WATER_LINE_Y) / (WORLD_HEIGHT - WATER_LINE_Y),
            self.physics.vel.length() / FISH_MAX_SPEED,
            self.security_level,
        ]

        self.last_inputs = radar + stats
        outputs, hidden = self.brain.forward(self.last_inputs)
        self.last_hidden = hidden
        self.last_outputs = outputs

        # Influence Steering based on State
        max_speed_mod = 1.0
        if self.state == FishState.FLEEING:
            if self.closest_plant:
                self.physics.apply_force(
                    self.physics.seek(
                        self.closest_plant.x, self.closest_plant.base_y, weight=2.0
                    )
                )
            max_speed_mod = 1.3
        elif self.state == FishState.NESTING:
            if self.closest_plant:
                self.physics.apply_force(
                    self.physics.seek(
                        self.closest_plant.x, self.closest_plant.base_y, weight=1.5
                    )
                )
                if (
                    self.physics.pos.distance_to(
                        (self.closest_plant.x, self.closest_plant.base_y)
                    )
                    < 40
                ):
                    self.is_pregnant = False
                    partner = self.pregnancy_partner
                    self.pregnancy_partner = None
                    return (
                        "egg",
                        self.physics.pos[0],
                        self.physics.pos[1],
                        self.pregnancy_traits,
                        self,
                        partner,
                    )
        elif self.state == FishState.RESTING:
            max_speed_mod = 0.3
            if self.closest_plant and not self.is_hidden:
                self.physics.apply_force(
                    self.physics.seek(
                        self.closest_plant.x, self.closest_plant.base_y, weight=0.5
                    )
                )

        # Family behavior
        if self.family and self.family.active:
            if self.is_mature and not self.is_pregnant:
                child_positions = [
                    (c.physics.pos.x, c.physics.pos.y)
                    for c in self.family.children
                    if not c.is_mature
                ]
                if child_positions:
                    avg_x = sum(p[0] for p in child_positions) / len(child_positions)
                    avg_y = sum(p[1] for p in child_positions) / len(child_positions)
                    self.physics.apply_force(
                        self.physics.seek(avg_x, avg_y, weight=0.8)
                    )

        # Apply Neural steering
        steer_input, thrust_input = outputs[0], (outputs[1] + 1.0) / 2.0
        desired_angle = self.physics.heading + steer_input * 0.8
        self.physics.apply_force(
            (
                (
                    (math.cos(desired_angle) * FISH_MAX_SPEED * max_speed_mod)
                    - self.physics.vel.x
                )
                * 0.1,
                (
                    (math.sin(desired_angle) * FISH_MAX_SPEED * max_speed_mod)
                    - self.physics.vel.y
                )
                * 0.1,
            )
        )
        force_mag = (
            thrust_input
            * self.physics.max_force
            * (1.8 if self.state == FishState.FLEEING else 1.0)
        )
        self.physics.apply_force(
            (
                math.cos(self.physics.heading) * force_mag,
                math.sin(self.physics.heading) * force_mag,
            )
        )

        self.physics.bounce_bounds(
            0,
            WATER_LINE_Y + 20,
            WORLD_WIDTH,
            self.world.get_terrain_height(self.physics.pos.x),
        )
        self.physics.update(dt, FISH_DRAG)

        # Collision with food
        for t in targets[:]:
            if self.is_predator:
                break  # Predators handle eating via their own update logic
            tx = getattr(t, "x", t.physics.pos.x if hasattr(t, "physics") else 0)
            ty = getattr(t, "y", t.physics.pos.y if hasattr(t, "physics") else 0)
            if self.physics.pos.distance_to((tx, ty)) < 25:
                self.energy = min(FISH_MAX_ENERGY, self.energy + 12.0)
                if hasattr(t, "reset"):
                    t.reset()
                elif t in targets:
                    targets.remove(t)
                break

        if random.random() < 0.001 * (self.energy / FISH_MAX_ENERGY):
            return PoopParticle(self.physics.pos.x, self.physics.pos.y)
        return None

    def draw(self, screen, camera, time, selected):
        pos = self.physics.pos
        if not camera.is_visible(pos, margin=60):
            return

        angle = self.physics.heading
        size = self.traits.physical_traits.get("size_mult", 1.0) * 4
        color = self.get_color()
        tail_angle = angle + math.pi + math.sin(time * 10) * 0.4
        screen_pos = camera.apply(pos)
        tail_pts = [
            (screen_pos[0], screen_pos[1]),
            (
                screen_pos[0] + math.cos(tail_angle - 0.6) * size * 2.5,
                screen_pos[1] + math.sin(tail_angle - 0.6) * size * 2.5,
            ),
            (
                screen_pos[0] + math.cos(tail_angle + 0.6) * size * 2.5,
                screen_pos[1] + math.sin(tail_angle + 0.6) * size * 2.5,
            ),
        ]
        pygame.draw.polygon(screen, color, tail_pts)

        body_surf = pygame.Surface((size * 6, size * 4), pygame.SRCALPHA)
        pygame.draw.ellipse(body_surf, (*color, 255), (size, size, size * 4, size * 2))
        if self.is_pregnant:
            pygame.draw.circle(
                body_surf, (255, 200, 200, 150), (size * 2.5, size * 2), size * 1.2
            )
        rotated_body = pygame.transform.rotate(body_surf, -math.degrees(angle))
        screen.blit(
            rotated_body,
            rotated_body.get_rect(center=(int(screen_pos[0]), int(screen_pos[1]))),
        )

        eye_x, eye_y = (
            screen_pos[0] + math.cos(angle + 0.35) * size * 1.3,
            screen_pos[1] + math.sin(angle + 0.35) * size * 1.3,
        )
        pygame.draw.circle(screen, (255, 255, 255), (int(eye_x), int(eye_y)), 2)
        pygame.draw.circle(screen, (0, 0, 0), (int(eye_x), int(eye_y)), 1)

        if selected:
            pygame.draw.circle(
                screen,
                (255, 255, 200),
                (int(screen_pos[0]), int(screen_pos[1])),
                size + 15,
                2,
            )

    def draw_brain(self, screen, time):
        """High-contrast brain visualization"""
        panel_width, panel_height = 540, 640
        surface = pygame.Surface((panel_width, panel_height), pygame.SRCALPHA)
        surface.fill((5, 10, 25, 245))
        pygame.draw.rect(surface, (0, 200, 255), (0, 0, panel_width, panel_height), 4)

        y_offset = 20
        # Title
        species = (
            "Predator"
            if self.is_predator
            else ("Cleaner" if self.is_cleaner else "Common")
        )
        tag_color = (
            (255, 100, 100)
            if self.is_predator
            else ((100, 200, 255) if self.is_cleaner else (255, 180, 50))
        )
        surface.blit(
            self.font_title.render(f"{species} Fish Brain", True, tag_color),
            (20, y_offset),
        )
        y_offset += 40

        # Identity Block
        life_stage = (
            "Larva"
            if self.age < FISH_LARVA_DURATION
            else (
                "Juvenile"
                if self.age < FISH_LARVA_DURATION + FISH_JUVENILE_DURATION
                else "Adult"
            )
        )
        sex_icon = "♂ Male" if self.sex == "M" else "♀ Female"
        maturity = "Mature" if self.is_mature else "Immature"
        pregnancy_text = "PREGNANT" if self.is_pregnant else ""

        id_text = f"{life_stage} {sex_icon} | {maturity}"
        surface.blit(
            self.font_normal.render(id_text, True, (255, 255, 255)), (20, y_offset)
        )

        if pregnancy_text:
            preg_surf = self.font_normal.render(pregnancy_text, True, (255, 150, 150))
            surface.blit(preg_surf, (panel_width - 140, y_offset))

        y_offset += 25

        # State display
        surface.blit(
            self.font_small.render(
                f"CURRENT FOCUS: {self.state.name}", True, (200, 255, 200)
            ),
            (20, y_offset),
        )
        y_offset += 25

        # --- Progress Bars ---
        # 1. Life Progress (remaining)
        current_max = FISH_MAX_AGE * self.traits.physical_traits.get(
            "lifespan_mult", 1.0
        )
        life_ratio = max(0.0, 1.0 - (self.age / current_max))
        surface.blit(
            self.font_small.render(
                f"LIFE ({int(life_ratio * 100)}%)", True, (200, 200, 200)
            ),
            (20, y_offset),
        )
        pygame.draw.rect(surface, (40, 40, 40), (100, y_offset + 2, 120, 12))
        pygame.draw.rect(
            surface, (150, 200, 255), (100, y_offset + 2, int(120 * life_ratio), 12)
        )

        # 2. Energy Bar
        energy_ratio = max(0.0, min(1.0, self.energy / FISH_MAX_ENERGY))
        surface.blit(
            self.font_small.render("ENERGY", True, (200, 200, 200)), (250, y_offset)
        )
        pygame.draw.rect(surface, (40, 40, 40), (320, y_offset + 2, 120, 12))
        pygame.draw.rect(
            surface,
            self._get_gradient_color(energy_ratio),
            (320, y_offset + 2, int(120 * energy_ratio), 12),
        )

        y_offset += 35

        # Network Visualization
        surface.blit(
            self.font_normal.render("NEURAL ACTIVITY MAP", True, (255, 255, 255)),
            (20, y_offset),
        )
        y_offset += 40

        # Draw connections and nodes (restored logic)
        input_x, hidden_x, output_x = 60, 220, 380
        input_spacing, node_radius = 28, 10
        input_labels = [
            "Food L",
            "Food C",
            "Food R",
            "Threat L",
            "Threat C",
            "Threat R",
            "Mate L",
            "Mate C",
            "Mate R",
            "Energy",
            "Stamina",
            "Depth",
            "Speed",
            "Safety",
        ]

        # Draw Connections
        for i, inp_val in enumerate(self.last_inputs):
            iy = y_offset + i * input_spacing
            for h, hid_val in enumerate(self.last_hidden):
                hy = y_offset + 80 + h * 50
                if abs(inp_val) > 0.1:
                    a_color = self._get_activation_color(inp_val)
                    pygame.draw.line(
                        surface, (*a_color, 40), (input_x, iy), (hidden_x, hy), 1
                    )

        for h, hid_val in enumerate(self.last_hidden):
            hy = y_offset + 80 + h * 50
            for o, out_val in enumerate(self.last_outputs):
                oy = y_offset + 180 + o * 120
                if abs(hid_val) > 0.1:
                    a_color = self._get_activation_color(hid_val)
                    pygame.draw.line(
                        surface, (*a_color, 80), (hidden_x, hy), (output_x, oy), 2
                    )

        # Draw Nodes
        for i, (val, lbl) in enumerate(zip(self.last_inputs, input_labels)):
            ny = y_offset + i * input_spacing
            pygame.draw.circle(
                surface, self._get_activation_color(val), (input_x, ny), node_radius
            )
            pygame.draw.circle(surface, (255, 255, 255), (input_x, ny), node_radius, 2)
            surface.blit(
                self.font_small.render(lbl, True, (220, 220, 220)),
                (input_x + 18, ny - 6),
            )

        for h, val in enumerate(self.last_hidden):
            ny = y_offset + 80 + h * 50
            pygame.draw.circle(
                surface,
                self._get_activation_color(val),
                (hidden_x, ny),
                node_radius + 2,
            )

    def _get_activation_color(self, value):
        """High-contrast color scale: Magenta (Neg) -> Grey (Neutral) -> Green (Pos)"""

        def lerp_color(c1, c2, t):
            return tuple(int(a + (b - a) * t) for a, b in zip(c1, c2))

        NEUTRAL_COLOR = (100, 100, 100)
        POSITIVE_COLOR = (50, 255, 50)
        NEGATIVE_COLOR = (255, 50, 255)

        t = min(1.0, abs(value))
        if value > 0:
            return lerp_color(NEUTRAL_COLOR, POSITIVE_COLOR, t)
        else:
            return lerp_color(NEUTRAL_COLOR, NEGATIVE_COLOR, t)

    def _get_gradient_color(self, ratio):
        ratio = max(0, min(1, ratio))
        if ratio < 0.5:
            return (255, int(255 * ratio * 2), 50)
        return (int(255 * (1 - (ratio - 0.5) * 2)), 255, 50)

    def get_color(self):
        if self.is_predator:
            base = [220, 60, 60]
        elif self.is_cleaner:
            base = [100, 180, 220]
        else:
            base = [255, 160, 60]
        color = [
            max(0, min(255, base[i] + self.traits.color_offset[i])) for i in range(3)
        ]
        factor = 1.0 - (self.age / FISH_MAX_AGE) * 0.4
        return tuple(max(0, min(255, int(c * factor))) for c in color)


class FishSystem:
    def __init__(self, particle_system, plant_manager, world):
        self.world, self.particle_system, self.plant_manager = (
            world,
            particle_system,
            plant_manager,
        )
        # Link world to system so predators can find mates in population lists
        self.world.fish_system = self

        self.fish = [NeuralFish(world) for _ in range(FISH_MAX_POPULATION // 2)]
        from cleaner_fish import CleanerFish
        from predator_fish import PredatorFish

        self.cleaner_fish = [
            CleanerFish(world) for _ in range(CLEANER_FISH_MAX_POPULATION // 2)
        ]
        self.predators = [PredatorFish(world) for _ in range(PREDATOR_MAX_POPULATION)]
        self.poops, self.eggs = [], []
        self.selected_fish = None
        self.families = []

    def handle_click(self, pos, camera):
        # Convert screen click to world coordinates
        world_x = pos[0] + camera.x
        world_y = pos[1] + camera.y

        all_f = self.fish + self.cleaner_fish + self.predators
        if not all_f:
            return
        clicked = min(
            all_f,
            key=lambda f: f.physics.pos.distance_to((world_x, world_y)),
        )
        if clicked.physics.pos.distance_to((world_x, world_y)) < 40:
            self.selected_fish = clicked
        else:
            self.selected_fish = None

    def update(self, dt):
        all_fish = self.fish + self.cleaner_fish + self.predators

        # 1. Predator Reproduction Cycle
        for predator in self.predators:
            if (
                hasattr(predator, "try_reproduce")
                and predator.try_reproduce()
                and len(self.predators) < PREDATOR_MAX_POPULATION
            ):
                egg = FishEgg(
                    predator.physics.pos.x,
                    predator.physics.pos.y,
                    predator.traits.mutate(),
                    parent1=predator,
                    parent2=predator.mate,
                    is_predator=True,
                )
                self.eggs.append(egg)

        # Update eggs
        for egg in self.eggs[:]:
            if egg.update(dt, self.world):
                self.eggs.remove(egg)
                self.spawn_from_egg(egg)

        # 3. Handle Family Units
        for family in self.families[:]:
            family.update(dt)
            if not family.active:
                self.families.remove(family)

        # 4. Handle Sediment/Fertilizer
        for p in self.poops[:]:
            if not p.update(dt, self.world):
                self.poops.remove(p)

        # 5. Core Simulation Loop
        plankton = [p for p in self.particle_system.particles if p.is_plankton]

        # Mapping populations to their targets and reproductive capability
        sim_groups = [
            (self.fish, plankton, True),
            (self.cleaner_fish, self.poops, True),
            (self.predators, self.fish + self.cleaner_fish, False),
        ]

        for f_list, targets, can_mate in sim_groups:
            for f in f_list[:]:
                res = f.update(
                    dt, all_fish, targets, self.particle_system, self.plant_manager
                )

                # Handle physical results (Poop or Eggs)
                if isinstance(res, PoopParticle):
                    self.poops.append(res)
                elif isinstance(res, tuple) and res[0] == "egg":
                    self.eggs.append(
                        FishEgg(
                            res[1],
                            res[2],
                            res[3],
                            res[4],
                            res[5],
                            f.is_cleaner,
                            f.is_predator,
                        )
                    )

                # Handle death
                lifespan = FISH_MAX_AGE * f.traits.physical_traits.get(
                    "lifespan_mult", 1.0
                )
                if f.energy <= 0 or f.age > lifespan:
                    if f == self.selected_fish:
                        self.selected_fish = None
                    f_list.remove(f)
                    continue

                # Handle mating attempts (within subspecies)
                if can_mate and f.state == FishState.MATING:
                    self.try_mate(f, f_list)

        # Maintain base population
        if len(self.fish) < 6:
            self.fish.append(NeuralFish(self.world))

    def try_mate(self, f, f_list):
        if f.is_pregnant:
            return
        for partner in f_list:
            if (
                partner != f
                and partner.state == FishState.MATING
                and partner.sex != f.sex
            ):
                if f.physics.pos.distance_to(partner.physics.pos) < 45:
                    f.energy -= FISH_REPRODUCTION_COST
                    partner.energy -= FISH_REPRODUCTION_COST
                    f.mating_cooldown, partner.mating_cooldown = 40.0, 40.0
                    child_traits = FishTraits.blend(f.traits, partner.traits)
                    mother = f if f.sex == "F" else partner
                    father = partner if f.sex == "F" else f
                    mother.is_pregnant = True
                    mother.pregnancy_traits, mother.pregnancy_partner = (
                        child_traits,
                        father,
                    )
                    break

    def spawn_from_egg(self, egg):
        if egg.is_cleaner:
            from cleaner_fish import CleanerFish

            child = CleanerFish(self.world, traits=egg.traits)
            self.cleaner_fish.append(child)
        elif egg.is_predator:
            from predator_fish import PredatorFish

            child = PredatorFish(self.world, traits=egg.traits)
            self.predators.append(child)
        else:
            child = NeuralFish(self.world, traits=egg.traits)
            self.fish.append(child)

        p1, p2 = egg.parent1, egg.parent2
        all_f = self.fish + self.cleaner_fish + self.predators
        if p1 in all_f and p2 in all_f:
            family = Family(p1, p2, [child], self)
            self.families.append(family)
            p1.family, p2.family, child.family = family, family, family

    def draw(self, screen, camera, time):
        for e in self.eggs:
            e.draw(screen, camera)
        for p in self.poops:
            p.draw(screen, camera)
        for f in self.fish + self.cleaner_fish + self.predators:
            f.draw(screen, camera, time, f == self.selected_fish)
        if self.selected_fish:
            self.selected_fish.draw_brain(screen, time)
