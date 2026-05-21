"""
Device detection engine for CadOwl.

Detects and classifies devices from CAD block insertions using:
- Layer name patterns
- Block name patterns
- Block attributes
- Spatial analysis
"""

import re
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional, Set, Tuple
from pathlib import Path


class SystemType(Enum):
    """High-level system classification."""
    VIDEO_SURVEILLANCE = "Video Surveillance"
    FIRE_ALARM = "Fire Alarm"
    INTRUSION = "Intrusion Detection"
    ACCESS_CONTROL = "Access Control"
    UNKNOWN = "Unknown"


class DeviceType(Enum):
    """Specific device type classification."""
    # Video Surveillance
    FIXED_CAMERA = "Fixed Camera"
    DOME_CAMERA = "Dome Camera"
    PTZ_CAMERA = "PTZ Camera"
    BULLET_CAMERA = "Bullet Camera"
    PANORAMIC_CAMERA = "Panoramic Camera"
    
    # Fire Alarm
    SMOKE_DETECTOR = "Smoke Detector"
    HEAT_DETECTOR = "Heat Detector"
    PULL_STATION = "Pull Station"
    HORN_STROBE = "Horn/Strobe"
    SPEAKER_STROBE = "Speaker/Strobe"
    WATERFLOW_SWITCH = "Waterflow Switch"
    TAMPER_SWITCH = "Tamper Switch"
    DUCT_DETECTOR = "Duct Detector"
    BEAM_DETECTOR = "Beam Detector"
    
    # Intrusion
    MOTION_SENSOR = "Motion Sensor"
    DOOR_CONTACT = "Door Contact"
    GLASS_BREAK = "Glass Break Sensor"
    PANIC_BUTTON = "Panic Button"
    
    # Access Control
    CARD_READER = "Card Reader"
    KEYPAD = "Keypad"
    DOOR_CONTROLLER = "Door Controller"
    
    # Generic
    UNKNOWN = "Unknown Device"


@dataclass
class DevicePattern:
    """Pattern definition for device detection."""
    pattern: str           # Regex pattern
    system_type: SystemType
    device_type: DeviceType
    confidence: float = 1.0  # Pattern reliability (0-1)
    description: str = ""


# ============================================================================
# PATTERN DEFINITIONS
# ============================================================================

# Layer patterns - what layers typically contain devices
LAYER_PATTERNS: List[DevicePattern] = [
    # Video Surveillance
    DevicePattern(r"(?i).*cctv.*", SystemType.VIDEO_SURVEILLANCE, DeviceType.FIXED_CAMERA, 0.9),
    DevicePattern(r"(?i).*camera.*", SystemType.VIDEO_SURVEILLANCE, DeviceType.FIXED_CAMERA, 0.9),
    DevicePattern(r"(?i).*video.*surv.*", SystemType.VIDEO_SURVEILLANCE, DeviceType.FIXED_CAMERA, 0.9),
    DevicePattern(r"(?i).*surveillance.*", SystemType.VIDEO_SURVEILLANCE, DeviceType.FIXED_CAMERA, 0.8),
    
    # Fire Alarm
    DevicePattern(r"(?i).*notification.*", SystemType.FIRE_ALARM, DeviceType.HORN_STROBE, 0.9),
    DevicePattern(r"(?i).*e-?alarm.*", SystemType.FIRE_ALARM, DeviceType.SMOKE_DETECTOR, 0.9),
    DevicePattern(r"(?i).*efp.*", SystemType.FIRE_ALARM, DeviceType.SMOKE_DETECTOR, 0.9),
    DevicePattern(r"(?i).*fire.*alarm.*", SystemType.FIRE_ALARM, DeviceType.SMOKE_DETECTOR, 0.9),
    DevicePattern(r"(?i).*notf.*", SystemType.FIRE_ALARM, DeviceType.HORN_STROBE, 0.8),
    DevicePattern(r"(?i).*facp.*", SystemType.FIRE_ALARM, DeviceType.SMOKE_DETECTOR, 0.8),
    
    # Intrusion
    DevicePattern(r"(?i).*intrusion.*", SystemType.INTRUSION, DeviceType.MOTION_SENSOR, 0.9),
    DevicePattern(r"(?i).*burg.*", SystemType.INTRUSION, DeviceType.MOTION_SENSOR, 0.9),
    DevicePattern(r"(?i).*security.*", SystemType.INTRUSION, DeviceType.MOTION_SENSOR, 0.7),
    DevicePattern(r"(?i).*motion.*", SystemType.INTRUSION, DeviceType.MOTION_SENSOR, 0.8),
    
    # Access Control
    DevicePattern(r"(?i).*access.*", SystemType.ACCESS_CONTROL, DeviceType.CARD_READER, 0.8),
    DevicePattern(r"(?i).*door.*control.*", SystemType.ACCESS_CONTROL, DeviceType.DOOR_CONTROLLER, 0.8),
]

