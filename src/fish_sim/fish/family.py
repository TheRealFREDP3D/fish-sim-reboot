"""Family system - parents stay with offspring until maturity"""


class Family:
    """A temporary family unit where parents stay near their children until they mature"""

    def __init__(self, parent1, parent2, children, fish_system):
        self.parents = [parent1, parent2]
        self.children = children[:]  # copy list
        self.fish_system = fish_system  # Reference to the FishSystem for list access
        self.active = True

    def update(self, dt):
        """Check if all children are mature - if so, dissolve family"""
        if not self.active:
            return

        # Update children list: keep only those still alive in the correct population
        new_children = []
        for child in self.children:
            if child in self.fish_system.fish or child in self.fish_system.cleaner_fish or child in self.fish_system.predators:
                new_children.append(child)
        self.children = new_children

        # Update parents list (in case a parent died)
        self.parents = [
            p
            for p in self.parents
            if p in self.fish_system.fish or p in self.fish_system.cleaner_fish or p in self.fish_system.predators
        ]

        # Dissolve if no children left or all children mature
        if len(self.children) == 0:
            self.active = False
            return

        all_mature = all(child.is_mature for child in self.children)
        if all_mature:
            self.active = False

    def get_family_members(self, exclude_self=None):
        """Return all living family members except optional excluded one"""
        # Combine all living fish into a set for efficient lookup
        living_fish = set(self.fish_system.fish) | set(self.fish_system.cleaner_fish) | set(self.fish_system.predators)

        members = self.parents + self.children
        if exclude_self:
            members = [m for m in members if m != exclude_self]

        # Filter using the efficient set lookup
        return [m for m in members if m in living_fish]
