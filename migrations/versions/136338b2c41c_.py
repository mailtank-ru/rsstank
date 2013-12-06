"""empty message

Revision ID: 136338b2c41c
Revises: 9ee9dd8d2bf
Create Date: 2013-12-06 12:43:34.662156

"""

# revision identifiers, used by Alembic.
revision = '136338b2c41c'
down_revision = '9ee9dd8d2bf'

from alembic import op
import sqlalchemy as sa

from rsstank import db, models


def upgrade():
    op.add_column('access_key', sa.Column('layout_id', sa.String(length=255), nullable=True))
    try:
        for access_key in models.AccessKey.query.all():
            if not access_key.layout_id:
                access_key.is_enabled = False
    finally:
        db.session.commit()


def downgrade():
    op.drop_column('access_key', 'layout_id')