# Block patterns - specific block names that indicate devices
BLOCK_PATTERNS: List[DevicePattern] = [
    # Fire Alarm - Notification
    DevicePattern(r"(?i)^scr$", SystemType.FIRE_ALARM, DeviceType.HORN_STROBE, 1.0, "System Sensor SCR"),
    DevicePattern(r"(?i)^pc2r$", SystemType.FIRE_ALARM, DeviceType.HORN_STROBE, 1.0, "System Sensor PC2R"),
    DevicePattern(r"(?i)^p2rk$", SystemType.FIRE_ALARM, DeviceType.HORN_STROBE, 1.0, "Weatherproof P2RK"),
    DevicePattern(r"(?i)^spr$", SystemType.FIRE_ALARM, DeviceType.SPEAKER_STROBE, 1.0, "Speaker"),
    DevicePattern(r"(?i).*horn.*strobe.*", SystemType.FIRE_ALARM, DeviceType.HORN_STROBE, 0.9),
    DevicePattern(r"(?i).*strobe.*", SystemType.FIRE_ALARM, DeviceType.HORN_STROBE, 0.8),
    
    # Fire Alarm - Detection
    DevicePattern(r"(?i)^d4120$", SystemType.FIRE_ALARM, DeviceType.SMOKE_DETECTOR, 1.0, "Bosch D4120"),
    DevicePattern(r"(?i)^d273$", SystemType.FIRE_ALARM, DeviceType.SMOKE_DETECTOR, 1.0, "Bosch D273"),
    DevicePattern(r"(?i).*smoke.*", SystemType.FIRE_ALARM, DeviceType.SMOKE_DETECTOR, 0.9),
    DevicePattern(r"(?i).*photo.*", SystemType.FIRE_ALARM, DeviceType.SMOKE_DETECTOR, 0.8),
    DevicePattern(r"(?i)^sd[_-]?.*", SystemType.FIRE_ALARM, DeviceType.SMOKE_DETECTOR, 0.9),
    DevicePattern(r"(?i).*heat.*det.*", SystemType.FIRE_ALARM, DeviceType.HEAT_DETECTOR, 0.9),
    DevicePattern(r"(?i).*duct.*det.*", SystemType.FIRE_ALARM, DeviceType.DUCT_DETECTOR, 0.9),
    
    # Fire Alarm - Manual
    DevicePattern(r"(?i)^fmm.*", SystemType.FIRE_ALARM, DeviceType.PULL_STATION, 1.0, "Fire Manual Module"),
    DevicePattern(r"(?i).*pull.*station.*", SystemType.FIRE_ALARM, DeviceType.PULL_STATION, 0.9),
    DevicePattern(r"(?i).*manual.*pull.*", SystemType.FIRE_ALARM, DeviceType.PULL_STATION, 0.9),
    DevicePattern(r"(?i)^ps[_-]?\d*$", SystemType.FIRE_ALARM, DeviceType.PULL_STATION, 0.8),
    
    # Fire Alarm - Monitoring
    DevicePattern(r"(?i).*swfs.*", SystemType.FIRE_ALARM, DeviceType.WATERFLOW_SWITCH, 1.0),
    DevicePattern(r"(?i).*flow.*", SystemType.FIRE_ALARM, DeviceType.WATERFLOW_SWITCH, 0.8),
    DevicePattern(r"(?i).*svts.*", SystemType.FIRE_ALARM, DeviceType.TAMPER_SWITCH, 1.0),
    DevicePattern(r"(?i).*tamper.*", SystemType.FIRE_ALARM, DeviceType.TAMPER_SWITCH, 0.9),
    
    # Video Surveillance
    DevicePattern(r"(?i).*dome.*", SystemType.VIDEO_SURVEILLANCE, DeviceType.DOME_CAMERA, 0.9),
    DevicePattern(r"(?i).*ptz.*", SystemType.VIDEO_SURVEILLANCE, DeviceType.PTZ_CAMERA, 0.95),
    DevicePattern(r"(?i).*bullet.*", SystemType.VIDEO_SURVEILLANCE, DeviceType.BULLET_CAMERA, 0.9),
    DevicePattern(r"(?i).*pan[oa]?ramic.*", SystemType.VIDEO_SURVEILLANCE, DeviceType.PANORAMIC_CAMERA, 0.9),
    DevicePattern(r"(?i).*360.*", SystemType.VIDEO_SURVEILLANCE, DeviceType.PANORAMIC_CAMERA, 0.85),
    DevicePattern(r"(?i)^cam[_-]?.*", SystemType.VIDEO_SURVEILLANCE, DeviceType.FIXED_CAMERA, 0.85),
    DevicePattern(r"(?i).*camera.*", SystemType.VIDEO_SURVEILLANCE, DeviceType.FIXED_CAMERA, 0.8),
    DevicePattern(r"(?i).*cctv.*", SystemType.VIDEO_SURVEILLANCE, DeviceType.FIXED_CAMERA, 0.85),
    
    # Intrusion
    DevicePattern(r"(?i).*motion.*", SystemType.INTRUSION, DeviceType.MOTION_SENSOR, 0.9),
    DevicePattern(r"(?i).*pir.*", SystemType.INTRUSION, DeviceType.MOTION_SENSOR, 0.9),
    DevicePattern(r"(?i).*door.*contact.*", SystemType.INTRUSION, DeviceType.DOOR_CONTACT, 0.9),
    DevicePattern(r"(?i).*glass.*break.*", SystemType.INTRUSION, DeviceType.GLASS_BREAK, 0.9),
    DevicePattern(r"(?i).*panic.*", SystemType.INTRUSION, DeviceType.PANIC_BUTTON, 0.9),
    DevicePattern(r"(?i).*duress.*", SystemType.INTRUSION, DeviceType.PANIC_BUTTON, 0.85),
    
    # Access Control
    DevicePattern(r"(?i).*card.*reader.*", SystemType.ACCESS_CONTROL, DeviceType.CARD_READER, 0.9),
    DevicePattern(r"(?i).*prox.*reader.*", SystemType.ACCESS_CONTROL, DeviceType.CARD_READER, 0.9),
    DevicePattern(r"(?i).*keypad.*", SystemType.ACCESS_CONTROL, DeviceType.KEYPAD, 0.9),
    
    # Walmart-specific patterns
    DevicePattern(r"(?i)^wmpoint$", SystemType.VIDEO_SURVEILLANCE, DeviceType.FIXED_CAMERA, 0.8),
    DevicePattern(r"(?i)^efp.*e-.*", SystemType.FIRE_ALARM, DeviceType.SMOKE_DETECTOR, 0.85),
    DevicePattern(r"(?i)^a\$c.*", SystemType.FIRE_ALARM, DeviceType.SMOKE_DETECTOR, 0.7),
]

