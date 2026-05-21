"""
MAXILLM API Routes

Endpoints for predictive intelligence and continuous model training.
"""
from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any

from forgesight.autodesign.maxillm_engine import maxillm_engine, TrainingFeedback
from apps.api.auth import get_current_user, WalmartUser

router = APIRouter(prefix="/api/v1/maxillm", tags=["maxillm"])

@router.post("/train", response_model=Dict[str, str])
def submit_training_feedback(
    feedback: TrainingFeedback,
    user: WalmartUser = Depends(get_current_user)
):
    """
    Submit human-in-the-loop feedback to train MAXILLM.
    This makes the AI smarter over time.
    """
    # Override user ID with authenticated user
    feedback.user_id = user.email
    
    record_id = maxillm_engine.record_feedback(feedback)
    return {"status": "success", "message": "Feedback ingested for MAXILLM training.", "record_id": record_id}

@router.get("/stats", response_model=Dict[str, Any])
def get_model_stats():
    """
    Get the current training volume and intelligence metrics for MAXILLM.
    """
    return maxillm_engine.get_training_stats()

@router.post("/predict")
def get_prediction(
    floor_plan: Dict[str, Any],
    constraints: Dict[str, Any] = {},
    user: WalmartUser = Depends(get_current_user)
):
    """
    Get a design prediction from the continuously learning MAXILLM model.
    """
    return maxillm_engine.predict_placement(floor_plan, constraints)
