import sqlalchemy
from data.db_session import SqlAlchemyBase

user_group = sqlalchemy.Table('followers', SqlAlchemyBase.metadata,
                             sqlalchemy.Column('followed_id', sqlalchemy.Integer,
                                                        sqlalchemy.ForeignKey("group.id")),
                             sqlalchemy.Column('follower_id', sqlalchemy.Integer,
                                                        sqlalchemy.ForeignKey("users.id")))