# Blocks to always exclude
EXCLUDE_PATTERNS: List[str] = [
    r"(?i)^\*u\d+$",        # Anonymous blocks
    r"(?i)^\*model_space$",
    r"(?i)^\*paper_space.*",
    r"(?i)^_.*",            # System blocks
    r"(?i).*title.*block.*",
    r"(?i).*border.*",
    r"(?i).*legend.*",
    r"(?i).*schedule.*",
    r"(?i).*detail.*",
    r"(?i).*viewport.*",
    r"(?i).*defpoints.*",
    r"(?i)^aecb_.*",        # MEP connectors
    r"(?i)^xborder.*",
    r"(?i)^xfloor.*",
    r"(?i)^shttitle.*",
    r"(?i)^stamp.*",
]

# Attribute tags that typically contain device names
NAME_ATTRIBUTE_TAGS: List[str] = [
    "NAME", "DEVICE", "DEVICE_NAME", "DEV_NAME",
    "D", "ID", "DEVICE_ID", "DEV_ID",
    "TAG", "LABEL", "NUMBER", "NUM",
    "S", "115CD", "WP", "CAMERA",
    "DESCRIPTION", "DESC",
]


@dataclass
class Device:
    """Detected device from CAD."""
    
    block_name: str
    layer: str
    cad_x: float
    cad_y: float
    system_type: SystemType = SystemType.UNKNOWN
    device_type: DeviceType = DeviceType.UNKNOWN
    attributes: Dict[str, str] = field(default_factory=dict)
    
    # Transformed coordinates (set by CoordinateMapper)
    art_x: float = 0.0
    art_y: float = 0.0
    site_x: float = 0.0
    site_y: float = 0.0
    
    # Detection metadata
    detection_confidence: float = 0.0
    matched_patterns: List[str] = field(default_factory=list)
    
    @property
    def name(self) -> str:
        """Get device name from attributes or block name."""
        for tag in NAME_ATTRIBUTE_TAGS:
            tag_upper = tag.upper()
            for attr_tag, attr_val in self.attributes.items():
                if attr_tag.upper() == tag_upper and attr_val.strip():
                    return attr_val.strip()
        return self.block_name
    
    @property
    def coordinates_str(self) -> str:
        """Format coordinates for SiteOwl CSV."""
        return f"({self.site_x}, {self.site_y})"
    
    def __repr__(self) -> str:
        return (
            f"Device(name={self.name!r}, system={self.system_type.name}, "
            f"type={self.device_type.name}, pos=({self.site_x}, {self.site_y}))"
        )


