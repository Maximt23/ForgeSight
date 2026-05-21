"""
Device Matcher - Core matching algorithm for multi-source device correlation.

Matches devices from different sources (CAD drawings, VIVE scans, SiteOwl imports)
based on proximity and attribute similarity.

Algorithm:
1. Transform all coordinates to SiteOwl space (0-100)
2. Build spatial index for efficient nearest-neighbor lookup
3. Score each potential match by distance + attribute similarity
4. Resolve conflicts using Hungarian algorithm for optimal assignment
5. Return matches with confidence scores

Usage:
    from shared.matching import DeviceMatcher, MatchConfig
    
    matcher = DeviceMatcher(config=MatchConfig(tolerance=0.05))
    result = matcher.match(cad_devices, vive_devices)
    
    for pair in result.matched:
        print(f"{pair.source.name} -> {pair.target.name} ({pair.confidence:.0%})")
"""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Dict, Optional, Tuple, Any, Callable
from uuid import UUID, uuid4
import math


class DeviceSource(Enum):
    """Source system for a device."""
    CAD = auto()
    VIVE = auto()
    SITEOWL = auto()
    MANUAL = auto()
    UNKNOWN = auto()


@dataclass
class SourceDevice:
    """
    Device from a source system (CAD, VIVE, SiteOwl).
    
    Coordinates should be in SiteOwl space (0-100) for matching.
    Use the transformer to convert before matching.
    """
    id: str
    name: str
    x: float  # SiteOwl X (0-100)
    y: float  # SiteOwl Y (0-100)
    source: DeviceSource
    device_type: str = ""
    attributes: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0  # Source confidence (e.g., from detection)
    
    @property
    def position(self) -> Tuple[float, float]:
        return (self.x, self.y)


@dataclass
class MatchedPair:
    """A matched pair of devices from two sources."""
    source: SourceDevice
    target: SourceDevice
    distance: float       # Euclidean distance in SiteOwl units
    confidence: float     # Overall match confidence (0-1)
    distance_score: float # Distance component of score
    attribute_score: float # Attribute similarity component
    match_id: str = field(default_factory=lambda: str(uuid4())[:8])


@dataclass
class UnmatchedDevice:
    """A device that could not be matched."""
    device: SourceDevice
    reason: str
    nearest_distance: Optional[float] = None
    nearest_device_id: Optional[str] = None


@dataclass
class MatchResult:
    """Complete result of a matching operation."""
    matched: List[MatchedPair]
    unmatched_source: List[UnmatchedDevice]
    unmatched_target: List[UnmatchedDevice]
    stats: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def match_rate(self) -> float:
        """Percentage of source devices that were matched."""
        total = len(self.matched) + len(self.unmatched_source)
        return len(self.matched) / total if total > 0 else 0.0
    
    @property
    def avg_confidence(self) -> float:
        """Average confidence of matched pairs."""
        if not self.matched:
            return 0.0
        return sum(m.confidence for m in self.matched) / len(self.matched)


@dataclass
class MatchConfig:
    """Configuration for the matching algorithm."""
    # Distance tolerance (percentage of floor diagonal)
    tolerance: float = 0.05  # 5% of floor = ~5 SiteOwl units
    
    # Maximum distance in SiteOwl units (overrides tolerance if set)
    max_distance: Optional[float] = None
    
    # Minimum confidence to accept a match
    min_confidence: float = 0.3
    
    # Weight for distance vs attributes in scoring
    distance_weight: float = 0.7
    attribute_weight: float = 0.3
    
    # Attribute keys to compare for similarity
    compare_attributes: List[str] = field(default_factory=lambda: [
        "device_type", "name", "manufacturer", "model"
    ])
    
    # Allow one-to-many matches (one CAD device → multiple VIVE detections)
    allow_one_to_many: bool = False
    
    # Use optimal assignment (Hungarian algorithm) vs greedy
    use_optimal_assignment: bool = True


