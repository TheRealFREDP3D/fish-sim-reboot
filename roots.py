"""Root network system - directed graphs for nutrient transport"""

import pygame
import random
import math
from config import (
    ROOT_BASE_THICKNESS,
    ROOT_BASE_GROWTH_RATE,
    ROOT_MAX_NODES,
    ROOT_MAX_DEPTH,
    ROOT_BRANCH_CHANCE,
    ROOT_UPTAKE_CAPACITY,
    ROOT_TRANSPORT_LOSS,
    ROOT_BASE_COLOR,
    ROOT_ACTIVE_COLOR,
    ROOT_TIP_COLOR,
)
from collections import deque


class RootNode:
    def __init__(self, cell_x, cell_y, parent=None):
        self.cell_x = cell_x
        self.cell_y = cell_y
        self.parent = parent
        self.children = []
        self.thickness = ROOT_BASE_THICKNESS
        self.stored_nutrient = 0.0
        self.is_tip = True
        self.age = 0
        self.flow_pulse = random.uniform(0, math.pi * 2)

    def add_child(self, child_node):
        self.children.append(child_node)
        self.is_tip = False

    def get_depth(self):
        depth = 0
        node = self
        while node.parent is not None:
            depth += 1
            node = node.parent
        return depth

    def get_pixel_position(self, cell_size):
        return (
            self.cell_x * cell_size + cell_size // 2,
            self.cell_y * cell_size + cell_size // 2,
        )


