import enum

import sqlalchemy as sa

from .database import Base


class ObjectType(enum.Enum):
    folder = 1
    file = 2


class Source(Base):
    __tablename__ = 'source'
    id = sa.Column(sa.Integer, primary_key=True, index=True)
    type = sa.Column(sa.String, nullable=False)
    name = sa.Column(sa.String, nullable=False)


class Object(Base):
    __tablename__ = 'object'
    __table_args__ = (sa.UniqueConstraint('key', 'bucket'),)
    id = sa.Column(sa.Integer, primary_key=True, index=True)
    type = sa.Column(sa.Enum(ObjectType), nullable=False)
    bucket = sa.Column(sa.String, nullable=False)
    key = sa.Column(sa.String, nullable=False)
    created = sa.Column(sa.DateTime, nullable=False)
    modified = sa.Column(sa.DateTime, nullable=False)
    updated_internal = sa.Column(sa.DateTime, nullable=False)
    sha1 = sa.Column(sa.String, nullable=False)

    source_id = sa.Column(sa.Integer, sa.ForeignKey("source.id"))

    source = sa.orm.relationship('Source', back_populates='objects', lazy=True)


class Metadata(Base):
    __tablename__ = 'metadata'
    __table_args__ = (sa.UniqueConstraint('object_id', 'generator_name'),)
    id = sa.Column(sa.Integer, primary_key=True, index=True)
    object_id = sa.Column(sa.Integer, sa.ForeignKey('object.id'))
    generator_name = sa.Column(sa.String, nullable=False)
    generator_version = sa.Column(sa.String, nullable=False)
    foreign_id = sa.Column(sa.String, nullable=False)

    object = sa.orm.relationship('Object', back_populates='metadata', lazy=True)