class DeviceMatcher:
    """
    Matches devices from different sources based on proximity and attributes.
    
    The matcher transforms all devices to a common coordinate space (SiteOwl),
    then uses a combination of distance and attribute similarity to find
    the best matches.
    """
    
    # Floor diagonal for tolerance calculation (SiteOwl units)
    FLOOR_DIAGONAL = math.sqrt(100**2 + 100**2)  # ~141.4
    
    def __init__(self, config: Optional[MatchConfig] = None):
        self.config = config or MatchConfig()
        self._spatial_index = None
    
    @property
    def max_distance(self) -> float:
        """Calculate maximum matching distance."""
        if self.config.max_distance is not None:
            return self.config.max_distance
        return self.config.tolerance * self.FLOOR_DIAGONAL
    
    def match(
        self,
        source_devices: List[SourceDevice],
        target_devices: List[SourceDevice]
    ) -> MatchResult:
        """
        Match source devices to target devices.
        
        Args:
            source_devices: Primary device list (e.g., from CAD)
            target_devices: Secondary device list (e.g., from VIVE)
            
        Returns:
            MatchResult with matched pairs and unmatched devices
        """
        if not source_devices or not target_devices:
            return MatchResult(
                matched=[],
                unmatched_source=[
                    UnmatchedDevice(d, "no_targets") for d in source_devices
                ],
                unmatched_target=[
                    UnmatchedDevice(d, "no_sources") for d in target_devices
                ],
                stats={"reason": "empty_input"}
            )
        
        # Build distance matrix
        distances = self._compute_distance_matrix(source_devices, target_devices)
        scores = self._compute_score_matrix(source_devices, target_devices, distances)
        
        # Find optimal assignment
        if self.config.use_optimal_assignment:
            assignments = self._hungarian_assignment(scores)
        else:
            assignments = self._greedy_assignment(scores)
        
        # Build results
        matched = []
        matched_source_ids = set()
        matched_target_ids = set()
        
        for src_idx, tgt_idx, score in assignments:
            src = source_devices[src_idx]
            tgt = target_devices[tgt_idx]
            dist = distances[src_idx][tgt_idx]
            
            if dist > self.max_distance or score < self.config.min_confidence:
                continue
            
            # Calculate component scores
            dist_score = self._distance_score(dist)
            attr_score = self._attribute_similarity(src, tgt)
            
            pair = MatchedPair(
                source=src,
                target=tgt,
                distance=dist,
                confidence=score,
                distance_score=dist_score,
                attribute_score=attr_score
            )
            matched.append(pair)
            matched_source_ids.add(src.id)
            matched_target_ids.add(tgt.id)
        
        # Collect unmatched
        unmatched_source = []
        for src in source_devices:
            if src.id not in matched_source_ids:
                nearest_dist, nearest_id = self._find_nearest(src, target_devices)
                unmatched_source.append(UnmatchedDevice(
                    device=src,
                    reason="no_match_within_tolerance",
                    nearest_distance=nearest_dist,
                    nearest_device_id=nearest_id
                ))
        
        unmatched_target = []
        for tgt in target_devices:
            if tgt.id not in matched_target_ids:
                nearest_dist, nearest_id = self._find_nearest(tgt, source_devices)
                unmatched_target.append(UnmatchedDevice(
                    device=tgt,
                    reason="no_match_within_tolerance",
                    nearest_distance=nearest_dist,
                    nearest_device_id=nearest_id
                ))
        
        return MatchResult(
            matched=matched,
            unmatched_source=unmatched_source,
            unmatched_target=unmatched_target,
            stats={
                "source_count": len(source_devices),
                "target_count": len(target_devices),
                "matched_count": len(matched),
                "max_distance_used": self.max_distance,
                "avg_match_distance": (
                    sum(m.distance for m in matched) / len(matched)
                    if matched else 0
                )
            }
        )
    
    def _compute_distance_matrix(
        self,
        sources: List[SourceDevice],
        targets: List[SourceDevice]
    ) -> List[List[float]]:
        """Compute pairwise Euclidean distances."""
        matrix = []
        for src in sources:
            row = []
            for tgt in targets:
                dist = math.sqrt(
                    (src.x - tgt.x)**2 + (src.y - tgt.y)**2
                )
                row.append(dist)
            matrix.append(row)
        return matrix
    
    def _compute_score_matrix(
        self,
        sources: List[SourceDevice],
        targets: List[SourceDevice],
        distances: List[List[float]]
    ) -> List[List[float]]:
        """Compute match scores combining distance and attributes."""
        scores = []
        for i, src in enumerate(sources):
            row = []
            for j, tgt in enumerate(targets):
                dist_score = self._distance_score(distances[i][j])
                attr_score = self._attribute_similarity(src, tgt)
                
                combined = (
                    self.config.distance_weight * dist_score +
                    self.config.attribute_weight * attr_score
                )
                row.append(combined)
            scores.append(row)
        return scores
    
    def _distance_score(self, distance: float) -> float:
        """Convert distance to a 0-1 score (closer = higher)."""
        if distance >= self.max_distance:
            return 0.0
        return 1.0 - (distance / self.max_distance)
    
    def _attribute_similarity(
        self,
        src: SourceDevice,
        tgt: SourceDevice
    ) -> float:
        """Calculate attribute similarity (0-1)."""
        if not self.config.compare_attributes:
            return 1.0  # No attributes to compare
        
        matches = 0
        comparisons = 0
        
        for key in self.config.compare_attributes:
            src_val = src.attributes.get(key, src.__dict__.get(key))
            tgt_val = tgt.attributes.get(key, tgt.__dict__.get(key))
            
            if src_val is None and tgt_val is None:
                continue
            
            comparisons += 1
            if src_val and tgt_val:
                # Fuzzy string match
                if isinstance(src_val, str) and isinstance(tgt_val, str):
                    if src_val.lower() == tgt_val.lower():
                        matches += 1
                    elif src_val.lower() in tgt_val.lower() or tgt_val.lower() in src_val.lower():
                        matches += 0.5
                elif src_val == tgt_val:
                    matches += 1
        
        return matches / comparisons if comparisons > 0 else 1.0
    
    def _greedy_assignment(
        self,
        scores: List[List[float]]
    ) -> List[Tuple[int, int, float]]:
        """Simple greedy assignment (best score first)."""
        assignments = []
        used_sources = set()
        used_targets = set()
        
        # Flatten and sort by score descending
        candidates = []
        for i, row in enumerate(scores):
            for j, score in enumerate(row):
                candidates.append((i, j, score))
        
        candidates.sort(key=lambda x: x[2], reverse=True)
        
        for src_idx, tgt_idx, score in candidates:
            if src_idx in used_sources or tgt_idx in used_targets:
                continue
            assignments.append((src_idx, tgt_idx, score))
            used_sources.add(src_idx)
            used_targets.add(tgt_idx)
        
        return assignments
    
    def _hungarian_assignment(
        self,
        scores: List[List[float]]
    ) -> List[Tuple[int, int, float]]:
        """
        Optimal assignment using Hungarian algorithm.
        Falls back to greedy if scipy not available.
        """
        try:
            from scipy.optimize import linear_sum_assignment
            import numpy as np
            
            # Convert to cost matrix (we want to maximize score)
            cost_matrix = np.array(scores)
            cost_matrix = -cost_matrix  # Negate for minimization
            
            # Handle non-square matrices
            n_rows, n_cols = cost_matrix.shape
            if n_rows != n_cols:
                # Pad to square
                size = max(n_rows, n_cols)
                padded = np.zeros((size, size))
                padded[:n_rows, :n_cols] = cost_matrix
                cost_matrix = padded
            
            row_ind, col_ind = linear_sum_assignment(cost_matrix)
            
            assignments = []
            for r, c in zip(row_ind, col_ind):
                if r < len(scores) and c < len(scores[0]):
                    assignments.append((r, c, scores[r][c]))
            
            return assignments
            
        except ImportError:
            # Fallback to greedy
            return self._greedy_assignment(scores)
    
    def _find_nearest(
        self,
        device: SourceDevice,
        candidates: List[SourceDevice]
    ) -> Tuple[Optional[float], Optional[str]]:
        """Find nearest device from candidates."""
        if not candidates:
            return None, None
        
        nearest_dist = float('inf')
        nearest_id = None
        
        for cand in candidates:
            dist = math.sqrt(
                (device.x - cand.x)**2 + (device.y - cand.y)**2
            )
            if dist < nearest_dist:
                nearest_dist = dist
                nearest_id = cand.id
        
        return nearest_dist, nearest_id