class RootSystem:
    def __init__(self, plant_base_x, plant_base_y, soil_grid):
        self.soil_grid = soil_grid
        self.cell_size = soil_grid.cell_size
        base_cell_x, base_cell_y = soil_grid.pixel_to_cell(plant_base_x, plant_base_y)
        self.root_origin = RootNode(base_cell_x, base_cell_y)
        self.all_nodes = [self.root_origin]
        self.tips = [self.root_origin]
        self._cell_lookup = {(base_cell_x, base_cell_y)}
        self.current_growth_rate = ROOT_BASE_GROWTH_RATE
        self.growth_timer = 0.0
        self.total_harvested = 0.0

    def adjust_growth_rate(self, new_rate):
        self.current_growth_rate = new_rate

    def update(self, dt, current_plant_height):
        # Increased base nodes and growth scaling to make roots more substantial
        dynamic_max = int(12 + current_plant_height * 0.4)
        self._max_nodes = min(ROOT_MAX_NODES, dynamic_max)

        self.growth_timer += dt * self.current_growth_rate
        while self.growth_timer >= 1.0:
            self.growth_timer -= 1.0
            self.grow_step()

        for node in self.all_nodes:
            node.age += 1
            if node.stored_nutrient > 0:
                node.flow_pulse = (node.flow_pulse + dt * 10) % (math.pi * 2)

        self.uptake_nutrients()
        self.transport_nutrients()

    def grow_step(self):
        if not self.tips or len(self.all_nodes) >= self._max_nodes:
            return

        tip = self._select_growth_tip()
        if tip is None or tip.get_depth() >= ROOT_MAX_DEPTH:
            if tip in self.tips:
                self.tips.remove(tip)
            return

        candidates = self._get_growth_candidates(tip)
        if not candidates:
            return

        best_cell, best_dir = self._select_best_candidate(candidates)
        if best_cell:
            new_node = RootNode(best_cell.x, best_cell.y, parent=tip)
            tip.add_child(new_node)
            self.all_nodes.append(new_node)
            self.tips.append(new_node)
            self._cell_lookup.add((best_cell.x, best_cell.y))

            if (
                best_dir[1] > 0
                and best_cell.nutrient > 0.4
                and random.random() < ROOT_BRANCH_CHANCE
            ):
                tip.is_tip = True

    def _select_growth_tip(self):
        if not self.tips:
            return None
        weights = [
            (
                sum(
                    c.nutrient
                    for c, _ in self.soil_grid.get_neighbors(t.cell_x, t.cell_y)
                )
                ** 2
            )
            + 0.1
            for t in self.tips
        ]
        return random.choices(self.tips, weights=weights, k=1)[0]

    def _get_growth_candidates(self, tip):
        candidates = []
        for dx, dy in [(0, 1), (-1, 1), (1, 1), (-1, 0), (1, 0), (0, -1), (-1, -1), (1, -1)]:
            nx, ny = tip.cell_x + dx, tip.cell_y + dy
            cell = self.soil_grid.get_cell(nx, ny)
            if (
                cell
                and not cell.is_water
                and (nx, ny) not in self._cell_lookup
                and cell.nutrient > 0.02
            ):
                candidates.append((cell, (dx, dy)))
        return candidates

    def _select_best_candidate(self, candidates):
        scored = []
        for cell, (dx, dy) in candidates:
            score = (
                cell.nutrient * 12
                + (15 if dy > 0 else 2 if dy == 0 else -10)
                + random.uniform(0, 4)
            )
            scored.append((score, cell, (dx, dy)))
        if not scored:
            return None, None
        scored.sort(key=lambda x: x[0], reverse=True)
        return scored[0][1], scored[0][2]

    def uptake_nutrients(self):
        for tip in self.tips:
            if tip.is_tip:
                cell = self.soil_grid.get_cell(tip.cell_x, tip.cell_y)
                if cell and not cell.is_water:
                    tip.stored_nutrient += cell.deplete(ROOT_UPTAKE_CAPACITY)

    def transport_nutrients(self):
        processed, to_process, visited = set(), deque(), set()
        for tip in self.tips:
            node = tip
            while node and node not in visited:
                to_process.append(node)
                visited.add(node)
                node = node.parent

        harvested = 0.0
        while to_process:
            node = to_process[-1]
            if all(child in processed for child in node.children):
                to_process.pop()
                processed.add(node)
                if node.stored_nutrient > 0:
                    if node.parent:
                        delivered = max(0, node.stored_nutrient - ROOT_TRANSPORT_LOSS)
                        node.parent.stored_nutrient += delivered
                    else:
                        harvested += node.stored_nutrient
                    node.stored_nutrient = 0.0
        self.total_harvested += harvested

    def harvest_nutrients(self):
        amt = self.total_harvested
        self.total_harvested = 0.0
        return amt

    def draw(self, screen, camera, time):
        for node in self.all_nodes:
            if node.parent:
                depth_factor = 1.0 - (node.get_depth() / (ROOT_MAX_DEPTH * 1.2))
                # Increased minimum thickness for better visibility
                thickness = max(2, int(ROOT_BASE_THICKNESS * depth_factor))

                base_color = ROOT_BASE_COLOR
                p_pos = camera.apply(node.parent.get_pixel_position(self.cell_size))
                n_pos = camera.apply(node.get_pixel_position(self.cell_size))

                if node.stored_nutrient > 0:
                    # Enhanced pulsing glow
                    pulse = (math.sin(node.flow_pulse * 2) + 1) / 2
                    active = tuple(
                        int(
                            base_color[i]
                            + (ROOT_ACTIVE_COLOR[i] - base_color[i]) * pulse
                        )
                        for i in range(3)
                    )
                    # Thicker glowing outer line
                    glow_color = tuple(min(255, int(active[i] * 1.3)) for i in range(3))
                    pygame.draw.line(screen, glow_color, p_pos, n_pos, thickness + 4)
                    color = active
                else:
                    color = base_color

                pygame.draw.line(screen, color, p_pos, n_pos, thickness)

        # Smaller, pointier root tips
        for tip in self.tips:
            if tip.is_tip:
                pos = camera.apply(tip.get_pixel_position(self.cell_size))
                tip_brightness = min(1.0, tip.stored_nutrient * 4.0)
                tip_color = tuple(
                    int(ROOT_TIP_COLOR[i] * (0.8 + 0.2 * tip_brightness))
                    for i in range(3)
                )

                # Smaller base circle
                pygame.draw.circle(screen, tip_color, pos, 3)

                # Pointy triangle indicator for active tips
                if tip.stored_nutrient > 0:
                    # Direction toward most nutrient-rich neighbor (or down if none)
                    best_dx, best_dy = 0, 1
                    best_n = 0
                    for nb, (dx, dy) in self.soil_grid.get_neighbors(
                        tip.cell_x, tip.cell_y
                    ):
                        if nb.nutrient > best_n:
                            best_n = nb.nutrient
                            best_dx, best_dy = dx, dy
                    angle = math.atan2(best_dy, best_dx)
                    tip_len = 8
                    p1 = (
                        pos[0] + math.cos(angle + 2.2) * tip_len,
                        pos[1] + math.sin(angle + 2.2) * tip_len,
                    )
                    p2 = (
                        pos[0] + math.cos(angle - 2.2) * tip_len,
                        pos[1] + math.sin(angle - 2.2) * tip_len,
                    )
                    pygame.draw.polygon(screen, tip_color, [pos, p1, p2])

                    # Glow around tip
                    glow = tuple(
                        min(255, int(c + 120 * tip_brightness)) for c in tip_color
                    )
                    pygame.draw.circle(screen, glow, pos, 5, 2)
