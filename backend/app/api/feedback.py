import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, status

from app.api.deps import Svc
from app.auth import CurrentUser, ensure_client_access
from app.contracts.platform import Feedback, FeedbackRequest
from app.errors import not_found

router = APIRouter(tags=["feedback"])


@router.post("/feedback", response_model=Feedback, status_code=status.HTTP_201_CREATED)
async def post_feedback(body: FeedbackRequest, user: CurrentUser, svc: Svc) -> Feedback:
    insight = svc.store.insights.get(body.insight_id)
    if insight is None:
        raise not_found("Insight")
    ensure_client_access(user, insight.client_id)
    feedback = Feedback(
        **body.model_dump(),
        feedback_id=f"fb-{uuid.uuid4().hex[:12]}",
        user_id=user.user_id,
        trace_id=insight.trace_id,
        created_at=datetime.now(UTC),
    )
    await svc.store.add_feedback(feedback)
    return feedback
