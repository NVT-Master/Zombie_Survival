"""
Spatial partitioning for efficient collision detection (O(n) -> O(1) average case).
Divides game world into grid cells for faster zombie-bullet collision checks.
"""

from typing import Dict, List, Tuple
from assets.core.Config import GAME_WIDTH, GAME_HEIGHT
from assets.utils.Vectors import Vector2


class SpatialGrid:
    """
    Divides the game world into cells for spatial partitioning.
    Objects are stored in cells based on their position for faster queries.
    """
    
    # Cell size in pixels - adjust based on object sizes
    CELL_SIZE: int = 120
    
    def __init__(self):
        self.cols = (GAME_WIDTH // self.CELL_SIZE) + 2
        self.rows = (GAME_HEIGHT // self.CELL_SIZE) + 2
        self.grid: Dict[Tuple[int, int], List] = {}
        self._query_cache: Dict[Tuple[int, int], List[Tuple[int, int]]] = {}
    
    def clear(self):
        """Clear all cells"""
        self.grid.clear()
    
    def _get_cell_key(self, position: Vector2) -> Tuple[int, int]:
        """Get the grid cell coordinates for a position"""
        col = int(position.x // self.CELL_SIZE)
        row = int(position.y // self.CELL_SIZE)
        # Clamp to valid range
        col = max(0, min(col, self.cols - 1))
        row = max(0, min(row, self.rows - 1))
        return (col, row)
    
    def insert(self, obj, position: Vector2):
        """Insert object into grid at position"""
        cell_key = self._get_cell_key(position)
        if cell_key not in self.grid:
            self.grid[cell_key] = []
        self.grid[cell_key].append(obj)
    
    def get_nearby_cells(self, position: Vector2, radius: float = 0) -> List[Tuple[int, int]]:
        """Get all cells within radius of a position"""
        # Use rectangular query for efficiency (covers radius)
        col, row = self._get_cell_key(position)
        cell_radius = int((radius / self.CELL_SIZE) + 1)
        
        nearby = []
        for dc in range(-cell_radius, cell_radius + 1):
            for dr in range(-cell_radius, cell_radius + 1):
                c, r = col + dc, row + dr
                if 0 <= c < self.cols and 0 <= r < self.rows:
                    nearby.append((c, r))
        return nearby
    
    def query_radius(self, position: Vector2, radius: float) -> List:
        """Query all objects within radius of position"""
        nearby_cells = self.get_nearby_cells(position, radius)
        sqr_radius = radius ** 2
        results = []
        
        for cell_key in nearby_cells:
            if cell_key in self.grid:
                for obj in self.grid[cell_key]:
                    dist_sqr = (obj.position - position).sqrMagnitude
                    if dist_sqr <= sqr_radius:
                        results.append(obj)
        
        return results
    
    def query_cell(self, cell_key: Tuple[int, int]) -> List:
        """Get all objects in a specific cell"""
        return self.grid.get(cell_key, [])


class FastCollisionDetector:
    """
    Fast collision detection using spatial partitioning.
    Significantly faster than O(n) linear search for large zombie counts.
    """
    
    def __init__(self):
        self.grid = SpatialGrid()
    
    def clear(self):
        """Clear all data"""
        self.grid.clear()
    
    def build_from_zombies(self, zombies):
        """Build spatial grid from zombie positions"""
        self.clear()
        for zombie in zombies:
            if not zombie.hidden:
                self.grid.insert(zombie, zombie.position)
    
    def find_colliding_zombies(self, bullet_pos: Vector2, bullet_radius: float) -> List:
        """
        Find all zombies that could collide with bullet at given position.
        Much faster than linear search when there are many zombies.
        """
        return self.grid.query_radius(bullet_pos, bullet_radius)

