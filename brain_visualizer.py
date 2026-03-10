import pygame
import math
from config import (BRAIN_PANEL_WIDTH, BRAIN_PANEL_HEIGHT, FishState, FISH_MAX_AGE, FISH_MAX_ENERGY, 
                   FISH_LARVA_DURATION, FISH_JUVENILE_DURATION, FISH_ELDER_DURATION)


class BrainVisualizer:
    def __init__(self, screen_width, screen_height):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.panel_width = BRAIN_PANEL_WIDTH
        self.panel_height = min(BRAIN_PANEL_HEIGHT, screen_height)
        self.panel_offset_x = self.panel_width  # Start fully off-screen
        self.anim_intensity = 0.5
        self.state_flash_timer = 0.0
        self.prev_state = None
        
        # Initialize fonts
        self.font_title = pygame.font.Font(None, 28)
        self.font_normal = pygame.font.Font(None, 22)
        self.font_small = pygame.font.Font(None, 18)
        self.font_tiny = pygame.font.Font(None, 14)
        
        # Species accent colors
        self.species_colors = {
            (False, False): (255, 180, 50),   # Common - amber
            (True, False): (100, 200, 255),    # Cleaner - cyan  
            (False, True): (255, 100, 100),    # Predator - red
        }
        
        # Animation intensity mapping by state
        self._ANIM_INTENSITY_MAP = {
            FishState.RESTING: 0.3,
            FishState.HUNTING: 0.7,
            FishState.FLEEING: 1.0,
            FishState.MATING: 0.6,
            FishState.NESTING: 0.5,
        }

    def update(self, dt, selected_fish):
        if selected_fish is not None:
            # Slide panel in
            self.panel_offset_x = max(0, self.panel_offset_x - 12 * dt * 60)
            
            # Update animation intensity
            target_intensity = self._ANIM_INTENSITY_MAP.get(selected_fish.state, 0.5)
            self.anim_intensity += (target_intensity - self.anim_intensity) * 2.0 * dt
            
            # State change flash
            if selected_fish.state != self.prev_state:
                self.state_flash_timer = 0.5
            self.prev_state = selected_fish.state
        else:
            # Slide panel out
            self.panel_offset_x = min(self.panel_width, self.panel_offset_x + 12 * dt * 60)
        
        # Update flash timer
        if self.state_flash_timer > 0:
            self.state_flash_timer = max(0, self.state_flash_timer - dt)

    def draw(self, screen, selected_fish, time):
        if self.panel_offset_x >= self.panel_width:
            return  # Fully hidden
        
        # Create panel surface
        surface = pygame.Surface((self.panel_width, self.panel_height), pygame.SRCALPHA)
        surface.fill((4, 8, 20, 250))
        
        # Get species accent color
        accent_color = self.species_colors.get(
            (selected_fish.is_cleaner, selected_fish.is_predator), (255, 180, 50)
        )
        
        # Draw border
        pygame.draw.rect(surface, accent_color, (0, 0, self.panel_width, self.panel_height), 3)
        
        # Draw sections
        y_cursor = 20
        y_cursor = self._draw_header(surface, selected_fish, time, y_cursor)
        y_cursor = self._draw_status_bars(surface, selected_fish, y_cursor)
        y_cursor = self._draw_network(surface, selected_fish, time, y_cursor)
        y_cursor = self._draw_output_footer(surface, selected_fish, time, y_cursor)
        y_cursor = self._draw_traits(surface, selected_fish, y_cursor)
        y_cursor = self._draw_lifetime_stats(surface, selected_fish, y_cursor)
        
        # Blit to screen
        screen.blit(
            surface,
            (self.screen_width - self.panel_width + int(self.panel_offset_x), 0)
        )

    def _get_activation_color(self, value):
        """Cyan/grey/magenta scale for activations"""
        neutral = (50, 50, 60)
        positive = (0, 255, 220)
        negative = (220, 0, 180)
        
        t = min(1.0, abs(value))
        if value > 0:
            return tuple(int(neutral[i] + (positive[i] - neutral[i]) * t) for i in range(3))
        else:
            return tuple(int(neutral[i] + (negative[i] - neutral[i]) * t) for i in range(3))

    def _draw_header(self, surface, fish, time, y_cursor):
        # Species badge
        species = "Predator" if fish.is_predator else ("Cleaner" if fish.is_cleaner else "Common")
        accent_color = self.species_colors.get((fish.is_cleaner, fish.is_predator), (255, 180, 50))
        
        # Draw rounded rect pill for species
        pill_rect = pygame.Rect(20, y_cursor, 120, 28)
        pygame.draw.rect(surface, accent_color, pill_rect, border_radius=14)
        species_text = self.font_normal.render(species, True, (255, 255, 255))
        surface.blit(species_text, (pill_rect.x + 10, pill_rect.y + 4))
        
        y_cursor += 35
        
        # Fish identity line
        life_stage = "Larva"
        if fish.age >= FISH_LARVA_DURATION + FISH_JUVENILE_DURATION:
            life_stage = "Adult"
        elif fish.age >= FISH_LARVA_DURATION:
            life_stage = "Juvenile"
        elif fish.age >= FISH_ELDER_DURATION:
            life_stage = "Elder"
            
        sex_icon = "♂" if fish.sex == "M" else "♀"
        maturity = "Mature" if fish.is_mature else "Immature"
        pregnancy = " PREGNANT" if fish.is_pregnant else ""
        
        identity_text = f"{sex_icon} {life_stage} • {maturity}{pregnancy}"
        text_surf = self.font_small.render(identity_text, True, (220, 220, 220))
        surface.blit(text_surf, (20, y_cursor))
        
        y_cursor += 25
        
        # State label with flash effect
        state_colors = {
            FishState.RESTING: (100, 200, 100),
            FishState.HUNTING: (255, 170, 0),
            FishState.FLEEING: (255, 100, 100),
            FishState.MATING: (255, 150, 200),
            FishState.NESTING: (200, 150, 255),
        }
        base_color = state_colors.get(fish.state, (200, 200, 200))
        
        # Apply flash effect
        if self.state_flash_timer > 0:
            flash_factor = self.state_flash_timer / 0.5
            color = tuple(int(base_color[i] + (255 - base_color[i]) * flash_factor) for i in range(3))
        else:
            color = base_color
            
        state_text = self.font_normal.render(fish.state.name, True, color)
        surface.blit(state_text, (20, y_cursor))
        
        y_cursor += 30
        
        # Separator line
        pygame.draw.line(surface, (80, 80, 80), (20, y_cursor), (self.panel_width - 20, y_cursor))
        y_cursor += 15
        
        return y_cursor

    def _draw_status_bars(self, surface, fish, y_cursor):
        bar_width = 280
        bar_height = 16
        label_width = 58
        
        # LIFE bar
        current_max = FISH_MAX_AGE * fish.traits.physical_traits.get("lifespan_mult", 1.0)
        life_ratio = max(0, 1 - fish.age / current_max)
        
        life_label = self.font_small.render("LIFE", True, (200, 200, 200))
        surface.blit(life_label, (20, y_cursor))
        
        bar_x = 20 + label_width
        pygame.draw.rect(surface, (40, 40, 40), (bar_x, y_cursor, bar_width, bar_height))
        pygame.draw.rect(surface, (100, 150, 255), (bar_x, y_cursor, int(bar_width * life_ratio), bar_height))
        
        life_pct = self.font_tiny.render(f"{int(life_ratio * 100)}%", True, (180, 180, 180))
        surface.blit(life_pct, (bar_x + bar_width + 8, y_cursor + 2))
        
        y_cursor += 25
        
        # ENERGY bar with gradient
        energy_ratio = max(0, min(1, fish.energy / FISH_MAX_ENERGY))
        
        energy_label = self.font_small.render("ENERGY", True, (200, 200, 200))
        surface.blit(energy_label, (20, y_cursor))
        
        pygame.draw.rect(surface, (40, 40, 40), (bar_x, y_cursor, bar_width, bar_height))
        
        # Gradient fill
        if energy_ratio < 0.5:
            color = (255, int(255 * energy_ratio * 2), 50)
        else:
            color = (int(255 * (1 - (energy_ratio - 0.5) * 2)), 255, 50)
        pygame.draw.rect(surface, color, (bar_x, y_cursor, int(bar_width * energy_ratio), bar_height))
        
        energy_pct = self.font_tiny.render(f"{int(energy_ratio * 100)}%", True, (180, 180, 180))
        surface.blit(energy_pct, (bar_x + bar_width + 8, y_cursor + 2))
        
        y_cursor += 25
        
        # STAMINA bar
        stamina_ratio = fish.stamina / 100.0
        
        stamina_label = self.font_small.render("STAMINA", True, (200, 200, 200))
        surface.blit(stamina_label, (20, y_cursor))
        
        pygame.draw.rect(surface, (40, 40, 40), (bar_x, y_cursor, bar_width, bar_height))
        pygame.draw.rect(surface, (150, 255, 150), (bar_x, y_cursor, int(bar_width * stamina_ratio), bar_height))
        
        stamina_pct = self.font_tiny.render(f"{int(stamina_ratio * 100)}%", True, (180, 180, 180))
        surface.blit(stamina_pct, (bar_x + bar_width + 8, y_cursor + 2))
        
        y_cursor += 35
        
        # Separator line
        pygame.draw.line(surface, (80, 80, 80), (20, y_cursor), (self.panel_width - 20, y_cursor))
        y_cursor += 15
        
        return y_cursor

    def _compute_node_positions(self, net_section_top, net_section_height):
        """Compute positions for all neural network nodes"""
        positions = {}
        
        # Column x positions
        input_x = int(self.panel_width * 0.15)
        hidden1_x = int(self.panel_width * 0.38)
        hidden2_x = int(self.panel_width * 0.62)
        output_x = int(self.panel_width * 0.85)
        
        # Input nodes (14)
        positions["inputs"] = []
        for i in range(14):
            y = net_section_top + int((i + 0.5) * net_section_height / 14)
            positions["inputs"].append((input_x, y))
        
        # Hidden layer 1 (8)
        positions["hidden1"] = []
        for i in range(8):
            y = net_section_top + int((i + 0.5) * net_section_height / 8)
            positions["hidden1"].append((hidden1_x, y))
        
        # Hidden layer 2 (6)
        positions["hidden2"] = []
        for i in range(6):
            y = net_section_top + int((i + 0.5) * net_section_height / 6)
            positions["hidden2"].append((hidden2_x, y))
        
        # Output nodes (2)
        positions["outputs"] = []
        for i in range(2):
            y = net_section_top + int((i + 0.5) * net_section_height / 2)
            positions["outputs"].append((output_x, y))
        
        return positions

    def _draw_network(self, surface, fish, time, y_cursor):
        # Section title
        title = self.font_normal.render("NEURAL NETWORK", True, (255, 255, 255))
        surface.blit(title, (20, y_cursor))
        y_cursor += 35
        
        net_section_height = 280
        net_section_top = y_cursor
        
        # Compute node positions
        node_positions = self._compute_node_positions(net_section_top, net_section_height)
        
        # Draw connections (background pass)
        self._draw_connections(surface, fish, time, node_positions, background=True)
        
        # Draw nodes
        self._draw_nodes(surface, fish, time, node_positions)
        
        # Draw connections (foreground pass with ripples)
        self._draw_connections(surface, fish, time, node_positions, background=False)
        
        y_cursor += net_section_height + 20
        
        # Separator line
        pygame.draw.line(surface, (80, 80, 80), (20, y_cursor), (self.panel_width - 20, y_cursor))
        y_cursor += 15
        
        return y_cursor

    def _draw_connections(self, surface, fish, time, node_positions, background=True):
        if background:
            # Background pass - draw all connections faintly
            # Input to hidden1
            for i, pos_in in enumerate(node_positions["inputs"]):
                for h, pos_h1 in enumerate(node_positions["hidden1"]):
                    self._draw_bezier_curve(surface, pos_in, pos_h1, (40, 60, 80), 20, 1)
            
            # Hidden1 to hidden2  
            for h, pos_h1 in enumerate(node_positions["hidden1"]):
                for h2, pos_h2 in enumerate(node_positions["hidden2"]):
                    self._draw_bezier_curve(surface, pos_h1, pos_h2, (40, 60, 80), 20, 1)
            
            # Hidden2 to outputs
            for h2, pos_h2 in enumerate(node_positions["hidden2"]):
                for o, pos_out in enumerate(node_positions["outputs"]):
                    self._draw_bezier_curve(surface, pos_h2, pos_out, (40, 60, 80), 20, 1)
        else:
            # Foreground pass - draw active connections with ripples
            # Input to hidden1
            for i, pos_in in enumerate(node_positions["inputs"]):
                activation = fish.last_inputs[i] if i < len(fish.last_inputs) else 0
                if abs(activation) > 0.12:
                    color = self._get_activation_color(activation)
                    alpha = int(40 + abs(activation) * 180)
                    thickness = min(3.5, 1 + abs(activation) * 2.5)
                    
                    for h, pos_h1 in enumerate(node_positions["hidden1"]):
                        self._draw_bezier_curve(surface, pos_in, pos_h1, color, alpha, thickness)
                        # Add ripple
                        self._draw_ripple(surface, pos_in, pos_h1, color, time, activation)
            
            # Hidden1 to hidden2 (using last_hidden1 if available, otherwise last_hidden)
            hidden1_acts = getattr(fish, 'last_hidden1', fish.last_hidden[:8])
            for h, pos_h1 in enumerate(node_positions["hidden1"]):
                activation = hidden1_acts[h] if h < len(hidden1_acts) else 0
                if abs(activation) > 0.12:
                    color = self._get_activation_color(activation)
                    alpha = int(40 + abs(activation) * 180)
                    thickness = min(3.5, 1 + abs(activation) * 2.5)
                    
                    for h2, pos_h2 in enumerate(node_positions["hidden2"]):
                        self._draw_bezier_curve(surface, pos_h1, pos_h2, color, alpha, thickness)
                        self._draw_ripple(surface, pos_h1, pos_h2, color, time, activation)
            
            # Hidden2 to outputs
            for h2, pos_h2 in enumerate(node_positions["hidden2"]):
                activation = fish.last_hidden[h2] if h2 < len(fish.last_hidden) else 0
                if abs(activation) > 0.12:
                    color = self._get_activation_color(activation)
                    alpha = int(40 + abs(activation) * 180)
                    thickness = min(3.5, 1 + abs(activation) * 2.5)
                    
                    for o, pos_out in enumerate(node_positions["outputs"]):
                        self._draw_bezier_curve(surface, pos_h2, pos_out, color, alpha, thickness)
                        self._draw_ripple(surface, pos_h2, pos_out, color, time, activation)

    def _draw_bezier_curve(self, surface, p0, p1, color, alpha, thickness):
        """Draw a quadratic Bezier curve between two points"""
        # Calculate control point
        mid_x = (p0[0] + p1[0]) / 2
        mid_y = (p0[1] + p1[1]) / 2
        
        # Perpendicular offset for curve
        dx = p1[0] - p0[0]
        dy = p1[1] - p0[1]
        length = math.sqrt(dx*dx + dy*dy)
        if length > 0:
            perp_x = -dy / length * 25
            perp_y = dx / length * 25
        else:
            perp_x, perp_y = 0, 25
            
        control = (mid_x + perp_x, mid_y + perp_y)
        
        # Sample curve and draw line segments
        points = []
        for t in range(21):
            t_norm = t / 20.0
            x = (1-t_norm)*(1-t_norm)*p0[0] + 2*(1-t_norm)*t_norm*control[0] + t_norm*t_norm*p1[0]
            y = (1-t_norm)*(1-t_norm)*p0[1] + 2*(1-t_norm)*t_norm*control[1] + t_norm*t_norm*p1[1]
            points.append((int(x), int(y)))
        
        # Draw the curve
        if len(points) > 1:
            color_with_alpha = (*color, alpha) if alpha < 255 else color
            for i in range(len(points) - 1):
                pygame.draw.line(surface, color_with_alpha, points[i], points[i+1], int(thickness))

    def _draw_ripple(self, surface, p0, p1, color, time, activation):
        """Draw a moving ripple dot on a connection"""
        # Calculate control point (same as bezier curve)
        mid_x = (p0[0] + p1[0]) / 2
        mid_y = (p0[1] + p1[1]) / 2
        
        dx = p1[0] - p0[0]
        dy = p1[1] - p0[1]
        length = math.sqrt(dx*dx + dy*dy)
        if length > 0:
            perp_x = -dy / length * 25
            perp_y = dx / length * 25
        else:
            perp_x, perp_y = 0, 25
            
        control = (mid_x + perp_x, mid_y + perp_y)
        
        # Calculate ripple position
        t = (time * 1.5 * self.anim_intensity) % 1.0
        x = (1-t)*(1-t)*p0[0] + 2*(1-t)*t*control[0] + t*t*p1[0]
        y = (1-t)*(1-t)*p0[1] + 2*(1-t)*t*control[1] + t*t*p1[1]
        
        # Draw ripple dot
        pygame.draw.circle(surface, color, (int(x), int(y)), 3)

    def _draw_nodes(self, surface, fish, time, node_positions):
        # Input nodes
        input_labels = [
            "Food L", "Food C", "Food R",
            "Threat L", "Threat C", "Threat R", 
            "Mate L", "Mate C", "Mate R",
            "Energy", "Stamina", "Depth", "Speed", "Safety"
        ]
        
        for i, (pos, label) in enumerate(zip(node_positions["inputs"], input_labels)):
            activation = fish.last_inputs[i] if i < len(fish.last_inputs) else 0
            self._draw_single_node(surface, pos, activation, time, 6, i)
            
            # Draw label
            label_surf = self.font_tiny.render(label, True, (180, 180, 180))
            surface.blit(label_surf, (pos[0] - 45, pos[1] - 7))
            
            # Draw group dividers
            if i in [2, 5, 8]:  # After Food, Threat, Mate groups
                divider_y = pos[1] + 14
                pygame.draw.line(surface, (60, 60, 60), (pos[0] - 50, divider_y), (pos[0] + 30, divider_y))
        
        # Hidden layer 1 nodes
        hidden1_acts = getattr(fish, 'last_hidden1', fish.last_hidden[:8])
        for i, pos in enumerate(node_positions["hidden1"]):
            activation = hidden1_acts[i] if i < len(hidden1_acts) else 0
            self._draw_single_node(surface, pos, activation, time, 7, i)
        
        # Hidden layer 2 nodes
        for i, pos in enumerate(node_positions["hidden2"]):
            activation = fish.last_hidden[i] if i < len(fish.last_hidden) else 0
            self._draw_single_node(surface, pos, activation, time, 7, i)
        
        # Output nodes
        output_labels = ["Steer", "Thrust"]
        for i, (pos, label) in enumerate(zip(node_positions["outputs"], output_labels)):
            activation = fish.last_outputs[i] if i < len(fish.last_outputs) else 0
            self._draw_single_node(surface, pos, activation, time, 9, i)
            
            # Draw label
            label_surf = self.font_tiny.render(label, True, (180, 180, 180))
            surface.blit(label_surf, (pos[0] + 15, pos[1] - 7))

    def _draw_single_node(self, surface, pos, activation, time, radius, node_index):
        """Draw a single neural network node with glow effect"""
        color = self._get_activation_color(activation)
        
        # Animated glow
        freq = 2.0 + abs(activation) * 4.0
        phase_offset = node_index * 0.7
        glow_radius = radius + math.sin(time * freq * self.anim_intensity + phase_offset) * 2
        
        # Draw glow ring
        glow_surf = pygame.Surface((int(glow_radius * 4), int(glow_radius * 4)), pygame.SRCALPHA)
        pygame.draw.circle(glow_surf, (*color, 30), (int(glow_radius * 2), int(glow_radius * 2)), int(glow_radius + 4))
        surface.blit(glow_surf, (pos[0] - glow_radius * 2, pos[1] - glow_radius * 2))
        
        # Draw filled node
        pygame.draw.circle(surface, color, pos, radius)
        
        # Draw border
        pygame.draw.circle(surface, (255, 255, 255), pos, radius, 1)

    def _draw_output_footer(self, surface, fish, time, y_cursor):
        # Section title
        title = self.font_small.render("— OUTPUT INTERPRETATION —", True, (150, 150, 150))
        surface.blit(title, (20, y_cursor))
        y_cursor += 25
        
        # Steer gauge
        steer_label = self.font_small.render("STEER", True, (200, 200, 200))
        surface.blit(steer_label, (20, y_cursor))
        
        gauge_x = 80
        gauge_width = 200
        gauge_height = 20
        gauge_y = y_cursor
        
        # Draw track
        pygame.draw.rect(surface, (40, 40, 40), (gauge_x, gauge_y, gauge_width, gauge_height))
        
        # Draw center line
        center_x = gauge_x + gauge_width // 2
        pygame.draw.line(surface, (80, 80, 80), (center_x, gauge_y), (center_x, gauge_y + gauge_height))
        
        # Draw needle
        if len(fish.last_outputs) > 0:
            steer_value = fish.last_outputs[0]
            needle_x = center_x + int(steer_value * gauge_width / 2)
            pygame.draw.rect(surface, (0, 255, 220), (needle_x - 1, gauge_y - 2, 3, gauge_height + 4))
            
            # End labels
            left_label = self.font_tiny.render("← LEFT", True, (150, 150, 150))
            right_label = self.font_tiny.render("RIGHT →", True, (150, 150, 150))
            surface.blit(left_label, (gauge_x - 5, gauge_y + gauge_height + 2))
            surface.blit(right_label, (gauge_x + gauge_width - 35, gauge_y + gauge_height + 2))
            
            # Value text
            value_text = self.font_tiny.render(f"{steer_value:.2f}", True, (180, 180, 180))
            surface.blit(value_text, (center_x - 15, gauge_y - 18))
        
        y_cursor += 50
        
        # Thrust gauge
        thrust_label = self.font_small.render("THRUST", True, (200, 200, 200))
        surface.blit(thrust_label, (20, y_cursor))
        
        if len(fish.last_outputs) > 1:
            thrust_value = (fish.last_outputs[1] + 1.0) / 2.0  # Convert from [-1,1] to [0,1]
            
            # Draw track
            pygame.draw.rect(surface, (40, 40, 40), (gauge_x, gauge_y, gauge_width, gauge_height))
            
            # Draw fill
            fill_width = int(gauge_width * thrust_value)
            if thrust_value < 0.5:
                color = (255, int(255 * thrust_value * 2), 50)
            else:
                color = (int(255 * (1 - (thrust_value - 0.5) * 2)), 255, 50)
            pygame.draw.rect(surface, color, (gauge_x, gauge_y, fill_width, gauge_height))
            
            # Percentage text
            pct_text = self.font_tiny.render(f"{int(thrust_value * 100)}%", True, (180, 180, 180))
            surface.blit(pct_text, (center_x - 15, gauge_y - 18))
        
        y_cursor += 50
        
        # Sparklines
        if len(fish.output_history) > 1:
            sparkline_height = 40
            sparkline_y = y_cursor
            
            # Steer sparkline
            steer_label = self.font_tiny.render("STEER", True, (150, 150, 150))
            surface.blit(steer_label, (20, sparkline_y + 5))
            
            steer_sparkline_x = 80
            steer_sparkline_width = 200
            pygame.draw.rect(surface, (30, 30, 30), (steer_sparkline_x, sparkline_y, steer_sparkline_width, sparkline_height))
            
            # Draw zero line
            zero_y = sparkline_y + sparkline_height // 2
            pygame.draw.line(surface, (60, 60, 60), (steer_sparkline_x, zero_y), (steer_sparkline_x + steer_sparkline_width, zero_y))
            
            # Draw sparkline
            points = []
            for i, output_pair in enumerate(fish.output_history):
                if len(output_pair) > 0:
                    x = steer_sparkline_x + int(i * steer_sparkline_width / len(fish.output_history))
                    y = zero_y - int(output_pair[0] * sparkline_height / 2)
                    points.append((x, y))
            
            if len(points) > 1:
                pygame.draw.lines(surface, (0, 255, 220), False, points, 1)
            
            y_cursor += sparkline_height + 10
            
            # Thrust sparkline
            thrust_label = self.font_tiny.render("THRUST", True, (150, 150, 150))
            surface.blit(thrust_label, (20, y_cursor + 5))
            
            thrust_sparkline_y = y_cursor
            pygame.draw.rect(surface, (30, 30, 30), (steer_sparkline_x, thrust_sparkline_y, steer_sparkline_width, sparkline_height))
            
            # Draw zero line
            zero_y = thrust_sparkline_y + sparkline_height // 2
            pygame.draw.line(surface, (60, 60, 60), (steer_sparkline_x, zero_y), (steer_sparkline_x + steer_sparkline_width, zero_y))
            
            # Draw sparkline
            points = []
            for i, output_pair in enumerate(fish.output_history):
                if len(output_pair) > 1:
                    x = steer_sparkline_x + int(i * steer_sparkline_width / len(fish.output_history))
                    y = zero_y - int((output_pair[1] + 1.0) / 2.0 * sparkline_height - sparkline_height / 2)
                    points.append((x, y))
            
            if len(points) > 1:
                pygame.draw.lines(surface, (255, 170, 0), False, points, 1)
            
            y_cursor += sparkline_height + 20
        
        # Separator line
        pygame.draw.line(surface, (80, 80, 80), (20, y_cursor), (self.panel_width - 20, y_cursor))
        y_cursor += 15
        
        return y_cursor

    def _draw_traits(self, surface, fish, y_cursor):
        # Section title
        title = self.font_small.render("— HERITABLE TRAITS —", True, (150, 150, 150))
        surface.blit(title, (20, y_cursor))
        y_cursor += 30
        
        traits = fish.traits.physical_traits
        trait_data = [
            ("SPEED", traits.get("max_speed_mult", 1.0)),
            ("STAMINA", traits.get("stamina_mult", 1.0)),
            ("AGILITY", traits.get("turn_rate_mult", 1.0)),
            ("METABOLISM", traits.get("metabolism_mult", 1.0)),
            ("SIZE", traits.get("size_mult", 1.0)),
            ("LIFESPAN", traits.get("lifespan_mult", 1.0)),
        ]
        
        label_width = 68
        track_width = 240
        track_height = 6
        track_x = 20 + label_width
        
        for label, value in trait_data:
            # Label
            label_surf = self.font_small.render(label, True, (200, 200, 200))
            surface.blit(label_surf, (20, y_cursor))
            
            # Track background
            track_y = y_cursor + 8
            pygame.draw.rect(surface, (40, 40, 40), (track_x, track_y, track_width, track_height))
            
            # Center line
            center_x = track_x + track_width // 2
            pygame.draw.line(surface, (60, 60, 60), (center_x, track_y), (center_x, track_y + track_height))
            
            # Fill
            if value != 1.0:
                normalized_offset = (value - 1.0) / 0.8  # Normalize to [-1, 1] range
                fill_width = min(track_width // 2, int(abs(normalized_offset) * track_width / 2))
                
                if value > 1.0:
                    fill_color = (100, 255, 100)
                    fill_x = center_x
                else:
                    fill_color = (255, 170, 0)
                    fill_x = center_x - fill_width
                
                pygame.draw.rect(surface, fill_color, (fill_x, track_y, fill_width, track_height))
            
            # Value text
            value_text = self.font_tiny.render(f"{value:.2f}", True, (180, 180, 180))
            surface.blit(value_text, (track_x + track_width + 8, y_cursor + 3))
            
            y_cursor += 25
        
        # Separator line
        pygame.draw.line(surface, (80, 80, 80), (20, y_cursor), (self.panel_width - 20, y_cursor))
        y_cursor += 15
        
        return y_cursor

    def _draw_lifetime_stats(self, surface, fish, y_cursor):
        # Section title
        title = self.font_small.render("— LIFETIME STATS —", True, (150, 150, 150))
        surface.blit(title, (20, y_cursor))
        y_cursor += 30
        
        # Three stat boxes
        box_width = 110
        box_height = 60
        box_spacing = 15
        start_x = 20
        
        stats = [
            ("FOOD EATEN", str(fish.food_eaten)),
            ("DIST TRAVELED", str(int(fish.distance_traveled))),
            ("OFFSPRING", str(fish.offspring_count)),
        ]
        
        for i, (label, value) in enumerate(stats):
            x = start_x + i * (box_width + box_spacing)
            
            # Box background
            pygame.draw.rect(surface, (20, 30, 40), (x, y_cursor, box_width, box_height))
            pygame.draw.rect(surface, (100, 150, 200), (x, y_cursor, box_width, box_height), 2)
            
            # Value
            value_surf = self.font_normal.render(value, True, (0, 255, 220))
            value_rect = value_surf.get_rect(center=(x + box_width // 2, y_cursor + 25))
            surface.blit(value_surf, value_rect)
            
            # Label
            label_surf = self.font_tiny.render(label, True, (150, 150, 150))
            label_rect = label_surf.get_rect(center=(x + box_width // 2, y_cursor + 45))
            surface.blit(label_surf, label_rect)
        
        return y_cursor
