"""create_argo_core_and_bgc_tables

Revision ID: 001_create_argo_tables
Revises: 
Create Date: 2026-08-29 01:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
import geoalchemy2

# revision identifiers, used by Alembic.
revision: str = '001_create_argo_tables'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 0. Ensure PostGIS extension is active
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis;")

    # 1. Create floats table
    op.create_table(
        'floats',
        sa.Column('id', sa.String(length=50), nullable=False),
        sa.Column('region', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_floats_id', 'floats', ['id'], unique=False)
    op.create_index('ix_floats_region', 'floats', ['region'], unique=False)

    # 2. Create profiles table
    op.create_table(
        'profiles',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('float_id', sa.String(length=50), nullable=False),
        sa.Column('cycle_number', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('latitude', sa.Float(), nullable=False),
        sa.Column('longitude', sa.Float(), nullable=False),
        sa.Column(
            'geom',
            geoalchemy2.types.Geometry(
                geometry_type='POINT',
                srid=4326,
                dimension=2,
                spatial_index=False,
                from_text='ST_GeomFromEWKT',
                name='geometry',
                nullable=False
            ),
            nullable=False
        ),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['float_id'], ['floats.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('float_id', 'cycle_number', name='uq_float_cycle')
    )
    op.create_index('idx_profiles_date', 'profiles', ['date'], unique=False)
    op.create_index('ix_profiles_float_id', 'profiles', ['float_id'], unique=False)
    op.create_index('idx_profiles_geom', 'profiles', ['geom'], unique=False, postgresql_using='gist')

    # 3. Create measurements table
    op.create_table(
        'measurements',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('profile_id', sa.BigInteger(), nullable=False),
        sa.Column('pressure_dbar', sa.Float(), nullable=False),
        sa.Column('depth_m', sa.Float(), nullable=False),
        sa.Column('temperature_c', sa.Float(), nullable=False),
        sa.Column('salinity', sa.Float(), nullable=False),
        sa.Column('density_kg_m3', sa.Float(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['profile_id'], ['profiles.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('profile_id', 'pressure_dbar', name='uq_profile_pressure')
    )
    op.create_index('idx_measurements_depth_m', 'measurements', ['depth_m'], unique=False)
    op.create_index('ix_measurements_profile_id', 'measurements', ['profile_id'], unique=False)

    # 4. Create bgc_measurements table
    op.create_table(
        'bgc_measurements',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('measurement_id', sa.BigInteger(), nullable=False),
        sa.Column('profile_id', sa.BigInteger(), nullable=False),
        sa.Column('dissolved_oxygen_umol_kg', sa.Float(), nullable=True),
        sa.Column('oxygen_saturation_pct', sa.Float(), nullable=True),
        sa.Column('chlorophyll_mg_m3', sa.Float(), nullable=True),
        sa.Column('nitrate_umol_kg', sa.Float(), nullable=True),
        sa.Column('ph', sa.Float(), nullable=True),
        sa.Column('par_umol_m2_s', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['measurement_id'], ['measurements.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['profile_id'], ['profiles.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('measurement_id', name='uq_bgc_measurement_id')
    )
    op.create_index('idx_bgc_profile_id', 'bgc_measurements', ['profile_id'], unique=False)
    op.create_index('ix_bgc_measurements_measurement_id', 'bgc_measurements', ['measurement_id'], unique=True)


def downgrade() -> None:
    op.drop_table('bgc_measurements')
    op.drop_table('measurements')
    op.drop_table('profiles')
    op.drop_table('floats')
