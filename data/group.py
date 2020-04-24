import sqlalchemy
from sqlalchemy.orm import relationship, backref
from sqlalchemy_serializer import SerializerMixin

from data.followers import user_group
from .db_session import SqlAlchemyBase


class Group(SqlAlchemyBase, SerializerMixin):
    __tablename__ = 'group'

    id = sqlalchemy.Column(sqlalchemy.Integer,
                           primary_key=True, autoincrement=True)
    name = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    info = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    admin = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey("users.id"))
    posts_list = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    avatar = sqlalchemy.Column(sqlalchemy.String, nullable=True)

    posts = relationship("Post", backref="group")
    user = relationship("User", backref="users")
    followed = relationship('User', secondary=user_group)
