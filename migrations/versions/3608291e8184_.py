"""Remove is_enabled, add enabled_at

Revision ID: 3608291e8184
Revises: 2a5ef79af053
Create Date: 2014-02-04 16:36:13.782916
"""

# revision identifiers, used by Alembic.
revision = '3608291e8184'
down_revision = '2a5ef79af053'

import datetime as dt

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql
from sqlalchemy.sql import table, column

from rsstank.models import db, AccessKey


def upgrade():
    select = db.select(['id', 'is_enabled'], from_obj=AccessKey.__tablename__)
    data = dict(db.session.execute(select).fetchall())
    db.session.rollback()

    op.add_column('access_key', sa.Column('enabled_at', sa.DateTime(), nullable=True))
    op.drop_column('access_key', u'is_enabled')

    for key in AccessKey.query.all():
        key.enabled_at = dt.datetime.utcnow() if data[key.id] else None
    db.session.commit()


def downgrade():
    data = dict(AccessKey.query.with_entities(AccessKey.id, AccessKey.enabled_at))
    db.session.rollback()

    op.add_column('access_key', sa.Column(u'is_enabled', mysql.TINYINT(display_width=1), nullable=False))

    for id, enabled_at in data.iteritems():
        update = db.update(
            table(AccessKey.__tablename__, column('is_enabled')),
            whereclause='id = {}'.format(id),
            values=dict(is_enabled=bool(enabled_at)))
    db.session.commit()
    
    op.drop_column('access_key', 'enabled_at')
