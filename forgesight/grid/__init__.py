"""
ForgeSight Grid - GIS/Coordinates/Zoning Engine

Coordinate transformation, zone management, and device matching.

Usage:
    from forgesight.grid import CoordinateTransformer, Bounds, ScaleMode
    
    bounds = Bounds(min_x=0, min_y=0, max_x=1000, max_y=500)
    transformer = CoordinateTransformer(mode=ScaleMode.FIT_CONTAIN)
    transformer.set_bounds(bounds)
    
    result = transformer.transform(500, 250)
    print(f"SiteOwl: ({result.site_x}, {result.site_y})")
"""

# Import from shared transform module
from shared.transform.transform_core import (
    CoordinateTransformer,
    Bounds,
    ScaleMode,
    TransformResult,
    transform_points,
)

# Import from shared matching module
from shared.matching.device_matcher import (
    DeviceMatcher,
    MatchResult,
    MatchedPair,
    UnmatchedDevice,
    MatchConfig,
    SourceDevice,
    DeviceSource,
    match_devices,
)

from shared.matching.merge_strategy import (
    MergeStrategy,
    MergedDevice,
    ConflictResolution,
    PreferSource,
    PreferNewest,
    ManualReview,
    Coalesce,
    FieldMerge,
    ConflictType,
)


__all__ = [
    # Transform
    "CoordinateTransformer",
    "Bounds",
    "ScaleMode",
    "TransformResult",
    "transform_points",
    
    # Matching
    "DeviceMatcher",
    "MatchResult",
    "MatchedPair",
    "UnmatchedDevice",
    "MatchConfig",
    "SourceDevice",
    "DeviceSource",
    "match_devices",
    
    # Merge
    "MergeStrategy",
    "MergedDevice",
    "ConflictResolution",
    "PreferSource",
    "PreferNewest",
    "ManualReview",
    "Coalesce",
    "FieldMerge",
    "ConflictType",
]
