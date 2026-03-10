# Updated class diagram for camera-aware world and simulation systems

```markdown
classDiagram
class Simulation {
+screen
+clock
+world
+camera
+plant_manager
+particle_system
+fish_system
+time
+handle_events()
+update()
+draw()
+run()
}

    class Camera {
        +float x
        +float y
        +int width
        +int height
        +target
        +follow(target)
        +update()
        +apply(pos)
        +is_visible(pos, margin)
        +get_view_rect()
    }

    class World {
        +initial_terrain
        +SoilGrid soil_grid
        +water_gradient_surface
        +haze_surface
        +_generate_initial_profile()
        +get_initial_terrain_height(x)
        +get_terrain_height(x)
        +get_depth_ratio(y)
        +render_water_gradient()
        +draw(screen, camera)
    }

    class SoilGrid {
        +dict cells
        +int cell_size
        +generate_soil()
        +get_cell(cx, cy)
        +get_neighbors(cx, cy)
        +update(dt)
        +diffuse(dt)
        +draw(screen, camera, time)
    }

    class SoilCell {
        +int x
        +int y
        +bool is_water
        +float nutrient
        +bool is_solid
        +float jitter_x
        +float jitter_y
        +grains
        +deplete(amount)
        +solidify()
        +update(dt)
        +get_color(time)
    }

    class PlantManager {
        +world
        +plants
        +seeds
        +bubbles
        +spawn_initial_seeds()
        +update(dt)
        +draw(screen, camera, time)
    }

    class Plant {
        +float x
        +float base_y
        +string plant_type
        +RootSystem root_system
        +PlantDevelopment development
        +seed_release_cooldown
        +floating_leaves
        +decomposition_particles
        +update(dt, soil_grid)
        +produce_seed(time)
        +draw(screen, camera, time, soil_grid)
        +draw_seagrass(screen, camera, time, color, height)
        +draw_kelp(screen, camera, time, color, height)
        +draw_algae(screen, camera, time, color, height)
        +get_tip_position(time)
        +draw_roots(screen, camera, time)
    }

    class RootSystem {
        +plant_base_x
        +plant_base_y
        +soil_grid
        +roots
        +tips
        +total_harvested
        +update(dt, shoot_height)
        +grow_step()
        +transport_nutrients()
        +harvest_nutrients()
        +draw(screen, camera, time)
    }

    class RootNode {
        +int cell_x
        +int cell_y
        +RootNode parent
        +children
        +float stored_nutrient
        +float flow_pulse
        +bool is_tip
        +get_depth()
        +get_pixel_position(cell_size)
    }

    class ParticleSystem {
        +particles
        +particle_surface
        +update(time)
        +draw(screen, camera)
    }

    class Particle {
        +bool is_plankton
        +float x
        +float y
        +int size
        +float speed_x
        +float speed_y
        +float phase
        +color
        +reset()
        +update(time)
    }

    class FishSystem {
        +world
        +particle_system
        +plant_manager
        +fish
        +cleaner_fish
        +predators
        +poops
        +eggs
        +selected_fish
        +families
        +handle_click(pos, camera)
        +update(dt)
        +try_mate(f, f_list)
        +spawn_from_egg(egg)
        +draw(screen, camera, time)
    }

    class NeuralFish {
        +SteeringPhysics physics
        +FishTraits traits
        +bool is_cleaner
        +bool is_predator
        +float age
        +float energy
        +float stamina
        +FishState state
        +string sex
        +bool is_mature
        +bool is_hidden
        +family
        +closest_plant
        +brain
        +last_inputs
        +last_hidden
        +last_outputs
        +property pos
        +get_radar_inputs(all_fish, targets, plant_manager)
        +update(dt, all_fish, targets, particle_system, plant_manager)
        +draw(screen, camera, time, selected)
        +draw_brain(screen, time)
        +get_color()
    }

    class CleanerFish {
        +update(dt, all_fish, targets, particle_system, plant_manager)
    }

    class PredatorFish {
        +bool is_dashing
        +float dash_timer
        +float dash_cooldown
        +update(dt, all_fish, targets, particle_system, plant_manager)
    }

    class PoopParticle {
        +float x
        +float y
        +float size
        +float rot
        +color
        +update(dt, world)
        +draw(screen, camera)
    }

    class FishEgg {
        +float x
        +float y
        +traits
        +parent1
        +parent2
        +bool is_cleaner
        +bool is_predator
        +timer
        +pulse_offset
        +update(dt, world)
        +draw(screen, camera)
    }

    class SteeringPhysics {
        +Vector2 pos
        +Vector2 vel
        +Vector2 acc
        +float max_speed
        +float max_force
        +float heading
        +apply_force(force)
        +seek(target_x, target_y, weight)
        +update(dt, drag)
        +bounce_bounds(min_x, min_y, max_x, max_y)
    }

    class Seed {
        +string plant_type
        +traits
        +float x
        +float y
        +float vx
        +float vy
        +float age
        +mutate(parent_traits)
        +update(dt, world)
        +draw(screen, camera)
    }

    Simulation --> World
    Simulation --> Camera
    Simulation --> PlantManager
    Simulation --> ParticleSystem
    Simulation --> FishSystem

    World *-- SoilGrid
    SoilGrid *-- SoilCell

    PlantManager *-- Plant
    PlantManager *-- Seed

    Plant *-- RootSystem
    RootSystem *-- RootNode

    ParticleSystem *-- Particle

    FishSystem *-- NeuralFish
    FishSystem *-- CleanerFish
    FishSystem *-- PredatorFish
    FishSystem *-- PoopParticle
    FishSystem *-- FishEgg

    NeuralFish *-- SteeringPhysics

    CleanerFish --|> NeuralFish
    PredatorFish --|> NeuralFish

    World ..> Camera : uses in draw
    PlantManager ..> Camera : uses in draw
    ParticleSystem ..> Camera : uses in draw
    FishSystem ..> Camera : uses in draw and handle_click
    SoilGrid ..> Camera : uses in draw
    RootSystem ..> Camera : uses in draw
    Seed ..> Camera : uses in draw
    PoopParticle ..> Camera : uses in draw
    NeuralFish ..> Camera : uses in draw
```
