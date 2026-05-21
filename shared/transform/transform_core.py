"""
Shared Coordinate Transformation Core (Python)

This module provides the core coordinate transformation logic used by both
CadOwl (CAD -> SiteOwl) and VIVE XR (VR -> SiteOwl).

No external dependencies - pure Python math only.

Usage:
    from shared.transform.transform_core import CoordinateTransformer, ScaleMode, Bounds
    
    bounds = Bounds(min_x=0, min_y=0, max_x=1000, max_y=500)
    transformer = CoordinateTransformer(mode=ScaleMode.FIT_CONTAIN)
    transformer.set_bounds(bounds)
    
    result = transformer.transform(500, 250)
    print(f"SiteOwl: ({result.site_x}, {result.site_y})")
"""

from dataclasses import dataclass
from enum import Enum, auto
from typing import List, Tuple, Optional
import math


class ScaleMode(Enum):
    """How to scale the content within the artboard."""
    FIT_WIDTH = auto()    # Scale to match width, center vertically
    FIT_HEIGHT = auto()   # Scale to match height, center horizontally
    FIT_CONTAIN = auto()  # Fit within bounds without cropping (DEFAULT)
    FIT_COVER = auto()    # Fill bounds, may crop edges
    STRETCH = auto()      # Stretch to fill (distorts aspect ratio)


@dataclass
class Bounds:
    """Axis-aligned bounding box."""
    min_x: float
    min_y: float
    max_x: float
    max_y: float
    
    @property
    def width(self) -> float:
        return self.max_x - self.min_x
    
    @property
    def height(self) -> float:
        return self.max_y - self.min_y
    
    @property
    def center(self) -> Tuple[float, float]:
        return (
            (self.min_x + self.max_x) / 2,
            (self.min_y + self.max_y) / 2
        )
    
    @property
    def aspect_ratio(self) -> float:
        """Width / Height ratio."""
        return self.width / self.height if self.height != 0 else 1.0
    
    @classmethod
    def from_points(cls, points: List[Tuple[float, float]]) -> Optional["Bounds"]:
        """Create bounding box from list of (x, y) points."""
        if not points:
            return None
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        return cls(min_x=min(xs), min_y=min(ys), max_x=max(xs), max_y=max(ys))
    
    @classmethod
    def from_dict(cls, d: dict) -> "Bounds":
        """Create from dictionary."""
        return cls(
            min_x=d["min_x"],
            min_y=d["min_y"],
            max_x=d["max_x"],
            max_y=d["max_y"]
        )
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "min_x": self.min_x,
            "min_y": self.min_y,
            "max_x": self.max_x,
            "max_y": self.max_y
        }


@dataclass
class TransformResult:
    """Result of coordinate transformation."""
    art_x: float       # Artboard X (0-1000)
    art_y: float       # Artboard Y (0-1000)
    site_x: float      # SiteOwl X (0-100)
    site_y: float      # SiteOwl Y (0-100)
    in_bounds: bool    # Whether point is within artboard
    confidence: float  # Confidence in transformation (0-1)
    
    def to_dict(self) -> dict:
        return {
            "art_x": self.art_x,
            "art_y": self.art_y,
            "site_x": self.site_x,
            "site_y": self.site_y,
            "in_bounds": self.in_bounds,
            "confidence": self.confidence
        }


