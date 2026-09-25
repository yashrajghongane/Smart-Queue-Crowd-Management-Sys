from typing import Optional
from sqlalchemy.orm import Session
from app.models.models import Queue

class QueueRepository:
    def __init__(self, db: Session) -> None:
        self.db = db
    def find_by_id(self, queue_id: str) -> Optional[Queue]:
        return self.db.query(Queue).filter(Queue.id == queue_id).first()
