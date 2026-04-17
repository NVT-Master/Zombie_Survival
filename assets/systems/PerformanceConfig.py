"""
Performance Settings Module
Configure performance optimizations and tuning parameters here.
"""

# ============ COLLISION DETECTION ============
ENABLE_SPATIAL_PARTITIONING = True  # Use fast collision detection with spatial grid
SPATIAL_CELL_SIZE = 120  # Size of grid cells in pixels (larger = fewer, denser cells)

# ============ CANVAS RENDERING ============
HEALTH_BAR_UPDATE_THRESHOLD = 1  # Only update when health changes by this amount
SHIELD_POSITION_UPDATE_THRESHOLD = 2.0  # pixels (TankZombie visual)
BOMB_POSITION_UPDATE_THRESHOLD = 2.0  # pixels (BomberZombie visual)
EXPLOSION_VISUAL_DURATION_MS = 120  # How long explosion effect stays visible

# ============ ANIMATION ============
ENABLE_DIRECTIONAL_ANIMATION_CACHE = True  # Cache rotated frames for smooth animation
ANIMATION_FRAME_SKIP_HIGH_LOAD = False  # Skip animation frames if FPS drops

# ============ SPAWNING ============
ZOMBIE_SPAWN_BURST_LIMIT = 1  # Max zombies to spawn per frame on easy mode
HIGH_LOAD_SPAWN_LIMIT = 1  # Max spawns when frame time > 30ms
MEDIUM_LOAD_SPAWN_LIMIT = 2  # Max spawns when frame time > 22ms

# ============ PHYSICS ============
BARRICADE_COLLISION_CHECK_DISTANCE = 45  # Distance threshold for barricade collision

# ============ DEBUG ============
ENABLE_PERFORMANCE_LOGGING = False  # Log performance metrics every N frames
PERFORMANCE_LOG_INTERVAL = 60  # Frames between logs (60 = 1 second at 60fps)
SHOW_COLLISION_DEBUG = False  # Visualize collision detection grid

# ============ LOW-END DEVICE FALLBACK ============
ENABLE_AUTO_QUALITY = True  # Automatically reduce quality on slow devices
LOW_END_DEVICE_FPS_THRESHOLD = 45  # FPS below this triggers quality reduction
QUALITY_REDUCTION_MODES = {
    "high": {"max_zombies": 10, "animation_quality": 1.0, "canvas_effects": True},
    "medium": {"max_zombies": 7, "animation_quality": 0.8, "canvas_effects": True},
    "low": {"max_zombies": 5, "animation_quality": 0.6, "canvas_effects": False},
}
