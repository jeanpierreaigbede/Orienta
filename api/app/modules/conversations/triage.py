"""Processing of a patient message (TDR section 7)."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import audit
from app.config import get_settings
from app.errors import AppError
from app.llm import SYSTEM_PROMPT_FR, ChatModel, LLMUnavailable, TriageOutput, ask
from app.models import (
    CallbackRequest,
    CallbackStatus,
    Conversation,
    ConversationStatus,
    MessageSender,
    OrientationLevel,
    User,
)
from app.repository import add_message, message_text
from app.security import now

FORCE_ORIENT_FR = (
    "Tu as posé le nombre maximal de questions. Donne maintenant l'orientation finale : "
    "decision doit valoir \"ORIENT\" avec un orientationLevel."
)


def _build_messages(db: Session, conversation: Conversation, new_text: str) -> list[dict]:
    settings = get_settings()
    messages = [{"role": "system", "content": SYSTEM_PROMPT_FR.replace("{max_follow_up}", str(settings.triage_max_follow_up_questions))}]
    for m in conversation.messages:
        messages.append({"role": "user" if m.sender == MessageSender.PATIENT else "assistant", "content": message_text(db, conversation, m)})
    messages.append({"role": "user", "content": new_text})
    return messages


def _red_flag(text: str) -> bool:
    keywords = [k.strip().lower() for k in get_settings().triage_red_flag_keywords.split(",") if k.strip()]
    return any(k in text.lower() for k in keywords)


def process_patient_message(db: Session, model: ChatModel, conversation: Conversation, patient: User, text: str) -> TriageOutput:
    settings = get_settings()
    # Serialize two messages sent at the same time on the same conversation.
    db.execute(select(Conversation.id).where(Conversation.id == conversation.id).with_for_update())
    db.refresh(conversation)
    if conversation.status != ConversationStatus.IN_PROGRESS:
        raise AppError(409, "CONVERSATION_CLOSED", "This conversation is closed.")

    messages = _build_messages(db, conversation, text)
    try:
        output = ask(model, messages)
        if output.decision == "ASK_FOLLOW_UP" and conversation.follow_up_count >= settings.triage_max_follow_up_questions:
            output = ask(model, messages + [{"role": "system", "content": FORCE_ORIENT_FR}])
            if output.decision != "ORIENT":
                # Conservative default, to be validated by a health professional (TDR section 16).
                output = TriageOutput(reply=output.reply, decision="ORIENT", orientationLevel="CONSULTATION_48H")
    except LLMUnavailable as exc:
        db.rollback()
        raise AppError(503, "LLM_UNAVAILABLE", "The assistant is temporarily unavailable. Please try again.") from exc

    if _red_flag(text):
        output = TriageOutput(reply=output.reply, decision="ORIENT", orientationLevel="EMERGENCY")

    add_message(db, conversation, MessageSender.PATIENT, text)
    add_message(db, conversation, MessageSender.ASSISTANT, output.reply)
    conversation.last_message_at = now()
    if output.decision == "ASK_FOLLOW_UP":
        conversation.follow_up_count += 1
    else:
        conversation.status = ConversationStatus.ORIENTED
        conversation.orientation_level = OrientationLevel(output.orientationLevel)
        conversation.oriented_at = now()
        audit.record(db, "conversation.oriented", "conversation", conversation.id, actor=patient,
                     metadata={"orientationLevel": output.orientationLevel})
        if conversation.orientation_level == OrientationLevel.EMERGENCY:
            db.add(CallbackRequest(conversation_id=conversation.id, status=CallbackStatus.PENDING))
    db.commit()
    return output
