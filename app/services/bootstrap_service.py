from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import get_password_hash
from app.models.species import Species
from app.models.breed import Breed
from app.models.role import Role
from app.models.user import User


def bootstrap_reference_data(db: Session) -> None:
    roles = {
        "admin": "Administrador del sistema",
        "veterinario": "Medico veterinario",
        "evaluador": "Asesor o evaluador academico",
    }
    for name, description in roles.items():
        if db.query(Role).filter(Role.name == name).first() is None:
            db.add(Role(name=name, description=description))

    for species_name in ["Perro", "Gato"]:
        if db.query(Species).filter(Species.name == species_name).first() is None:
            db.add(Species(name=species_name))

    db.commit()

    for species_name, breed_names in [
        ("Perro", ["Mestizo", "Poodle", "Schnauzer", "Yorkshire Terrier", "Chihuahua"]),
        ("Gato", ["Mestizo", "Siamés", "Persa", "Maine Coon"])
    ]:
        species = db.query(Species).filter(Species.name == species_name).first()
        if species:
            for breed_name in breed_names:
                if db.query(Breed).filter(Breed.species_id == species.id, Breed.name == breed_name).first() is None:
                    db.add(Breed(species_id=species.id, name=breed_name))

    db.commit()


    admin_role = db.query(Role).filter(Role.name == "admin").first()
    if settings.bootstrap_admin_email and settings.bootstrap_admin_password and admin_role:
        existing_admin = db.query(User).filter(User.email == settings.bootstrap_admin_email).first()
        if existing_admin is None:
            db.add(
                User(
                    full_name="Administrador",
                    email=settings.bootstrap_admin_email,
                    password_hash=get_password_hash(settings.bootstrap_admin_password),
                    role_id=admin_role.id,
                )
            )
            db.commit()