@dataclass
class DeviceMatch:
    """Result of pattern matching for a block."""
    
    device: Device
    layer_matches: List[DevicePattern]
    block_matches: List[DevicePattern]
    
    @property
    def confidence(self) -> float:
        """Overall confidence score."""
        all_matches = self.layer_matches + self.block_matches
        if not all_matches:
            return 0.0
        
        # Use highest confidence from matches
        return max(p.confidence for p in all_matches)
    
    @property
    def best_system_type(self) -> SystemType:
        """Most likely system type based on matches."""
        # Block matches are more specific
        if self.block_matches:
            return max(self.block_matches, key=lambda p: p.confidence).system_type
        if self.layer_matches:
            return max(self.layer_matches, key=lambda p: p.confidence).system_type
        return SystemType.UNKNOWN
    
    @property
    def best_device_type(self) -> DeviceType:
        """Most likely device type based on matches."""
        if self.block_matches:
            return max(self.block_matches, key=lambda p: p.confidence).device_type
        if self.layer_matches:
            return max(self.layer_matches, key=lambda p: p.confidence).device_type
        return DeviceType.UNKNOWN


class DeviceDetector:
    """
    Detect and classify devices from CAD document.
    
    Example:
        detector = DeviceDetector()
        devices = detector.extract_from_dxf(doc)
        
        for device in devices:
            print(f"{device.name}: {device.system_type.value}")
    """
    
    def __init__(
        self,
        layer_patterns: Optional[List[DevicePattern]] = None,
        block_patterns: Optional[List[DevicePattern]] = None,
        exclude_patterns: Optional[List[str]] = None,
        min_confidence: float = 0.5
    ):
        """
        Initialize detector with patterns.
        
        Args:
            layer_patterns: Custom layer patterns (or use defaults)
            block_patterns: Custom block patterns (or use defaults)
            exclude_patterns: Patterns to exclude
            min_confidence: Minimum confidence to include device
        """
        self.layer_patterns = layer_patterns or LAYER_PATTERNS
        self.block_patterns = block_patterns or BLOCK_PATTERNS
        self.exclude_patterns = exclude_patterns or EXCLUDE_PATTERNS
        self.min_confidence = min_confidence
        
        # Compile exclude patterns for efficiency
        self._exclude_compiled = [
            re.compile(p) for p in self.exclude_patterns
        ]
    
    def _is_excluded(self, block_name: str) -> bool:
        """Check if block should be excluded."""
        return any(p.match(block_name) for p in self._exclude_compiled)
    
    def _match_patterns(
        self, 
        text: str, 
        patterns: List[DevicePattern]
    ) -> List[DevicePattern]:
        """Find all matching patterns for text."""
        matches = []
        for pattern in patterns:
            if re.match(pattern.pattern, text):
                matches.append(pattern)
        return matches
    
    def classify_block(self, block_name: str, layer: str) -> DeviceMatch:
        """
        Classify a block by name and layer.
        
        Returns DeviceMatch with confidence and type info.
        """
        layer_matches = self._match_patterns(layer, self.layer_patterns)
        block_matches = self._match_patterns(block_name, self.block_patterns)
        
        device = Device(
            block_name=block_name,
            layer=layer,
            cad_x=0,
            cad_y=0
        )
        
        match = DeviceMatch(
            device=device,
            layer_matches=layer_matches,
            block_matches=block_matches
        )
        
        # Apply classification
        device.system_type = match.best_system_type
        device.device_type = match.best_device_type
        device.detection_confidence = match.confidence
        device.matched_patterns = [
            p.pattern for p in (layer_matches + block_matches)
        ]
        
        return match
    
    def extract_from_dxf(self, doc) -> List[Device]:
        """
        Extract all devices from a DXF document.
        
        Args:
            doc: ezdxf document
            
        Returns:
            List of detected devices
        """
        msp = doc.modelspace()
        devices = []
        
        for entity in msp.query("INSERT"):
            block_name = entity.dxf.name
            layer = entity.dxf.layer
            
            # Skip excluded blocks
            if self._is_excluded(block_name):
                continue
            
            # Classify
            match = self.classify_block(block_name, layer)
            
            # Skip low confidence
            if match.confidence < self.min_confidence:
                continue
            
            # Get position
            device = match.device
            device.cad_x = entity.dxf.insert.x
            device.cad_y = entity.dxf.insert.y
            
            # Get attributes
            if hasattr(entity, 'attribs'):
                for attrib in entity.attribs:
                    tag = attrib.dxf.tag
                    text = attrib.dxf.text
                    if tag and text and text.strip():
                        device.attributes[tag.upper()] = text.strip()
            
            devices.append(device)
        
        return devices
    
    def extract_from_file(self, dxf_path: Path) -> List[Device]:
        """
        Extract devices from a DXF file.
        
        Args:
            dxf_path: Path to DXF file
            
        Returns:
            List of detected devices
        """
        import ezdxf
        doc = ezdxf.readfile(str(dxf_path))
        return self.extract_from_dxf(doc)
    
    def generate_report(self, doc) -> Dict:
        """
        Generate detection report showing what was found.
        
        Useful for debugging detection patterns.
        """
        msp = doc.modelspace()
        
        all_blocks = {}
        all_layers = set()
        detected = []
        excluded = []
        unmatched = []
        
        for entity in msp.query("INSERT"):
            block_name = entity.dxf.name
            layer = entity.dxf.layer
            
            all_layers.add(layer)
            
            if block_name not in all_blocks:
                all_blocks[block_name] = {"count": 0, "layers": set()}
            all_blocks[block_name]["count"] += 1
            all_blocks[block_name]["layers"].add(layer)
            
            if self._is_excluded(block_name):
                excluded.append(block_name)
                continue
            
            match = self.classify_block(block_name, layer)
            
            if match.confidence >= self.min_confidence:
                detected.append({
                    "block": block_name,
                    "layer": layer,
                    "system": match.best_system_type.value,
                    "type": match.best_device_type.value,
                    "confidence": match.confidence
                })
            else:
                unmatched.append({
                    "block": block_name,
                    "layer": layer,
                    "confidence": match.confidence
                })
        
        return {
            "total_blocks": len(all_blocks),
            "total_inserts": sum(b["count"] for b in all_blocks.values()),
            "layers": sorted(all_layers),
            "detected_count": len(detected),
            "excluded_count": len(set(excluded)),
            "unmatched_count": len(unmatched),
            "detected": detected,
            "unmatched": unmatched[:50],  # Limit output
            "blocks": {
                k: {"count": v["count"], "layers": list(v["layers"])} 
                for k, v in sorted(all_blocks.items())
            }
        }
