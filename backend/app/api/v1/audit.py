"""
Audit API Router

Provides endpoints for:
- Verifying cryptographic audit chains
- Managing pending AI-proposed actions (approve/reject)
- Viewing audit history

The "Four-Eyes Guardrail" - AI proposes, Human approves.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import datetime

from app.database import get_db
from app.utils.auth import get_current_user
from app.models.user import User

router = APIRouter()


# ============================================
# Response Models
# ============================================

class AuditVerificationResult(BaseModel):
    is_valid: bool
    total_entries: int
    broken_at_sequence: Optional[int] = None
    error_message: Optional[str] = None


class AuditEntry(BaseModel):
    audit_id: str
    operation: str
    changed_at: datetime
    changed_by: Optional[str] = None
    changed_by_type: Optional[str] = None
    changed_fields: Optional[List[str]] = None
    old_values: Optional[dict] = None
    new_values: Optional[dict] = None
    record_sequence: int
    chain_valid: bool


class PendingAction(BaseModel):
    id: str
    action_type: str
    target_table: str
    target_id: Optional[str] = None
    payload: dict
    confidence: float
    reasoning: Optional[str] = None
    source_document_id: Optional[str] = None
    source_text: Optional[str] = None
    case_id: Optional[str] = None
    status: str
    created_at: datetime
    expires_at: datetime


class ApproveRequest(BaseModel):
    review_notes: Optional[str] = None


class RejectRequest(BaseModel):
    rejection_reason: str


# ============================================
# Audit Chain Verification
# ============================================

@router.get("/verify/{record_id}", response_model=AuditVerificationResult)
async def verify_audit_chain(
    record_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Verify the cryptographic integrity of an audit chain for a record.

    The audit system uses SHA-256 hash chaining to create a tamper-evident
    trail. This endpoint verifies that no entries have been modified.
    """
    try:
        # Call the database function to verify the chain
        result = db.execute(
            text("SELECT * FROM verify_audit_chain(:record_id)"),
            {"record_id": record_id}
        ).fetchone()

        if result is None:
            # No audit entries for this record
            return AuditVerificationResult(
                is_valid=True,
                total_entries=0,
                broken_at_sequence=None,
                error_message=None
            )

        return AuditVerificationResult(
            is_valid=result.is_valid,
            total_entries=result.total_entries,
            broken_at_sequence=result.broken_at_sequence,
            error_message=result.error_message
        )

    except Exception as e:
        # If the function doesn't exist, return a graceful error
        if "does not exist" in str(e):
            raise HTTPException(
                status_code=501,
                detail="Audit verification not available. Database migration may be needed."
            )
        raise HTTPException(status_code=500, detail=f"Verification failed: {str(e)}")


