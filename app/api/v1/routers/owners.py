from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.owner import OwnerCreate, OwnerOut, OwnerUpdate
from app.services.owner_service import OwnerService

router = APIRouter(prefix="/owners", tags=["Owners"])


@router.post("/", response_model=OwnerOut, status_code=status.HTTP_201_CREATED)
def create_owner(schema: OwnerCreate, db: Session = Depends(get_db)):
    return OwnerService(db).create_owner(schema)


@router.get("/", response_model=list[OwnerOut])
def get_owners(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return OwnerService(db).list_owners(skip, limit)


@router.get("/{owner_id}", response_model=OwnerOut)
def get_owner(owner_id: int, db: Session = Depends(get_db)):
    return OwnerService(db).get_owner(owner_id)


@router.put("/{owner_id}", response_model=OwnerOut)
def update_owner(owner_id: int, schema: OwnerUpdate, db: Session = Depends(get_db)):
    return OwnerService(db).update_owner(owner_id, schema)


@router.delete("/{owner_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_owner(owner_id: int, db: Session = Depends(get_db)):
    OwnerService(db).delete_owner(owner_id)
