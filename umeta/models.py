import sqlalchemy as sa

from umeta.core import ObjectType, ReindexStatus
from umeta.database import Base


class Generator(Base):
    name = sa.Column(sa.String, nullable=False)
    version = sa.Column(sa.String, nullable=False, default='0.0.1')


class Source(Base):
    name = sa.Column(sa.String, nullable=False, default='default')


class Reindex(Base):
    ended = sa.Column(sa.DateTime, nullable=True)
    status = sa.Column(
        sa.Enum(ReindexStatus), nullable=False, default=ReindexStatus.running
    )
    source_id = sa.Column(sa.Integer, sa.ForeignKey(Source.id), nullable=False)
    source = sa.orm.relationship('Source')


class Object(Base):
    __table_args__ = (sa.UniqueConstraint('name', 'parent_id'),)
    type = sa.Column(sa.Enum(ObjectType), nullable=False)
    name = sa.Column(sa.String, nullable=False)
    modified = sa.Column(sa.Integer, nullable=False)
    size = sa.Column(sa.Integer, nullable=False)

    parent_id = sa.Column(
        sa.Integer, sa.ForeignKey('object.id'), nullable=True
    )
    parent = sa.orm.relationship('Object', uselist=False)

    # the last reindex where an object was modified
    reindex_id = sa.Column(
        sa.Integer, sa.ForeignKey(Reindex.id), nullable=False
    )
    reindex = sa.orm.relationship('Reindex', uselist=False)

    # if source is populated, that means this object is a bucket
    source_id = sa.Column(sa.Integer, sa.ForeignKey(Source.id), nullable=True)
    source = sa.orm.relationship('Source', uselist=False)


class Revision(Base):
    object_id = sa.Column(sa.Integer, sa.ForeignKey(Object.id), nullable=False)
    object = sa.orm.relationship('Object')


class Metadata(Base):
    __table_args__ = (
        sa.UniqueConstraint('object_id', 'generator_id', 'name'),
    )
    name = sa.Column(sa.String, nullable=False, default='default')
    foreign_id = sa.Column(sa.String, nullable=False, unique=True)

    generator_id = sa.Column(
        sa.Integer, sa.ForeignKey(Generator.id), nullable=False
    )
    generator = sa.orm.relationship('Generator')

    object_id = sa.Column(sa.Integer, sa.ForeignKey('object.id'))
    object = sa.orm.relationship('Object', backref='metadata', lazy=True)