class CoordinateTransformer:
    """
    Transform coordinates from source system to SiteOwl.
    
    The transformation pipeline:
    1. Source coords -> Normalize to bounding box origin
    2. Normalized -> Scale to artboard (0-1000)
    3. Artboard -> Flip Y axis (optional, for CAD Y-up -> web Y-down)
    4. Artboard -> Divide by 10 for SiteOwl (0-100)
    """
    
    DEFAULT_ARTBOARD_SIZE = 1000
    DEFAULT_FLOORPLAN_SIZE = 800
    
    def __init__(
        self,
        mode: ScaleMode = ScaleMode.FIT_CONTAIN,
        artboard_size: int = DEFAULT_ARTBOARD_SIZE,
        floorplan_size: int = DEFAULT_FLOORPLAN_SIZE,
        flip_y: bool = True,
        rotation_deg: float = 0.0
    ):
        self.mode = mode
        self.artboard_size = artboard_size
        self.floorplan_size = floorplan_size
        self.flip_y = flip_y
        self.rotation_rad = math.radians(rotation_deg)
        
        # Calculated after bounds are set
        self._bounds: Optional[Bounds] = None
        self._scale_x: float = 1.0
        self._scale_y: float = 1.0
        self._offset_x: float = 0.0
        self._offset_y: float = 0.0
    
    @property
    def margin(self) -> float:
        """Margin between artboard edge and floorplan."""
        return (self.artboard_size - self.floorplan_size) / 2
    
    @property
    def is_ready(self) -> bool:
        """Check if transformer is ready (bounds set)."""
        return self._bounds is not None
    
    def set_bounds(self, bounds: Bounds) -> None:
        """
        Set the source coordinate bounds and calculate transformation.
        
        Args:
            bounds: Bounding box of source coordinates
        """
        self._bounds = bounds
        
        if bounds.width <= 0 or bounds.height <= 0:
            self._scale_x = 1.0
            self._scale_y = 1.0
            self._offset_x = self.margin
            self._offset_y = self.margin
            return
        
        # Calculate scale factors based on mode
        if self.mode == ScaleMode.STRETCH:
            self._scale_x = self.floorplan_size / bounds.width
            self._scale_y = self.floorplan_size / bounds.height
        elif self.mode == ScaleMode.FIT_WIDTH:
            scale = self.floorplan_size / bounds.width
            self._scale_x = scale
            self._scale_y = scale
        elif self.mode == ScaleMode.FIT_HEIGHT:
            scale = self.floorplan_size / bounds.height
            self._scale_x = scale
            self._scale_y = scale
        elif self.mode == ScaleMode.FIT_CONTAIN:
            scale = min(
                self.floorplan_size / bounds.width,
                self.floorplan_size / bounds.height
            )
            self._scale_x = scale
            self._scale_y = scale
        elif self.mode == ScaleMode.FIT_COVER:
            scale = max(
                self.floorplan_size / bounds.width,
                self.floorplan_size / bounds.height
            )
            self._scale_x = scale
            self._scale_y = scale
        
        # Calculate offsets to center the content
        scaled_width = bounds.width * self._scale_x
        scaled_height = bounds.height * self._scale_y
        self._offset_x = (self.artboard_size - scaled_width) / 2
        self._offset_y = (self.artboard_size - scaled_height) / 2
    
    def transform(self, x: float, y: float) -> TransformResult:
        """
        Transform a single coordinate pair.
        
        Args:
            x: Source X coordinate
            y: Source Y coordinate
            
        Returns:
            TransformResult with artboard and SiteOwl coordinates
        """
        if self._bounds is None:
            raise ValueError("Bounds not set. Call set_bounds() first.")
        
        # Apply rotation if needed
        if self.rotation_rad != 0:
            cx, cy = self._bounds.center
            dx, dy = x - cx, y - cy
            cos_r, sin_r = math.cos(self.rotation_rad), math.sin(self.rotation_rad)
            x = cx + dx * cos_r - dy * sin_r
            y = cy + dx * sin_r + dy * cos_r
        
        # Normalize to bounds origin
        norm_x = x - self._bounds.min_x
        norm_y = y - self._bounds.min_y
        
        # Scale to artboard
        art_x = self._offset_x + norm_x * self._scale_x
        
        # Y-axis handling
        if self.flip_y:
            norm_y_flipped = self._bounds.height - norm_y
            art_y = self._offset_y + norm_y_flipped * self._scale_y
        else:
            art_y = self._offset_y + norm_y * self._scale_y
        
        # Convert to SiteOwl (0-100)
        site_x = round(art_x / 10.0, 2)
        site_y = round(art_y / 10.0, 2)
        
        # Check bounds
        in_bounds = (
            0 <= art_x <= self.artboard_size and
            0 <= art_y <= self.artboard_size
        )
        
        # Calculate confidence
        confidence = 1.0
        if not in_bounds:
            dist = math.sqrt(
                (art_x - self.artboard_size/2)**2 +
                (art_y - self.artboard_size/2)**2
            )
            max_dist = self.artboard_size * math.sqrt(2) / 2
            confidence = max(0.0, 1.0 - (dist / max_dist - 0.7) * 2)
        
        return TransformResult(
            art_x=art_x,
            art_y=art_y,
            site_x=site_x,
            site_y=site_y,
            in_bounds=in_bounds,
            confidence=confidence
        )
    
    def transform_batch(self, points: List[Tuple[float, float]]) -> List[TransformResult]:
        """Transform multiple points at once."""
        return [self.transform(x, y) for x, y in points]
    
    def inverse_transform(self, site_x: float, site_y: float) -> Tuple[float, float]:
        """Convert SiteOwl coordinates back to source coordinates."""
        if self._bounds is None:
            raise ValueError("Bounds not set.")
        
        art_x = site_x * 10.0
        art_y = site_y * 10.0
        
        norm_x = (art_x - self._offset_x) / self._scale_x
        
        if self.flip_y:
            norm_y_flipped = (art_y - self._offset_y) / self._scale_y
            norm_y = self._bounds.height - norm_y_flipped
        else:
            norm_y = (art_y - self._offset_y) / self._scale_y
        
        source_x = norm_x + self._bounds.min_x
        source_y = norm_y + self._bounds.min_y
        
        return (source_x, source_y)
    
    def get_transform_matrix(self) -> List[List[float]]:
        """
        Get the 3x3 affine transformation matrix.
        
        Returns:
            3x3 matrix: [[a, b, tx], [c, d, ty], [0, 0, 1]]
        """
        if self._bounds is None:
            return [[1, 0, 0], [0, 1, 0], [0, 0, 1]]
        
        tx1 = -self._bounds.min_x
        ty1 = -self._bounds.min_y
        
        sx = self._scale_x
        sy = self._scale_y if not self.flip_y else -self._scale_y
        
        tx2 = self._offset_x
        ty2 = self._offset_y if not self.flip_y else (
            self._offset_y + self._bounds.height * self._scale_y
        )
        
        return [
            [sx, 0, sx * tx1 + tx2],
            [0, sy, sy * ty1 + ty2],
            [0, 0, 1]
        ]
    
    def to_config_dict(self) -> dict:
        """Export configuration as dictionary (for JSON serialization)."""
        return {
            "mode": self.mode.name,
            "artboard_size": self.artboard_size,
            "floorplan_size": self.floorplan_size,
            "flip_y": self.flip_y,
            "rotation_deg": math.degrees(self.rotation_rad),
            "bounds": self._bounds.to_dict() if self._bounds else None,
            "matrix": self.get_transform_matrix()
        }
    
    @classmethod
    def from_config_dict(cls, config: dict) -> "CoordinateTransformer":
        """Create transformer from configuration dictionary."""
        transformer = cls(
            mode=ScaleMode[config.get("mode", "FIT_CONTAIN")],
            artboard_size=config.get("artboard_size", cls.DEFAULT_ARTBOARD_SIZE),
            floorplan_size=config.get("floorplan_size", cls.DEFAULT_FLOORPLAN_SIZE),
            flip_y=config.get("flip_y", True),
            rotation_deg=config.get("rotation_deg", 0.0)
        )
        if config.get("bounds"):
            transformer.set_bounds(Bounds.from_dict(config["bounds"]))
        return transformer


