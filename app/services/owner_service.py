from app.core.config import settings
from app.core.exceptions import AppException, ConflictError, NotFoundError
from app.repositories.owner_repository import OwnerRepository
from app.schemas.owner import OwnerCreate, OwnerUpdate


class OwnerService:
    def __init__(self, repository: OwnerRepository):
        self.repository = repository

    def create_owner(self, schema: OwnerCreate):
        if schema.document_type and schema.document_number:
            existing = self.repository.get_by_document(schema.document_type.value, schema.document_number)
            if existing:
                raise self._duplicate_document_error(
                    schema.document_type.value, schema.document_number, existing.is_active
                )
        return self.repository.create(schema.model_dump())

    def get_owner(self, owner_id: int):
        owner = self.repository.get_by_id(owner_id)
        if not owner:
            raise NotFoundError("Dueno no encontrado")
        return owner

    def get_owner_detail(self, owner_id: int):
        owner = self.repository.get_any(owner_id)
        if not owner:
            raise NotFoundError("Dueno no encontrado")
        return owner

    def list_owners(self, skip: int = 0, limit: int = settings.default_page_size):
        return self.repository.list(skip=skip, limit=limit)

    def delete_owner(self, owner_id: int):
        owner = self.get_owner(owner_id)
        if owner.patients:
            raise AppException("No se puede eliminar un dueno con pacientes registrados")
        return self.repository.delete(owner_id)

    def update_owner(self, owner_id: int, schema: OwnerUpdate):
        owner = self.get_owner(owner_id)
        if schema.document_type and schema.document_number:
            changed = (
                schema.document_type.value != owner.document_type
                or schema.document_number != owner.document_number
            )
            if changed:
                existing = self.repository.get_by_document(schema.document_type.value, schema.document_number)
                if existing and existing.id != owner_id:
                    raise self._duplicate_document_error(
                        schema.document_type.value, schema.document_number, existing.is_active
                    )
        return self.repository.update_by_id(owner_id, schema.model_dump(exclude_unset=True))

    @staticmethod
    def _duplicate_document_error(document_type: str, document_number: str, is_active: bool) -> ConflictError:
        message = f"Ya existe un propietario registrado con {document_type} {document_number}"
        if not is_active:
            message += " (el registro existente esta inactivo)"
        return ConflictError(message)