# Convenience function
def match_devices(
    source: List[Dict],
    target: List[Dict],
    tolerance: float = 0.05
) -> MatchResult:
    """
    Quick match of device dictionaries.
    
    Args:
        source: List of dicts with 'id', 'name', 'x', 'y', 'device_type'
        target: List of dicts with same structure
        tolerance: Match tolerance (fraction of floor)
        
    Returns:
        MatchResult
    """
    src_devices = [
        SourceDevice(
            id=d.get('id', str(i)),
            name=d.get('name', ''),
            x=d['x'],
            y=d['y'],
            source=DeviceSource.CAD,
            device_type=d.get('device_type', ''),
            attributes=d
        )
        for i, d in enumerate(source)
    ]
    
    tgt_devices = [
        SourceDevice(
            id=d.get('id', str(i)),
            name=d.get('name', ''),
            x=d['x'],
            y=d['y'],
            source=DeviceSource.VIVE,
            device_type=d.get('device_type', ''),
            attributes=d
        )
        for i, d in enumerate(target)
    ]
    
    matcher = DeviceMatcher(MatchConfig(tolerance=tolerance))
    return matcher.match(src_devices, tgt_devices)


# Test
if __name__ == "__main__":
    # Test matching
    cad_devices = [
        SourceDevice("c1", "CAM_ENTRANCE", 10.0, 20.0, DeviceSource.CAD, "dome"),
        SourceDevice("c2", "CAM_CHECKOUT", 50.0, 50.0, DeviceSource.CAD, "ptz"),
        SourceDevice("c3", "CAM_BACKROOM", 80.0, 30.0, DeviceSource.CAD, "fixed"),
    ]
    
    vive_devices = [
        SourceDevice("v1", "Camera_A", 10.5, 20.2, DeviceSource.VIVE, "dome"),
        SourceDevice("v2", "Camera_B", 49.8, 50.1, DeviceSource.VIVE, "ptz"),
        SourceDevice("v3", "Camera_C", 90.0, 90.0, DeviceSource.VIVE, "fixed"),  # No match
    ]
    
    matcher = DeviceMatcher()
    result = matcher.match(cad_devices, vive_devices)
    
    print(f"Matched: {len(result.matched)}")
    for pair in result.matched:
        print(f"  {pair.source.name} -> {pair.target.name} "
              f"(dist={pair.distance:.2f}, conf={pair.confidence:.0%})")
    
    print(f"\nUnmatched source: {len(result.unmatched_source)}")
    for u in result.unmatched_source:
        print(f"  {u.device.name}: {u.reason}")
    
    print(f"\nUnmatched target: {len(result.unmatched_target)}")
    for u in result.unmatched_target:
        print(f"  {u.device.name}: {u.reason}")
    
    print(f"\nMatch rate: {result.match_rate:.0%}")
    print(f"Avg confidence: {result.avg_confidence:.0%}")
