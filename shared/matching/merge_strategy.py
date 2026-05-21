"""
Merge Strategy - Rules for combining matched devices into a unified record.

When devices from multiple sources are matched, we need to merge their
attributes into a single canonical record. This module provides:

1. Conflict resolution strategies
2. Source priority rules
3. Audit trail for merged values
4. Manual review flagging

Usage:
    from shared.matching import MergeStrategy, PreferSource, MergedDevice
    
    strategy = MergeStrategy([
        PreferSource("coordinates", DeviceSource.VIVE),  # VIVE has better location
        PreferSource("name", DeviceSource.CAD),          # CAD has correct names
        PreferNewest("ip_address"),                       # Use most recent
    ])
    
    merged = strategy.merge(matched_pair)
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Dict, List, Optional, Any, Callable
from uuid import uuid4

from .device_matcher import MatchedPair, SourceDevice, DeviceSource


class ConflictType(Enum):
    """Type of conflict between source values."""
    NO_CONFLICT = auto()      # Values match or only one has value
    VALUE_MISMATCH = auto()   # Different values
    TYPE_MISMATCH = auto()    # Different types
    MISSING_SOURCE = auto()   # One source missing value
    REQUIRES_REVIEW = auto()  # Flagged for manual review


@dataclass
class FieldMerge:
    """Record of how a field was merged."""
    field_name: str
    final_value: Any
    source_value: Any
    target_value: Any
    chosen_source: DeviceSource
    conflict_type: ConflictType
    strategy_used: str
    confidence: float = 1.0


@dataclass
class MergedDevice:
    """A unified device record from merged sources."""
    id: str
    name: str
    x: float
    y: float
    device_type: str
    source_ids: List[str]
    sources: List[DeviceSource]
    attributes: Dict[str, Any]
    
    # Merge metadata
    merge_id: str = field(default_factory=lambda: str(uuid4())[:8])
    merged_at: datetime = field(default_factory=datetime.utcnow)
    field_merges: List[FieldMerge] = field(default_factory=list)
    requires_review: bool = False
    review_reasons: List[str] = field(default_factory=list)
    confidence: float = 1.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API/storage."""
        return {
            "id": self.id,
            "name": self.name,
            "x": self.x,
            "y": self.y,
            "device_type": self.device_type,
            "source_ids": self.source_ids,
            "sources": [s.name for s in self.sources],
            "attributes": self.attributes,
            "merge_id": self.merge_id,
            "merged_at": self.merged_at.isoformat(),
            "requires_review": self.requires_review,
            "review_reasons": self.review_reasons,
            "confidence": self.confidence
        }


class ConflictResolution:
    """Base class for conflict resolution strategies."""
    
    def __init__(self, field_name: str):
        self.field_name = field_name
    
    def resolve(
        self,
        source: SourceDevice,
        target: SourceDevice
    ) -> FieldMerge:
        """Resolve conflict between source and target values."""
        raise NotImplementedError
    
    def _get_value(self, device: SourceDevice, field: str) -> Any:
        """Get a field value from device."""
        if hasattr(device, field):
            return getattr(device, field)
        return device.attributes.get(field)


class PreferSource(ConflictResolution):
    """Always prefer value from a specific source."""
    
    def __init__(self, field_name: str, preferred: DeviceSource):
        super().__init__(field_name)
        self.preferred = preferred
    
    def resolve(
        self,
        source: SourceDevice,
        target: SourceDevice
    ) -> FieldMerge:
        src_val = self._get_value(source, self.field_name)
        tgt_val = self._get_value(target, self.field_name)
        
        # Determine which device matches preferred source
        if source.source == self.preferred:
            chosen = source.source
            final_val = src_val if src_val is not None else tgt_val
        elif target.source == self.preferred:
            chosen = target.source
            final_val = tgt_val if tgt_val is not None else src_val
        else:
            # Neither matches preferred, use source
            chosen = source.source
            final_val = src_val if src_val is not None else tgt_val
        
        # Determine conflict type
        if src_val == tgt_val:
            conflict = ConflictType.NO_CONFLICT
        elif src_val is None or tgt_val is None:
            conflict = ConflictType.MISSING_SOURCE
        else:
            conflict = ConflictType.VALUE_MISMATCH
        
        return FieldMerge(
            field_name=self.field_name,
            final_value=final_val,
            source_value=src_val,
            target_value=tgt_val,
            chosen_source=chosen,
            conflict_type=conflict,
            strategy_used=f"PreferSource({self.preferred.name})"
        )