@router.get("/history/{record_id}", response_model=List[AuditEntry])
async def get_record_history(
    record_id: str,
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get the full audit history for a record, including chain validity status.
    """
    try:
        results = db.execute(
            text("SELECT * FROM get_record_history(:record_id, :limit)"),
            {"record_id": record_id, "limit": limit}
        ).fetchall()

        return [
            AuditEntry(
                audit_id=str(row.audit_id),
                operation=row.operation,
                changed_at=row.changed_at,
                changed_by=str(row.changed_by) if row.changed_by else None,
                changed_by_type=row.changed_by_type,
                changed_fields=row.changed_fields,
                old_values=row.old_values,
                new_values=row.new_values,
                record_sequence=row.record_sequence,
                chain_valid=row.chain_valid
            )
            for row in results
        ]

    except Exception as e:
        if "does not exist" in str(e):
            raise HTTPException(
                status_code=501,
                detail="Audit history not available. Database migration may be needed."
            )
        raise HTTPException(status_code=500, detail=f"Failed to get history: {str(e)}")


# ============================================
# Pending Actions (AI Staging Area)
# ============================================

@router.get("/pending/count")
async def get_pending_actions_count(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get the count of pending AI-proposed actions awaiting approval.
    Used for the "Pending Approvals" indicator in the UI.
    """
    try:
        result = db.execute(
            text("""
                SELECT COUNT(*) as count
                FROM pending_docket_actions
                WHERE user_id = :user_id
                  AND status = 'pending'
                  AND expires_at > NOW()
            """),
            {"user_id": str(current_user.id)}
        ).fetchone()

        return {"count": result.count if result else 0}

    except Exception as e:
        if "does not exist" in str(e):
            # Table doesn't exist yet - return 0
            return {"count": 0}
        raise HTTPException(status_code=500, detail=f"Failed to get count: {str(e)}")


@router.get("/pending", response_model=List[PendingAction])
async def get_pending_actions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all pending AI-proposed actions for the current user.
    """
    try:
        results = db.execute(
            text("""
                SELECT id, action_type, target_table, target_id, payload,
                       confidence, reasoning, source_document_id, source_text,
                       case_id, status, created_at, expires_at
                FROM pending_docket_actions
                WHERE user_id = :user_id
                  AND status = 'pending'
                  AND expires_at > NOW()
                ORDER BY created_at DESC
            """),
            {"user_id": str(current_user.id)}
        ).fetchall()

        return [
            PendingAction(
                id=str(row.id),
                action_type=row.action_type,
                target_table=row.target_table,
                target_id=str(row.target_id) if row.target_id else None,
                payload=row.payload or {},
                confidence=float(row.confidence),
                reasoning=row.reasoning,
                source_document_id=str(row.source_document_id) if row.source_document_id else None,
                source_text=row.source_text,
                case_id=str(row.case_id) if row.case_id else None,
                status=row.status,
                created_at=row.created_at,
                expires_at=row.expires_at
            )
            for row in results
        ]

    except Exception as e:
        if "does not exist" in str(e):
            return []
        raise HTTPException(status_code=500, detail=f"Failed to get pending actions: {str(e)}")


@router.post("/actions/{action_id}/approve")
async def approve_pending_action(
    action_id: str,
    request: ApproveRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Approve a pending AI-proposed action, committing it to the live tables.

    This is the human verification step in the "Four-Eyes Guardrail" pattern.
    """
    try:
        # First verify the action belongs to this user and is pending
        action = db.execute(
            text("""
                SELECT * FROM pending_docket_actions
                WHERE id = :action_id
                  AND user_id = :user_id
                  AND status = 'pending'
                FOR UPDATE
            """),
            {"action_id": action_id, "user_id": str(current_user.id)}
        ).fetchone()

        if not action:
            raise HTTPException(
                status_code=404,
                detail="Pending action not found, already processed, or access denied"
            )

        # Mark as approved
        db.execute(
            text("""
                UPDATE pending_docket_actions
                SET status = 'approved',
                    reviewed_by = :user_id,
                    reviewed_at = NOW(),
                    review_notes = :notes
                WHERE id = :action_id
            """),
            {
                "action_id": action_id,
                "user_id": str(current_user.id),
                "notes": request.review_notes
            }
        )

        # Execute the action based on type
        new_id = None
        try:
            if action.action_type == 'CREATE_DEADLINE':
                result = db.execute(
                    text("""
                        INSERT INTO deadlines (
                            id, user_id, case_id, title, description,
                            deadline_date, deadline_type, applicable_rule,
                            priority, confidence_score, confidence_level,
                            verification_status, created_at, updated_at
                        ) VALUES (
                            uuid_generate_v4(), :user_id, :case_id, :title, :description,
                            :deadline_date, :deadline_type, :applicable_rule,
                            :priority, :confidence, :confidence_level,
                            'verified', NOW(), NOW()
                        )
                        RETURNING id
                    """),
                    {
                        "user_id": str(current_user.id),
                        "case_id": action.payload.get('case_id', str(action.case_id)),
                        "title": action.payload.get('title'),
                        "description": action.payload.get('description'),
                        "deadline_date": action.payload.get('deadline_date'),
                        "deadline_type": action.payload.get('deadline_type'),
                        "applicable_rule": action.payload.get('applicable_rule'),
                        "priority": action.payload.get('priority', 'standard'),
                        "confidence": action.confidence,
                        "confidence_level": 'high' if action.confidence >= 0.9 else 'medium' if action.confidence >= 0.7 else 'low'
                    }
                )
                new_id = result.fetchone().id

            elif action.action_type == 'CREATE_TRIGGER':
                result = db.execute(
                    text("""
                        INSERT INTO trigger_events (
                            id, user_id, case_id, trigger_type, trigger_date,
                            description, source_document_id, source_type,
                            created_at, updated_at
                        ) VALUES (
                            uuid_generate_v4(), :user_id, :case_id, :trigger_type, :trigger_date,
                            :description, :source_document_id, 'ai_extracted',
                            NOW(), NOW()
                        )
                        RETURNING id
                    """),
                    {
                        "user_id": str(current_user.id),
                        "case_id": action.payload.get('case_id', str(action.case_id)),
                        "trigger_type": action.payload.get('trigger_type'),
                        "trigger_date": action.payload.get('trigger_date'),
                        "description": action.payload.get('description'),
                        "source_document_id": str(action.source_document_id) if action.source_document_id else None
                    }
                )
                new_id = result.fetchone().id
            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"Unsupported action type: {action.action_type}"
                )

            # Mark as committed
            db.execute(
                text("""
                    UPDATE pending_docket_actions
                    SET status = 'committed',
                        committed_record_id = :new_id
                    WHERE id = :action_id
                """),
                {"action_id": action_id, "new_id": new_id}
            )

            db.commit()

            return {
                "success": True,
                "message": "Action approved and committed",
                "committed_record_id": str(new_id)
            }

        except Exception as commit_error:
            db.rollback()
            # Mark as error
            db.execute(
                text("""
                    UPDATE pending_docket_actions
                    SET status = 'error',
                        commit_error = :error
                    WHERE id = :action_id
                """),
                {"action_id": action_id, "error": str(commit_error)}
            )
            db.commit()
            raise HTTPException(status_code=500, detail=f"Commit failed: {str(commit_error)}")

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Approval failed: {str(e)}")


@router.post("/actions/{action_id}/reject")
async def reject_pending_action(
    action_id: str,
    request: RejectRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Reject a pending AI-proposed action.

    Requires a rejection reason for audit purposes.
    """
    if not request.rejection_reason or not request.rejection_reason.strip():
        raise HTTPException(status_code=400, detail="Rejection reason is required")

    try:
        result = db.execute(
            text("""
                UPDATE pending_docket_actions
                SET status = 'rejected',
                    reviewed_by = :user_id,
                    reviewed_at = NOW(),
                    review_notes = :reason
                WHERE id = :action_id
                  AND user_id = :user_id
                  AND status = 'pending'
                RETURNING id
            """),
            {
                "action_id": action_id,
                "user_id": str(current_user.id),
                "reason": request.rejection_reason
            }
        )

        if result.fetchone() is None:
            raise HTTPException(
                status_code=404,
                detail="Pending action not found or already processed"
            )

        db.commit()

        return {
            "success": True,
            "message": "Action rejected"
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Rejection failed: {str(e)}")
