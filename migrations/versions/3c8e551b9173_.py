"""empty message

Revision ID: 3c8e551b9173
Revises: 70d140e9e89
Create Date: 2015-04-20 11:49:15.061762

"""

# revision identifiers, used by Alembic.
revision = '3c8e551b9173'
down_revision = '70d140e9e89'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('user', 'password')
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.add_column('user', sa.Column('password', mysql.VARCHAR(length=128), nullable=True))
    ### end Alembic commands ###
