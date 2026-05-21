"""
Coordinate transformation engine for CadOwl.

Handles all coordinate transformations between:
- CAD coordinates (arbitrary units, Y-up)
- Artboard coordinates (0-1000, Y-down)
- SiteOwl coordinates (0-100, Y-down)
"""

from dataclasses import dataclass
from enum import Enum, auto
from typing import List, Optional, Tuple
import math


class ScaleMode(Enum):
    """How to scale the floorplan within the artboard."""
    
    FIT_WIDTH = auto()    # Scale to width, center vertically
    FIT_HEIGHT = auto()   # Scale to height, center horizontally  
    FIT_CONTAIN = auto()  # Fit within bounds (no cropping)
    FIT_COVER = auto()    # Fill bounds (may crop edges)
    STRETCH = auto()      # Stretch to fill (distorts aspect ratio)


@dataclass
class BoundingBox:
    """Axis-aligned bounding box for coordinate calculations."""
    
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
        if self.height == 0:
            return 1.0
        return self.width / self.height
    
    def expand(self, margin: float) -> "BoundingBox":
        """Return new bbox expanded by margin on all sides."""
        return BoundingBox(
            min_x=self.min_x - margin,
            min_y=self.min_y - margin,
            max_x=self.max_x + margin,
            max_y=self.max_y + margin
        )
    
    def pad_to_aspect_ratio(self, target_ratio: float) -> "BoundingBox":
        """Pad bbox to match target aspect ratio (width/height)."""
        current_ratio = self.aspect_ratio
        
        if abs(current_ratio - target_ratio) < 0.001:
            return self  # Already matches
        
        cx, cy = self.center
        
        if current_ratio < target_ratio:
            # Too tall, widen it
            new_width = self.height * target_ratio
            return BoundingBox(
                min_x=cx - new_width / 2,
                min_y=self.min_y,
                max_x=cx + new_width / 2,
                max_y=self.max_y
            )
        else:
            # Too wide, heighten it
            new_height = self.width / target_ratio
            return BoundingBox(
                min_x=self.min_x,
                min_y=cy - new_height / 2,
                max_x=self.max_x,
                max_y=cy + new_height / 2
            )
    
    @classmethod
    def from_points(cls, points: List[Tuple[float, float]]) -> Optional["BoundingBox"]:
        """Create bounding box from list of (x, y) points."""
        if not points:
            return None
        
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        
        return cls(
            min_x=min(xs),
            min_y=min(ys),
            max_x=max(xs),
            max_y=max(ys)
        )


@dataclass
class TransformResult:
    """Result of coordinate transformation with metadata."""
    
    art_x: float      # Artboard X (0-1000)
    art_y: float      # Artboard Y (0-1000)
    site_x: float     # SiteOwl X (0-100)
    site_y: float     # SiteOwl Y (0-100)
    in_bounds: bool   # Whether point is within artboard
    confidence: float # Confidence in transformation (0-1)


