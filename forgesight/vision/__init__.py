"""
ForgeSight Vision - Camera/FOV Coverage Engine

Analyze camera coverage and optimize placement.

Status: 🟡 Beta

Usage:
    from forgesight.vision import Camera, FOVCalculator, CoverageAnalyzer
    
    camera = Camera(type="dome", lens_mm=2.8, mount_height_ft=12)
    fov = FOVCalculator.compute(camera)
    
    analyzer = CoverageAnalyzer(floor_plan)
    analyzer.add_cameras(cameras)
    heatmap = analyzer.generate_heatmap()
"""

from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict, Any
from enum import Enum
import math


class CameraType(str, Enum):
    """Types of security cameras."""
    DOME = "dome"
    PTZ = "ptz"
    BULLET = "bullet"
    FISHEYE = "fisheye"
    PANORAMIC = "panoramic"
    BOX = "box"


@dataclass
class Camera:
    """A security camera with specifications."""
    id: str = ""
    type: CameraType = CameraType.DOME
    lens_mm: float = 2.8
    sensor_size: str = "1/2.8"
    resolution: Tuple[int, int] = (1920, 1080)
    mount_height_ft: float = 12.0
    x: float = 0.0
    y: float = 0.0
    rotation_deg: float = 0.0
    
    # Computed fields
    h_fov_deg: Optional[float] = None
    v_fov_deg: Optional[float] = None


@dataclass
class FOVResult:
    """Result of FOV calculation."""
    h_degrees: float
    v_degrees: float
    floor_coverage_sqft: float
    coverage_radius_ft: float
    near_distance_ft: float
    far_distance_ft: float


class FOVCalculator:
    """Calculate camera field of view."""
    
    # Sensor sizes in mm (width x height)
    SENSOR_SIZES = {
        "1/4": (3.6, 2.7),
        "1/3": (4.8, 3.6),
        "1/2.8": (5.0, 3.75),
        "1/2.7": (5.4, 4.0),
        "1/2.5": (5.8, 4.3),
        "1/2": (6.4, 4.8),
        "1/1.8": (7.2, 5.4),
        "2/3": (8.8, 6.6),
        "1": (12.8, 9.6),
    }
    
    @classmethod
    def compute(cls, camera: Camera) -> FOVResult:
        """Compute field of view for a camera."""
        # Get sensor dimensions
        if camera.sensor_size in cls.SENSOR_SIZES:
            sensor_w, sensor_h = cls.SENSOR_SIZES[camera.sensor_size]
        else:
            sensor_w, sensor_h = 5.0, 3.75  # Default to 1/2.8
        
        # Calculate FOV angles
        h_fov = 2 * math.degrees(math.atan(sensor_w / (2 * camera.lens_mm)))
        v_fov = 2 * math.degrees(math.atan(sensor_h / (2 * camera.lens_mm)))
        
        # Override for special camera types
        if camera.type == CameraType.FISHEYE:
            h_fov = 180
            v_fov = 180
        elif camera.type == CameraType.PANORAMIC:
            h_fov = 180
            v_fov = 90
        
        # Calculate floor coverage (simplified)
        height_m = camera.mount_height_ft * 0.3048
        coverage_radius = height_m * math.tan(math.radians(h_fov / 2))
        coverage_radius_ft = coverage_radius / 0.3048
        
        floor_coverage_sqft = math.pi * coverage_radius_ft ** 2
        
        # Store computed values
        camera.h_fov_deg = h_fov
        camera.v_fov_deg = v_fov
        
        return FOVResult(
            h_degrees=h_fov,
            v_degrees=v_fov,
            floor_coverage_sqft=floor_coverage_sqft,
            coverage_radius_ft=coverage_radius_ft,
            near_distance_ft=0,
            far_distance_ft=coverage_radius_ft * 2
        )


@dataclass
class CoverageStats:
    """Statistics about camera coverage."""
    total_area_sqft: float = 0.0
    covered_area_sqft: float = 0.0
    coverage_percent: float = 0.0
    blind_spot_count: int = 0
    overlap_percent: float = 0.0


