from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import delete, func, select
from sqlalchemy.orm import selectinload

from ..models import ConversationRecord, MessageRecord


class ConversationRepository:
    def __init__(self, session):
        self.session = session

    def list_for_owner(self, owner_id: str) -> list[ConversationRecord]:
        statement = select(ConversationRecord).where(ConversationRecord.owner_id == owner_id).order_by(ConversationRecord.updated_at.desc())
        return list(self.session.scalars(statement))

    def get_for_owner(self, conversation_id: str, owner_id: str) -> ConversationRecord | None:
        statement = select(ConversationRecord).options(selectinload(ConversationRecord.messages)).where(
            ConversationRecord.id == conversation_id, ConversationRecord.owner_id == owner_id
        )
        return self.session.scalar(statement)

    def create(self, owner_id: str, title: str = "Nouvelle conversation") -> ConversationRecord:
        record = ConversationRecord(id=f"c-{uuid4().hex}", owner_id=owner_id, title=title.strip() or "Nouvelle conversation")
        self.session.add(record)
        self.session.flush()
        return record

    def delete(self, conversation_id: str, owner_id: str) -> bool:
        result = self.session.execute(delete(ConversationRecord).where(
            ConversationRecord.id == conversation_id, ConversationRecord.owner_id == owner_id
        ))
        return bool(result.rowcount)

    def append_exchange(self, conversation: ConversationRecord, question: str, answer: str, sources: list[dict]) -> ConversationRecord:
        next_position = self.session.scalar(select(func.coalesce(func.max(MessageRecord.position), -1)).where(
            MessageRecord.conversation_id == conversation.id
        ))
        now = datetime.now(timezone.utc)
        self.session.add_all([
            MessageRecord(id=f"m-{uuid4().hex}", conversation_id=conversation.id, position=next_position + 1,
                          role="user", content=question, sources=[], status="COMPLETE", created_at=now),
            MessageRecord(id=f"m-{uuid4().hex}", conversation_id=conversation.id, position=next_position + 2,
                          role="assistant", content=answer, sources=sources, status="COMPLETE", created_at=now),
        ])
        if conversation.title == "Nouvelle conversation":
            conversation.title = question[:80]
        conversation.updated_at = now
        self.session.flush()
        self.session.expire(conversation, ["messages"])
        return conversation
