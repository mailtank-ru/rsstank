"""empty message

Revision ID: 2a5ef79af053
Revises: 136338b2c41c
Create Date: 2013-12-06 15:09:15.008680

"""

# revision identifiers, used by Alembic.
revision = '2a5ef79af053'
down_revision = '136338b2c41c'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.add_column('feed', sa.Column('channel_description', sa.Text(), nullable=True))
    op.add_column('feed', sa.Column('channel_image_url', sa.String(length=2000), nullable=True))
    op.add_column('feed', sa.Column('channel_link', sa.String(length=2000), nullable=True))
    op.add_column('feed', sa.Column('channel_title', sa.String(length=2000), nullable=True))
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('feed', 'channel_title')
    op.drop_column('feed', 'channel_link')
    op.drop_column('feed', 'channel_image_url')
    op.drop_column('feed', 'channel_description')
    ### end Alembic commands ###