"""add bayesian inference support and data preservation

Revision ID: b2aeb44f214b
Revises: None
Create Date: 2026-05-20 04:03:58.348371
"""
from alembic import op
import sqlalchemy as sa


revision = 'b2aeb44f214b'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ==========================================
    # FASE 1: CREAR NUEVAS TABLAS RELACIONALES
    # ==========================================
    
    # 1. Crear tabla de dueños (owners)
    op.create_table(
        'owners',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('first_name', sa.String(length=120), nullable=False),
        sa.Column('last_name', sa.String(length=120), nullable=True),
        sa.Column('phone', sa.String(length=20), nullable=True),
        sa.Column('email', sa.String(length=160), nullable=True),
        sa.Column('address', sa.String(length=255), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_owners_email'), 'owners', ['email'], unique=True)
    op.create_index(op.f('ix_owners_id'), 'owners', ['id'], unique=False)

    # 2. Crear tabla de razas (breeds)
    op.create_table(
        'breeds',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('species_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=80), nullable=False),
        sa.ForeignKeyConstraint(['species_id'], ['species.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('species_id', 'name', name='uix_species_breed_name')
    )
    op.create_index(op.f('ix_breeds_id'), 'breeds', ['id'], unique=False)

    # 3. Crear tabla de probabilidades clínicas bayesianas (clinical_probabilities)
    op.create_table(
        'clinical_probabilities',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('disease_id', sa.Integer(), nullable=False),
        sa.Column('symptom_id', sa.Integer(), nullable=True),
        sa.Column('variable_id', sa.Integer(), nullable=True),
        sa.Column('expected_value', sa.String(length=100), nullable=True),
        sa.Column('probability_given_disease', sa.Float(), nullable=False),
        sa.Column('general_probability', sa.Float(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.ForeignKeyConstraint(['disease_id'], ['diseases.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['symptom_id'], ['symptoms.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['variable_id'], ['clinical_variables.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_clinical_probabilities_id'), 'clinical_probabilities', ['id'], unique=False)

    # ==================================================
    # FASE 2: COLUMNAS DE ADICION PROVISIONAL (NULLABLES)
    # ==================================================
    op.add_column('patients', sa.Column('owner_id', sa.Integer(), nullable=True))
    op.add_column('patients', sa.Column('breed_id', sa.Integer(), nullable=True))

    # Columnas complementarias para el soporte Bayesiano en Inferencia y Enfermedades
    op.add_column('diseases', sa.Column('base_probability', sa.Float(), nullable=True, server_default='0.20'))
    op.add_column('inference_results', sa.Column('probability', sa.Float(), nullable=True))
    op.add_column('inference_results', sa.Column('inference_method', sa.String(length=50), nullable=True))

    # ==================================================
    # FASE 3: MIGRACIÓN Y NORMALIZACIÓN DE DATA HISTÓRICA
    # ==================================================
    connection = op.get_bind()

    # 1. Migración de dueños: Extraer 'tutor_name' únicos de 'patients'
    # Usamos try-except por si la tabla está vacía o si las columnas no existen.
    try:
        raw_patients = connection.execute(
            sa.text("SELECT id, tutor_name, breed, species_id FROM patients")
        ).fetchall()
    except Exception:
        # En caso de que sea una instalación limpia sin tablas previas
        raw_patients = []

    inserted_owners = {}  # Mapeo: tutor_name -> owner_id
    inserted_breeds = {}  # Mapeo: (species_id, breed_name) -> breed_id

    for row in raw_patients:
        p_id = row[0]
        tutor_name = row[1] or "Propietario Desconocido"
        breed_name = row[2] or "Sin Definir"
        species_id = row[3]

        # Separación inteligente de Nombre y Apellido
        name_parts = tutor_name.strip().split(" ", 1)
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else ""

        # Evitar crear dueños duplicados en la misma migración
        if tutor_name not in inserted_owners:
            # Comprobar si ya existe en la base de datos de dueños para ser reentrante
            db_owner = connection.execute(
                sa.text("SELECT id FROM owners WHERE first_name = :fn AND last_name = :ln"),
                {"fn": first_name, "ln": last_name}
            ).fetchone()

            if db_owner:
                inserted_owners[tutor_name] = db_owner[0]
            else:
                res_owner = connection.execute(
                    sa.text(
                        "INSERT INTO owners (first_name, last_name, phone, email, address) "
                        "VALUES (:fn, :ln, NULL, NULL, NULL) RETURNING id"
                    ),
                    {"fn": first_name, "ln": last_name}
                ).fetchone()
                inserted_owners[tutor_name] = res_owner[0]

        owner_id = inserted_owners[tutor_name]

        # Normalización y poblamiento de razas
        breed_clean = breed_name.strip().title()
        breed_key = (species_id, breed_clean)

        if breed_key not in inserted_breeds:
            # Comprobar si la raza ya fue insertada físicamente en la BD
            db_breed = connection.execute(
                sa.text("SELECT id FROM breeds WHERE species_id = :sid AND name = :name"),
                {"sid": species_id, "name": breed_clean}
            ).fetchone()

            if db_breed:
                inserted_breeds[breed_key] = db_breed[0]
            else:
                res_breed = connection.execute(
                    sa.text("INSERT INTO breeds (species_id, name) VALUES (:sid, :name) RETURNING id"),
                    {"sid": species_id, "name": breed_clean}
                ).fetchone()
                inserted_breeds[breed_key] = res_breed[0]

        breed_id = inserted_breeds[breed_key]

        # Actualizar paciente con las llaves foráneas correctas
        connection.execute(
            sa.text("UPDATE patients SET owner_id = :oid, breed_id = :bid WHERE id = :pid"),
            {"oid": owner_id, "bid": breed_id, "pid": p_id}
        )

    # Si hay registros preexistentes que de alguna forma quedaron con owner_id NULL, resolvemos asignando un tutor genérico
    if raw_patients:
        connection.execute(
            sa.text(
                "INSERT INTO owners (id, first_name, last_name) VALUES (9999, 'Tutor', 'General') "
                "ON CONFLICT (id) DO NOTHING"
            )
        )
        connection.execute(
            sa.text("UPDATE patients SET owner_id = 9999 WHERE owner_id IS NULL")
        )

    # ==================================================
    # FASE 4: CONFIGURACIÓN DE CONSTRAINTS (FOREIGN KEYS)
    # ==================================================
    op.create_foreign_key('fk_patients_owner_id', 'patients', 'owners', ['owner_id'], ['id'])
    op.create_foreign_key('fk_patients_breed_id', 'patients', 'breeds', ['breed_id'], ['id'])

    # ==================================================
    # FASE 5: ENDURECER NOT NULL EN COLUMNAS PRINCIPALES
    # ==================================================
    # Primero asignamos un owner_id por defecto para registros nuevos si no existiera
    op.alter_column('patients', 'owner_id', existing_type=sa.Integer(), nullable=False)

    # ==================================================
    # FASE 6: REMOCIÓN DE COLUMNAS OBSOLETAS
    # ==================================================
    op.drop_column('patients', 'breed')
    op.drop_column('patients', 'tutor_name')


def downgrade() -> None:
    # Proceso inverso y seguro de downgrade para revertir los esquemas sin romper todo
    op.add_column('patients', sa.Column('tutor_name', sa.VARCHAR(length=120), nullable=True))
    op.add_column('patients', sa.Column('breed', sa.VARCHAR(length=80), nullable=True))

    connection = op.get_bind()

    # Re-poblar los campos de texto plano desde los datos relacionales antes de destruir
    try:
        connection.execute(
            sa.text(
                "UPDATE patients p "
                "SET tutor_name = CONCAT(o.first_name, ' ', COALESCE(o.last_name, '')), "
                "    breed = COALESCE(b.name, 'Mestizo') "
                "FROM owners o, breeds b "
                "WHERE p.owner_id = o.id AND p.breed_id = b.id"
            )
        )
    except Exception:
        pass

    # Hacer no-nulo el campo revertido si es crítico
    op.alter_column('patients', 'tutor_name', existing_type=sa.VARCHAR(length=120), nullable=False)

    # Eliminar llaves foráneas y columnas nuevas
    op.drop_constraint('fk_patients_breed_id', 'patients', type_='foreignkey')
    op.drop_constraint('fk_patients_owner_id', 'patients', type_='foreignkey')
    op.drop_column('patients', 'breed_id')
    op.drop_column('patients', 'owner_id')
    op.drop_column('inference_results', 'inference_method')
    op.drop_column('inference_results', 'probability')
    op.drop_column('diseases', 'base_probability')

    # Eliminar tablas de soporte creadas en upgrade
    op.drop_index(op.f('ix_clinical_probabilities_id'), table_name='clinical_probabilities')
    op.drop_table('clinical_probabilities')
    op.drop_index(op.f('ix_breeds_id'), table_name='breeds')
    op.drop_table('breeds')
    op.drop_index(op.f('ix_owners_id'), table_name='owners')
    op.drop_index(op.f('ix_owners_email'), table_name='owners')
    op.drop_table('owners')
