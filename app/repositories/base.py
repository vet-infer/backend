from typing import Generic, TypeVar
from app.core.config import settings

from sqlalchemy.orm import Session

ModelT = TypeVar("ModelT")


class BaseRepository(Generic[ModelT]):
    model: type[ModelT]

    def __init__(self, db: Session):
        self.db = db

    def get(self, entity_id: int) -> ModelT | None:
        entity = self.db.get(self.model, entity_id)
        if entity and hasattr(entity, "is_active") and not entity.is_active:
            return None
        return entity

    def list(self, skip: int = 0, limit: int = settings.default_page_size) -> list[ModelT]:
        query = self.db.query(self.model)
        if hasattr(self.model, "is_active"):
            query = query.filter(self.model.is_active == True)
        return query.offset(skip).limit(limit).all()

    def add(self, entity: ModelT) -> ModelT:
        self.db.add(entity)
        self.db.commit()
        self.db.refresh(entity)
        return entity

    def delete(self, entity: ModelT) -> None:
        if hasattr(entity, "is_active"):
            entity.is_active = False
            self.db.commit()
        else:
            self.db.delete(entity)
            self.db.commit()


