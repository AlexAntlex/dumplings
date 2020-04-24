import sqlalchemy
from sqlalchemy import orm
from sqlalchemy.orm import relationship, backref
from sqlalchemy_serializer import SerializerMixin
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from data.followers import user_group
from .db_session import SqlAlchemyBase


class User(SqlAlchemyBase, SerializerMixin, UserMixin):
    __tablename__ = 'users'

    id = sqlalchemy.Column(sqlalchemy.Integer,
                           primary_key=True, autoincrement=True)
    name = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    email = sqlalchemy.Column(sqlalchemy.String,
                              index=True, unique=True, nullable=True)
    hashed_password = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    about = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    avatar = sqlalchemy.Column(sqlalchemy.String, nullable=True)

    posts_user = relationship("PostUser", backref="users")
    own = orm.relation("Group", backref="groups")
    follower = relationship('Group', secondary=user_group, lazy='dynamic')

    def follow(self, group):
        if not self.is_following(group):
            self.follower.append(group)

    def unfollow(self, group):
        if self.is_following(group):
            self.follower.remove(group)

    def is_following(self, group):
        return group in self.follower

    def set_password(self, password):
        self.hashed_password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.hashed_password, password)
