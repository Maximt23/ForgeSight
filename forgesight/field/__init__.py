"""
ForgeSight Field - Mobile/VR Site Survey Application

Capture real-world device locations with mobile devices and VIVE XR.

Status: 🟡 Beta

Usage:
    from forgesight.field import SurveyCapture, VIVECalibration
    
    # Mobile survey
    survey = SurveyCapture(site_id="uuid")
    survey.add_device(x=45.2, y=32.1, device_type="dome_camera")
    survey.add_photo(device_id="...", image_path="photo.jpg")
    survey.sync()
    
    # VR calibration
    calibration = VIVECalibration()
    calibration.add_point(vr_pos=(1.2, 0, 3.4), site_pos=(45.2, 32.1))
    calibration.compute_transform()
"""

from dataclasses import dataclass, field
from typing import List, Optional, Tuple
from datetime import datetime
from uuid import uuid4


@dataclass
class SurveyDevice:
    """A device marked during survey."""
    id: str = field(default_factory=lambda: str(uuid4()))
    device_type: str = ""
    x: float = 0.0
    y: float = 0.0
    notes: str = ""
    photo_urls: List[str] = field(default_factory=list)
    captured_at: datetime = field(default_factory=datetime.utcnow)
    captured_by: str = ""


@dataclass
class Survey:
    """A site survey session."""
    id: str = field(default_factory=lambda: str(uuid4()))
    site_id: str = ""
    surveyor: str = ""
    devices: List[SurveyDevice] = field(default_factory=list)
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    synced: bool = False


class SurveyCapture:
    """Capture devices during a site survey."""
    
    def __init__(self, site_id: str, surveyor: str = ""):
        self.survey = Survey(site_id=site_id, surveyor=surveyor)
        self._offline_queue = []
    
    def add_device(
        self,
        x: float,
        y: float,
        device_type: str,
        notes: str = ""
    ) -> SurveyDevice:
        """Mark a device at a location."""
        device = SurveyDevice(
            device_type=device_type,
            x=x,
            y=y,
            notes=notes,
            captured_by=self.survey.surveyor
        )
        self.survey.devices.append(device)
        return device
    
    def add_photo(self, device_id: str, image_path: str):
        """Add a photo to a device."""
        for device in self.survey.devices:
            if device.id == device_id:
                device.photo_urls.append(image_path)
                return
        raise ValueError(f"Device not found: {device_id}")
    
    def complete(self):
        """Mark survey as complete."""
        self.survey.completed_at = datetime.utcnow()
    
    def sync(self) -> bool:
        """Sync survey to cloud."""
        # TODO: Implement cloud sync
        self.survey.synced = True
        return True
    
    def to_dict(self) -> dict:
        """Export survey as dictionary."""
        return {
            "id": self.survey.id,
            "site_id": self.survey.site_id,
            "surveyor": self.survey.surveyor,
            "devices": [
                {
                    "id": d.id,
                    "device_type": d.device_type,
                    "x": d.x,
                    "y": d.y,
                    "notes": d.notes,
                    "photo_urls": d.photo_urls,
                }
                for d in self.survey.devices
            ],
            "started_at": self.survey.started_at.isoformat(),
            "completed_at": self.survey.completed_at.isoformat() if self.survey.completed_at else None,
        }


class VIVECalibration:
    """Calibrate VIVE XR space to floor plan coordinates."""
    
    def __init__(self):
        self.calibration_points: List[Tuple[Tuple[float, float, float], Tuple[float, float]]] = []
        self.transform_matrix = None
    
    def add_point(
        self,
        vr_pos: Tuple[float, float, float],
        site_pos: Tuple[float, float]
    ):
        """Add a calibration point."""
        self.calibration_points.append((vr_pos, site_pos))
    
    def compute_transform(self):
        """Compute transformation matrix from calibration points."""
        if len(self.calibration_points) < 3:
            raise ValueError("Need at least 3 calibration points")
        
        # TODO: Implement affine transformation computation
        # For now, return identity-ish matrix
        self.transform_matrix = [
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0]
        ]
        return self.transform_matrix
    
    def transform(self, vr_pos: Tuple[float, float, float]) -> Tuple[float, float]:
        """Transform VR position to site coordinates."""
        if self.transform_matrix is None:
            self.compute_transform()
        
        # VR: x=left/right, y=up/down, z=forward/back
        # Site: x=horizontal, y=vertical (top-down view)
        x, y, z = vr_pos
        
        # Simple transform (use x and z, ignore y which is height)
        site_x = x * self.transform_matrix[0][0] + self.transform_matrix[0][2]
        site_y = z * self.transform_matrix[1][1] + self.transform_matrix[1][2]
        
        return (site_x, site_y)


__all__ = [
    "SurveyCapture",
    "SurveyDevice",
    "Survey",
    "VIVECalibration",
]