class PreferNewest(ConflictResolution):
    """Prefer value from the most recently updated source."""
    
    def resolve(
        self,
        source: SourceDevice,
        target: SourceDevice
    ) -> FieldMerge:
        src_val = self._get_value(source, self.field_name)
        tgt_val = self._get_value(target, self.field_name)
        
        # Check for timestamps
        src_time = source.attributes.get("updated_at", source.attributes.get("created_at"))
        tgt_time = target.attributes.get("updated_at", target.attributes.get("created_at"))
        
        if src_time and tgt_time:
            if isinstance(src_time, str):
                src_time = datetime.fromisoformat(src_time.replace('Z', '+00:00'))
            if isinstance(tgt_time, str):
                tgt_time = datetime.fromisoformat(tgt_time.replace('Z', '+00:00'))
            
            if src_time >= tgt_time:
                final_val = src_val
                chosen = source.source
            else:
                final_val = tgt_val
                chosen = target.source
        else:
            # No timestamps, prefer source
            final_val = src_val if src_val is not None else tgt_val
            chosen = source.source
        
        conflict = (
            ConflictType.NO_CONFLICT if src_val == tgt_val
            else ConflictType.VALUE_MISMATCH
        )
        
        return FieldMerge(
            field_name=self.field_name,
            final_value=final_val,
            source_value=src_val,
            target_value=tgt_val,
            chosen_source=chosen,
            conflict_type=conflict,
            strategy_used="PreferNewest"
        )


class ManualReview(ConflictResolution):
    """Flag for manual review if values conflict."""
    
    def __init__(self, field_name: str, fallback: DeviceSource = DeviceSource.CAD):
        super().__init__(field_name)
        self.fallback = fallback
    
    def resolve(
        self,
        source: SourceDevice,
        target: SourceDevice
    ) -> FieldMerge:
        src_val = self._get_value(source, self.field_name)
        tgt_val = self._get_value(target, self.field_name)
        
        if src_val == tgt_val or src_val is None or tgt_val is None:
            # No conflict
            final_val = src_val if src_val is not None else tgt_val
            conflict = ConflictType.NO_CONFLICT
        else:
            # Conflict - use fallback but flag for review
            if source.source == self.fallback:
                final_val = src_val
                chosen = source.source
            else:
                final_val = tgt_val
                chosen = target.source
            conflict = ConflictType.REQUIRES_REVIEW
            
            return FieldMerge(
                field_name=self.field_name,
                final_value=final_val,
                source_value=src_val,
                target_value=tgt_val,
                chosen_source=chosen,
                conflict_type=conflict,
                strategy_used=f"ManualReview(fallback={self.fallback.name})",
                confidence=0.5  # Low confidence due to conflict
            )
        
        return FieldMerge(
            field_name=self.field_name,
            final_value=final_val,
            source_value=src_val,
            target_value=tgt_val,
            chosen_source=source.source if src_val else target.source,
            conflict_type=conflict,
            strategy_used="ManualReview"
        )


class Coalesce(ConflictResolution):
    """Use first non-null value from ordered sources."""
    
    def __init__(self, field_name: str, priority: List[DeviceSource]):
        super().__init__(field_name)
        self.priority = priority
    
    def resolve(
        self,
        source: SourceDevice,
        target: SourceDevice
    ) -> FieldMerge:
        devices = {source.source: source, target.source: target}
        
        for prio_source in self.priority:
            if prio_source in devices:
                val = self._get_value(devices[prio_source], self.field_name)
                if val is not None:
                    return FieldMerge(
                        field_name=self.field_name,
                        final_value=val,
                        source_value=self._get_value(source, self.field_name),
                        target_value=self._get_value(target, self.field_name),
                        chosen_source=prio_source,
                        conflict_type=ConflictType.NO_CONFLICT,
                        strategy_used=f"Coalesce({[s.name for s in self.priority]})"
                    )
        
        # Fallback
        src_val = self._get_value(source, self.field_name)
        tgt_val = self._get_value(target, self.field_name)
        
        return FieldMerge(
            field_name=self.field_name,
            final_value=src_val or tgt_val,
            source_value=src_val,
            target_value=tgt_val,
            chosen_source=source.source,
            conflict_type=ConflictType.MISSING_SOURCE,
            strategy_used="Coalesce(fallback)"
        )


