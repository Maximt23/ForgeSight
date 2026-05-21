"""
Device Matching Module

Correlates devices from different sources (CAD, VIVE, SiteOwl imports)
based on proximity, attributes, and confidence scoring.

This is the core intelligence for merging multi-source device data.
"""

from .device_matcher import (
    DeviceMatcher,
    MatchResult,
    MatchedPair,
    UnmatchedDevice,
    MatchConfig,
)
from .merge_strategy import (
    MergeStrategy,
    MergedDevice,
    ConflictResolution,
    PreferSource,
    PreferNewest,
    ManualReview,
)

__all__ = [
    "DeviceMatcher",
    "MatchResult",
    "MatchedPair",
    "UnmatchedDevice",
    "MatchConfig",
    "MergeStrategy",
    "MergedDevice",
    "ConflictResolution",
    "PreferSource",
    "PreferNewest",
    "ManualReview",
]