class CoordinateMapper:
    """
    Transform CAD coordinates to SiteOwl coordinates.
    
    The transformation pipeline:
    1. CAD coords → Normalize to bounding box
    2. Normalized → Scale to artboard (0-1000)
    3. Artboard → Flip Y axis (CAD Y-up → SiteOwl Y-down)
    4. Artboard → Divide by 10 for SiteOwl (0-100)
    
    Example:
        mapper = CoordinateMapper(mode=ScaleMode.FIT_CONTAIN)
        mapper.set_bounds(device_bbox)
        
        for device in devices:
            result = mapper.transform(device.cad_x, device.cad_y)
            device.site_x = result.site_x
            device.site_y = result.site_y
    """
    
    DEFAULT_ARTBOARD_SIZE = 1000
    DEFAULT_FLOORPLAN_SIZE = 800
    DEFAULT_MARGIN = 100  # (1000 - 800) / 2
    
    def __init__(
        self,
        mode: ScaleMode = ScaleMode.FIT_CONTAIN,
        artboard_size: int = DEFAULT_ARTBOARD_SIZE,
        floorplan_size: int = DEFAULT_FLOORPLAN_SIZE,
        flip_y: bool = True,
        rotation_deg: float = 0.0
    ):
        """
        Initialize the coordinate mapper.
        
        Args:
            mode: How to scale the floorplan within artboard
            artboard_size: Size of square artboard (default 1000)
            floorplan_size: Size of usable area (default 800)
            flip_y: Flip Y axis (CAD Y-up → SiteOwl Y-down)
            rotation_deg: Rotate floorplan by degrees (clockwise)
        """
        self.mode = mode
        self.artboard_size = artboard_size
        self.floorplan_size = floorplan_size
        self.flip_y = flip_y
        self.rotation_rad = math.radians(rotation_deg)
        
        # Calculated after bounds are set
        self._bounds: Optional[BoundingBox] = None
        self._scale_x: float = 1.0
        self._scale_y: float = 1.0
        self._offset_x: float = 0.0
        self._offset_y: float = 0.0
        
    @property
    def margin(self) -> float:
        """Margin between artboard edge and floorplan."""
        return (self.artboard_size - self.floorplan_size) / 2
    
    def set_bounds(
        self, 
        bounds: BoundingBox,
        preserve_aspect: bool = True
    ) -> None:
        """
        Set the CAD coordinate bounds and calculate transformation.
        
        Args:
            bounds: Bounding box of CAD coordinates
            preserve_aspect: If True, maintain aspect ratio
        """
        self._bounds = bounds
        
        if bounds.width <= 0 or bounds.height <= 0:
            # Degenerate bounds, use identity transform
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
            # Fit entirely within bounds (no cropping)
            scale = min(
                self.floorplan_size / bounds.width,
                self.floorplan_size / bounds.height
            )
            self._scale_x = scale
            self._scale_y = scale
            
        elif self.mode == ScaleMode.FIT_COVER:
            # Cover entire bounds (may crop)
            scale = max(
                self.floorplan_size / bounds.width,
                self.floorplan_size / bounds.height
            )
            self._scale_x = scale
            self._scale_y = scale
        
        # Calculate offsets to center the floorplan
        scaled_width = bounds.width * self._scale_x
        scaled_height = bounds.height * self._scale_y
        
        self._offset_x = (self.artboard_size - scaled_width) / 2
        self._offset_y = (self.artboard_size - scaled_height) / 2
    
    def transform(self, cad_x: float, cad_y: float) -> TransformResult:
        """
        Transform a single CAD coordinate to SiteOwl coordinates.
        
        Args:
            cad_x: CAD X coordinate
            cad_y: CAD Y coordinate
            
        Returns:
            TransformResult with artboard and SiteOwl coordinates
        """
        if self._bounds is None:
            raise ValueError("Bounds not set. Call set_bounds() first.")
        
        # Apply rotation if needed
        if self.rotation_rad != 0:
            cx, cy = self._bounds.center
            dx = cad_x - cx
            dy = cad_y - cy
            cos_r = math.cos(self.rotation_rad)
            sin_r = math.sin(self.rotation_rad)
            cad_x = cx + dx * cos_r - dy * sin_r
            cad_y = cy + dx * sin_r + dy * cos_r
        
        # Normalize to bounds origin
        norm_x = cad_x - self._bounds.min_x
        norm_y = cad_y - self._bounds.min_y
        
        # Scale to artboard
        art_x = self._offset_x + norm_x * self._scale_x
        
        # Y-axis: CAD is Y-up, SiteOwl is Y-down
        if self.flip_y:
            # Flip: max_y becomes 0, min_y becomes height
            norm_y_flipped = self._bounds.height - norm_y
            art_y = self._offset_y + norm_y_flipped * self._scale_y
        else:
            art_y = self._offset_y + norm_y * self._scale_y
        
        # Convert to SiteOwl (0-100)
        site_x = round(art_x / 10.0, 2)
        site_y = round(art_y / 10.0, 2)
        
        # Check if in bounds
        in_bounds = (
            0 <= art_x <= self.artboard_size and
            0 <= art_y <= self.artboard_size
        )
        
        # Calculate confidence based on position
        confidence = 1.0
        if not in_bounds:
            # Reduce confidence for out-of-bounds points
            dist_from_center = math.sqrt(
                (art_x - self.artboard_size/2)**2 + 
                (art_y - self.artboard_size/2)**2
            )
            max_dist = self.artboard_size * math.sqrt(2) / 2
            confidence = max(0.0, 1.0 - (dist_from_center / max_dist - 0.7) * 2)
        
        return TransformResult(
            art_x=art_x,
            art_y=art_y,
            site_x=site_x,
            site_y=site_y,
            in_bounds=in_bounds,
            confidence=confidence
        )
    
    def transform_batch(
        self, 
        points: List[Tuple[float, float]]
    ) -> List[TransformResult]:
        """Transform multiple points at once."""
        return [self.transform(x, y) for x, y in points]
    
    def inverse_transform(
        self, 
        site_x: float, 
        site_y: float
    ) -> Tuple[float, float]:
        """
        Convert SiteOwl coordinates back to CAD coordinates.
        
        Useful for placing new devices at specific SiteOwl positions.
        """
        if self._bounds is None:
            raise ValueError("Bounds not set. Call set_bounds() first.")
        
        # SiteOwl → Artboard
        art_x = site_x * 10.0
        art_y = site_y * 10.0
        
        # Artboard → Normalized
        norm_x = (art_x - self._offset_x) / self._scale_x
        
        if self.flip_y:
            norm_y_flipped = (art_y - self._offset_y) / self._scale_y
            norm_y = self._bounds.height - norm_y_flipped
        else:
            norm_y = (art_y - self._offset_y) / self._scale_y
        
        # Normalized → CAD
        cad_x = norm_x + self._bounds.min_x
        cad_y = norm_y + self._bounds.min_y
        
        # Apply inverse rotation if needed
        if self.rotation_rad != 0:
            cx, cy = self._bounds.center
            dx = cad_x - cx
            dy = cad_y - cy
            cos_r = math.cos(-self.rotation_rad)
            sin_r = math.sin(-self.rotation_rad)
            cad_x = cx + dx * cos_r - dy * sin_r
            cad_y = cy + dx * sin_r + dy * cos_r
        
        return (cad_x, cad_y)
    
    def get_transform_matrix(self) -> List[List[float]]:
        """
        Return the 3x3 transformation matrix.
        
        Useful for applying the same transform in other systems (Unity, etc.)
        
        Returns:
            3x3 matrix as nested list: [[a, b, tx], [c, d, ty], [0, 0, 1]]
        """
        if self._bounds is None:
            return [[1, 0, 0], [0, 1, 0], [0, 0, 1]]
        
        # Translation to origin
        tx1 = -self._bounds.min_x
        ty1 = -self._bounds.min_y
        
        # Scale
        sx = self._scale_x
        sy = self._scale_y if not self.flip_y else -self._scale_y
        
        # Translation to artboard
        tx2 = self._offset_x
        ty2 = self._offset_y if not self.flip_y else (
            self._offset_y + self._bounds.height * self._scale_y
        )
        
        # Combined: M = T2 * S * T1
        return [
            [sx, 0, sx * tx1 + tx2],
            [0, sy, sy * ty1 + ty2],
            [0, 0, 1]
        ]
    
    def __repr__(self) -> str:
        return (
            f"CoordinateMapper(mode={self.mode.name}, "
            f"artboard={self.artboard_size}, "
            f"floorplan={self.floorplan_size})"
        )


# Convenience function for simple transformations
def transform_points_to_siteowl(
    points: List[Tuple[float, float]],
    mode: ScaleMode = ScaleMode.FIT_CONTAIN,
    artboard_size: int = 1000,
    floorplan_size: int = 800
) -> List[Tuple[float, float]]:
    """
    Quick transform of CAD points to SiteOwl coordinates.
    
    Args:
        points: List of (x, y) CAD coordinates
        mode: Scale mode
        artboard_size: Artboard size
        floorplan_size: Usable floorplan area
        
    Returns:
        List of (site_x, site_y) coordinates
    """
    if not points:
        return []
    
    bbox = BoundingBox.from_points(points)
    if bbox is None:
        return [(0, 0)] * len(points)
    
    mapper = CoordinateMapper(
        mode=mode,
        artboard_size=artboard_size,
        floorplan_size=floorplan_size
    )
    mapper.set_bounds(bbox)
    
    results = mapper.transform_batch(points)
    return [(r.site_x, r.site_y) for r in results]