@dataclass
class BlindSpot:
    """An area with no camera coverage."""
    x: float
    y: float
    area_sqft: float
    priority: str = "low"  # low, medium, high, critical


class CoverageAnalyzer:
    """Analyze camera coverage on a floor plan."""
    
    def __init__(self, floor_plan: Optional[Dict[str, Any]] = None):
        self.floor_plan = floor_plan or {}
        self.cameras: List[Camera] = []
        self._heatmap = None
    
    def add_camera(self, camera: Camera):
        """Add a camera to analysis."""
        if camera.h_fov_deg is None:
            FOVCalculator.compute(camera)
        self.cameras.append(camera)
        self._heatmap = None  # Invalidate cache
    
    def add_cameras(self, cameras: List[Camera]):
        """Add multiple cameras."""
        for camera in cameras:
            self.add_camera(camera)
    
    def generate_heatmap(self, resolution: int = 100) -> List[List[float]]:
        """Generate coverage heatmap."""
        # Initialize grid
        heatmap = [[0.0 for _ in range(resolution)] for _ in range(resolution)]
        
        # Get floor plan bounds
        width = self.floor_plan.get("width", 100)
        height = self.floor_plan.get("height", 100)
        
        # Calculate coverage for each cell
        for i in range(resolution):
            for j in range(resolution):
                x = (j / resolution) * width
                y = (i / resolution) * height
                
                coverage = 0.0
                for camera in self.cameras:
                    dist = math.sqrt((x - camera.x) ** 2 + (y - camera.y) ** 2)
                    if camera.h_fov_deg:
                        radius = camera.mount_height_ft * math.tan(math.radians(camera.h_fov_deg / 2))
                        if dist <= radius:
                            coverage += 1.0 - (dist / radius)
                
                heatmap[i][j] = min(coverage, 1.0)
        
        self._heatmap = heatmap
        return heatmap
    
    def get_statistics(self) -> CoverageStats:
        """Get coverage statistics."""
        if self._heatmap is None:
            self.generate_heatmap()
        
        total_cells = len(self._heatmap) * len(self._heatmap[0])
        covered_cells = sum(
            1 for row in self._heatmap for cell in row if cell > 0
        )
        
        width = self.floor_plan.get("width", 100)
        height = self.floor_plan.get("height", 100)
        total_area = width * height
        
        coverage_percent = (covered_cells / total_cells) * 100
        
        return CoverageStats(
            total_area_sqft=total_area,
            covered_area_sqft=total_area * (coverage_percent / 100),
            coverage_percent=coverage_percent,
            blind_spot_count=self._count_blind_spots(),
            overlap_percent=self._calculate_overlap()
        )
    
    def find_blind_spots(self, min_area_sqft: float = 50) -> List[BlindSpot]:
        """Find areas with no coverage."""
        if self._heatmap is None:
            self.generate_heatmap()
        
        # Simple blind spot detection
        blind_spots = []
        resolution = len(self._heatmap)
        width = self.floor_plan.get("width", 100)
        height = self.floor_plan.get("height", 100)
        cell_area = (width / resolution) * (height / resolution)
        
        for i in range(resolution):
            for j in range(resolution):
                if self._heatmap[i][j] == 0:
                    x = (j / resolution) * width
                    y = (i / resolution) * height
                    blind_spots.append(BlindSpot(
                        x=x,
                        y=y,
                        area_sqft=cell_area,
                        priority="medium"
                    ))
        
        return blind_spots
    
    def _count_blind_spots(self) -> int:
        """Count number of blind spot regions."""
        return len(self.find_blind_spots())
    
    def _calculate_overlap(self) -> float:
        """Calculate percentage of overlapping coverage."""
        if self._heatmap is None:
            return 0.0
        
        overlap_cells = sum(
            1 for row in self._heatmap for cell in row if cell > 1.0
        )
        total_cells = len(self._heatmap) * len(self._heatmap[0])
        
        return (overlap_cells / total_cells) * 100


__all__ = [
    "Camera",
    "CameraType",
    "FOVCalculator",
    "FOVResult",
    "CoverageAnalyzer",
    "CoverageStats",
    "BlindSpot",
]
