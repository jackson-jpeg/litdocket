"""
Workload Analysis API
Intelligent calendar workload management and optimization
"""
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel, Field

from app.database import get_db
from app.models.user import User
from app.utils.auth import get_current_user
from app.services.workload_optimizer import workload_optimizer
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/analysis")
async def analyze_workload(
    days_ahead: int = Query(default=60, ge=7, le=180, description="Days to analyze ahead"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Analyze attorney's calendar workload and identify saturation risks

    Returns:
    - High-risk days with excessive deadlines
    - Burnout alerts (consecutive saturated days)
    - AI-powered rebalancing suggestions
    - Workload heatmap data for visualization

    Use this to:
    - Prevent deadline clustering
    - Optimize workload distribution
    - Identify burnout risk periods
    - Get AI suggestions for rescheduling
    """

    try:
        analysis = await workload_optimizer.analyze_calendar_saturation(
            user_id=str(current_user.id),
            db=db,
            days_ahead=days_ahead
        )

        return {
            "success": True,
            "data": analysis,
            "message": f"Analyzed workload for next {days_ahead} days"
        }

    except Exception as e:
        logger.error(f"Workload analysis error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@router.get("/heatmap")
async def get_workload_heatmap(
    days_ahead: int = Query(default=60, ge=7, le=180),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get workload heatmap data for calendar visualization

    Returns a day-by-day breakdown of workload intensity:
    - risk_score: Numeric intensity (0-30+)
    - deadline_count: Number of deadlines
    - intensity: Categorical level (low/medium/high/very_high/extreme)

    Perfect for:
    - Color-coding calendar days
    - GitHub contribution graph-style visualizations
    - Quick visual workload scanning
    """

    try:
        analysis = await workload_optimizer.analyze_calendar_saturation(
            user_id=str(current_user.id),
            db=db,
            days_ahead=days_ahead
        )

        # Return just the heatmap data
        return {
            "success": True,
            "data": {
                "heatmap": analysis['workload_heatmap'],
                "statistics": analysis['statistics']
            }
        }

    except Exception as e:
        logger.error(f"Heatmap generation error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Heatmap generation failed: {str(e)}")


@router.get("/suggestions")
async def get_rebalancing_suggestions(
    days_ahead: int = Query(default=60, ge=7, le=180),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get AI-powered deadline rebalancing suggestions

    Analyzes high-risk days and provides specific recommendations:
    - Which deadlines to move
    - Optimal new dates
    - Reasoning for each suggestion

    Example response:
    {
        "suggestions": [
            {
                "date": "2026-02-15",
                "risk_score": 25.0,
                "ai_recommendations": [
                    {
                        "deadline_title": "Expert Witness List",
                        "move_to_date": "2026-02-13",
                        "reason": "Move to day with lower workload, maintains 2-day buffer before trial"
                    }
                ],
                "summary": "Redistribute 3 lower-priority tasks to adjacent days..."
            }
        ]
    }
    """

    try:
        analysis = await workload_optimizer.analyze_calendar_saturation(
            user_id=str(current_user.id),
            db=db,
            days_ahead=days_ahead
        )

        return {
            "success": True,
            "data": {
                "suggestions": analysis['ai_suggestions'],
                "risk_days_count": len(analysis['risk_days']),
                "burnout_alerts": analysis['burnout_alerts']
            },
            "message": "AI suggestions generated successfully"
        }

    except Exception as e:
        logger.error(f"Suggestion generation error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate suggestions: {str(e)}")