# Convenience function
def transform_points(
    points: List[Tuple[float, float]],
    mode: ScaleMode = ScaleMode.FIT_CONTAIN
) -> List[Tuple[float, float]]:
    """
    Quick transform of points to SiteOwl coordinates.
    
    Args:
        points: List of (x, y) source coordinates
        mode: Scale mode
        
    Returns:
        List of (site_x, site_y) coordinates
    """
    if not points:
        return []
    
    bounds = Bounds.from_points(points)
    if bounds is None:
        return [(0, 0)] * len(points)
    
    transformer = CoordinateTransformer(mode=mode)
    transformer.set_bounds(bounds)
    
    results = transformer.transform_batch(points)
    return [(r.site_x, r.site_y) for r in results]


# For testing
if __name__ == "__main__":
    # Test basic transform
    bounds = Bounds(min_x=0, min_y=0, max_x=1000, max_y=500)
    transformer = CoordinateTransformer(mode=ScaleMode.FIT_CONTAIN)
    transformer.set_bounds(bounds)
    
    test_points = [(0, 0), (1000, 0), (1000, 500), (0, 500), (500, 250)]
    
    print("Transform Test:")
    for x, y in test_points:
        result = transformer.transform(x, y)
        print(f"  ({x}, {y}) -> ({result.site_x}, {result.site_y})")
    
    # Test matrix export
    print(f"\nTransform Matrix:")
    for row in transformer.get_transform_matrix():
        print(f"  {row}")
