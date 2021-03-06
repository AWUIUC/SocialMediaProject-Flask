"""empty message

Revision ID: 45f214b25e96
Revises: b0500147306a
Create Date: 2020-06-30 16:41:06.013004

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '45f214b25e96'
down_revision = 'b0500147306a'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('user', sa.Column('courses', sa.String(length=180), nullable=False))
    op.add_column('user', sa.Column('interests_and_hobbies', sa.String(length=180), nullable=False))
    op.add_column('user', sa.Column('major', sa.String(length=180), nullable=False))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('user', 'major')
    op.drop_column('user', 'interests_and_hobbies')
    op.drop_column('user', 'courses')
    # ### end Alembic commands ###
