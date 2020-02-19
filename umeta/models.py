import sqlalchemy as sa
from umeta.core import (
    DerivativeType,
    GeneratorStatus,
    ObjectType,
    ReindexStatus,
)
from umeta.database import Base


class Source(Base):
    name = sa.Column(sa.String, nullable=False)


class Generator(Base):
    name = sa.Column(sa.String, nullable=False)
    ended = sa.Column(sa.DateTime, nullable=True)
    version = sa.Column(sa.String, nullable=False)
    status = sa.Column(
        sa.Enum(GeneratorStatus),
        nullable=False,
        default=GeneratorStatus.running,
    )
    source_id = sa.Column(sa.Integer, sa.ForeignKey(Source.id), nullable=False)
    source = sa.orm.relationship('Source')


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

    # the last reindex where object was modified
    reindex_id = sa.Column(
        sa.Integer, sa.ForeignKey(Reindex.id), nullable=False
    )
    reindex = sa.orm.relationship('Reindex', foreign_keys='Object.reindex_id')

    # the last reindex where object was seen
    seen_reindex_id = sa.Column(
        sa.Integer, sa.ForeignKey(Reindex.id), nullable=False
    )
    seen_reindex = sa.orm.relationship(
        'Reindex', foreign_keys='Object.seen_reindex_id'
    )

    # if source is populated, that means this object is a bucket
    source_id = sa.Column(sa.Integer, sa.ForeignKey(Source.id), nullable=True)
    source = sa.orm.relationship('Source')


class Revision(Base):
    object_id = sa.Column(sa.Integer, sa.ForeignKey(Object.id), nullable=False)
    object = sa.orm.relationship('Object')


class Derivative(Base):
    __table_args__ = (sa.UniqueConstraint('generator_id', 'name', 'type', 'object_id'),)
    name = sa.Column(sa.String, nullable=False, default='default')
    type = sa.Column(sa.Enum(DerivativeType), nullable=False)
    foreign_id = sa.Column(sa.String, nullable=True, unique=True)

    generator_id = sa.Column(
        sa.Integer, sa.ForeignKey(Generator.id), nullable=False
    )
    generator = sa.orm.relationship('Generator')

    object_id = sa.Column(sa.Integer, sa.ForeignKey('object.id'))
    object = sa.orm.relationship('Object', backref='metadata', lazy=True)


class Dependency(Base):
    __table_args__ = (sa.UniqueConstraint('revision_id', 'derivative_id'),)
    revision_id = sa.Column(
        sa.Integer, sa.ForeignKey(Revision.id), nullable=False
    )
    revision = sa.orm.relationship('Revision')

    derivative_id = sa.Column(
        sa.Integer, sa.ForeignKey(Derivative.id), nullable=False
    )
    derivative = sa.orm.relationship('Derivative')