class MergeStrategy:
    """
    Strategy for merging matched device pairs.
    
    Combines multiple field-level resolution strategies into a complete
    merge operation.
    """
    
    # Default resolution strategies
    DEFAULT_STRATEGIES = {
        "x": PreferSource("x", DeviceSource.VIVE),
        "y": PreferSource("y", DeviceSource.VIVE),
        "name": PreferSource("name", DeviceSource.CAD),
        "device_type": PreferSource("device_type", DeviceSource.CAD),
    }
    
    def __init__(
        self,
        strategies: Optional[List[ConflictResolution]] = None,
        default_source: DeviceSource = DeviceSource.CAD
    ):
        self.strategies: Dict[str, ConflictResolution] = dict(self.DEFAULT_STRATEGIES)
        self.default_source = default_source
        
        if strategies:
            for strategy in strategies:
                self.strategies[strategy.field_name] = strategy
    
    def merge(self, pair: MatchedPair) -> MergedDevice:
        """Merge a matched pair into a unified device."""
        source = pair.source
        target = pair.target
        
        field_merges = []
        requires_review = False
        review_reasons = []
        
        # Merge core fields
        x_merge = self.strategies.get("x", PreferSource("x", self.default_source)).resolve(source, target)
        y_merge = self.strategies.get("y", PreferSource("y", self.default_source)).resolve(source, target)
        name_merge = self.strategies.get("name", PreferSource("name", self.default_source)).resolve(source, target)
        type_merge = self.strategies.get("device_type", PreferSource("device_type", self.default_source)).resolve(source, target)
        
        field_merges.extend([x_merge, y_merge, name_merge, type_merge])
        
        # Check for review flags
        for merge in field_merges:
            if merge.conflict_type == ConflictType.REQUIRES_REVIEW:
                requires_review = True
                review_reasons.append(f"Field '{merge.field_name}' has conflicting values")
        
        # Merge attributes
        merged_attrs = {}
        all_keys = set(source.attributes.keys()) | set(target.attributes.keys())
        
        for key in all_keys:
            if key in ["x", "y", "name", "device_type"]:
                continue
            
            strategy = self.strategies.get(key)
            if strategy:
                attr_merge = strategy.resolve(source, target)
            else:
                # Default: prefer source
                attr_merge = PreferSource(key, self.default_source).resolve(source, target)
            
            merged_attrs[key] = attr_merge.final_value
            field_merges.append(attr_merge)
            
            if attr_merge.conflict_type == ConflictType.REQUIRES_REVIEW:
                requires_review = True
                review_reasons.append(f"Attribute '{key}' has conflicting values")
        
        # Calculate overall confidence
        confidence = pair.confidence * (
            sum(m.confidence for m in field_merges) / len(field_merges)
            if field_merges else 1.0
        )
        
        return MergedDevice(
            id=f"{source.id}_{target.id}",
            name=name_merge.final_value or source.name or target.name,
            x=x_merge.final_value,
            y=y_merge.final_value,
            device_type=type_merge.final_value or source.device_type or target.device_type,
            source_ids=[source.id, target.id],
            sources=[source.source, target.source],
            attributes=merged_attrs,
            field_merges=field_merges,
            requires_review=requires_review,
            review_reasons=review_reasons,
            confidence=confidence
        )
    
    def merge_all(self, pairs: List[MatchedPair]) -> List[MergedDevice]:
        """Merge all matched pairs."""
        return [self.merge(pair) for pair in pairs]


# Test
if __name__ == "__main__":
    from .device_matcher import DeviceMatcher, SourceDevice, DeviceSource
    
    # Create test devices
    cad = SourceDevice(
        id="cad1",
        name="CAM_ENTRANCE_01",
        x=10.0,
        y=20.0,
        source=DeviceSource.CAD,
        device_type="dome",
        attributes={"manufacturer": "Bosch", "model": "Flexidome"}
    )
    
    vive = SourceDevice(
        id="vive1",
        name="Camera_A",
        x=10.5,
        y=20.2,
        source=DeviceSource.VIVE,
        device_type="dome",
        attributes={"manufacturer": "Bosch", "model": "Unknown"}
    )
    
    # Create matched pair
    pair = MatchedPair(
        source=cad,
        target=vive,
        distance=0.54,
        confidence=0.95,
        distance_score=0.96,
        attribute_score=0.9
    )
    
    # Merge
    strategy = MergeStrategy([
        PreferSource("x", DeviceSource.VIVE),
        PreferSource("y", DeviceSource.VIVE),
        PreferSource("name", DeviceSource.CAD),
        ManualReview("model"),
    ])
    
    merged = strategy.merge(pair)
    
    print(f"Merged Device: {merged.name}")
    print(f"  Position: ({merged.x}, {merged.y})")
    print(f"  Type: {merged.device_type}")
    print(f"  Confidence: {merged.confidence:.0%}")
    print(f"  Requires Review: {merged.requires_review}")
    if merged.review_reasons:
        print(f"  Review Reasons: {merged.review_reasons}")
    print(f"\nField Merges:")
    for fm in merged.field_merges[:5]:
        print(f"  {fm.field_name}: {fm.source_value} + {fm.target_value} -> {fm.final_value} ({fm.strategy_used})")
