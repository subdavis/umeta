import os
from datetime import datetime
from typing import Dict, List, Tuple, Union
from uuid import uuid4

import sqlalchemy as sa
from sqlalchemy.orm import Session, aliased
from sqlalchemy.sql import label

from umeta import config, core, generators, models, sources


def get_buckets(db: Session, s: config.Source) -> List[models.Object]:
    source = (
        db.query(models.Source).filter(models.Source.name == s.name).first()
    )
    if source is None:
        raise ValueError(f'source {s.name} not in database')
    buckets = (
        db.query(models.Object)
        .filter(models.Object.source_id == source.id)
        .all()
    )
    return (
        source,
        buckets,
    )


def get_nodes(db: Session, root: models.Object, modified: datetime = None):
    hierarchy = (
        db.query(models.Object, sa.literal(0).label('level'))
        .filter(models.Object.parent_id == root.id)
        .cte(name="hierarchy", recursive=True)
    )
    parent = aliased(hierarchy, name="p")
    children = aliased(models.Object, name="c")
    hierarchy = hierarchy.union_all(
        db.query(children, (parent.c.level + 1).label("level")).filter(
            children.parent_id == parent.c.id
        )
    )
    q = db.query(models.Object, hierarchy.c.level).select_entity_from(
        hierarchy
    )
    if modified:
        q = q.filter(models.Object.modified >= modified)
    return q.all()


def index_source(db: Session, s: config.Source, reindex: models.Reindex):
    parent_cache = {}
    for i, obj in enumerate(sources.get_module(s.type).index(s)):
        if obj.key is not None:
            upsert_object(db, obj, parent_cache, reindex)
        yield i
    reindex.ended = datetime.utcnow()
    reindex.status = models.ReindexStatus.succeeded
    db.add(reindex)
    db.commit()


def get_parent(
    db: Session, obj: core.Object, cache: Dict[str, models.Object],
) -> models.Object:
    """
    get parent node of obj
        get_parent('/foo/bar.txt') -> Object(name=foo)
        get_parent('/bar') -> Object(name=None, bucket=bucket)
    """
    path = obj.key
    if path is None:
        raise ValueError(f'Cannot get parent of bucket {obj.key} {obj.bucket}')
    parent_name = os.path.dirname(path)
    if parent_name == '':
        return (
            db.query(models.Object)
            .filter(
                sa.and_(
                    models.Object.name == obj.bucket,
                    models.Object.parent_id == None,
                )
            )
            .first()
        )
    cache_key = f'{obj.bucket}/{parent_name}'
    if cache_key in cache:
        return cache[cache_key]
    grandparent = get_parent(
        db, core.Object(key=parent_name, bucket=obj.bucket), cache=cache
    )
    if grandparent is None:
        return None
    parent = (
        db.query(models.Object)
        .filter(
            sa.and_(
                models.Object.name == os.path.basename(parent_name),
                models.Object.parent_id == grandparent.id,
            )
        )
        .first()
    )
    if parent is None:
        return None
    else:
        cache[cache_key] = parent
        return parent


def upsert_object(
    db: Session,
    obj: core.Object,
    parent_cache: Dict[str, models.Object],
    reindex: models.Reindex,
    source: models.Source = None,
) -> models.Object:
    is_bucket = obj.key is None

    name = obj.bucket if is_bucket else os.path.basename(obj.key)
    parent_id = None if is_bucket else get_parent(db, obj, parent_cache).id

    if parent_id is None and not is_bucket:
        raise ValueError(
            f'cannot create object without existing parent {obj.key}'
        )

    obj_model: models.Object = db.query(models.Object).filter(
        sa.and_(
            models.Object.name == name, models.Object.parent_id == parent_id,
        )
    ).first()

    revised = False
    if not obj_model:
        # need to create model
        # TODO: check for copy or move
        obj_model = models.Object(
            name=name,
            parent_id=parent_id,
            type=obj.type,
            size=obj.size,
            modified=obj.modified,
            reindex=reindex,
            seen_reindex=reindex,
            source=source,
        )
        revised = True
        db.add(obj_model)
        if obj.type == core.ObjectType.directory:
            db.flush()
    elif (
        obj.type != obj_model.type
        or obj.modified != obj_model.modified
        or obj.size != obj_model.size
    ):
        obj_model.type = obj.type
        obj_model.size = obj.size
        obj_model.modified = obj.modified
        obj_model.reindex = reindex
        revised = True
    if revised:
        revision = models.Revision(object=obj_model)
        db.add(revision)
    obj_model.seen_reindex = reindex
    db.add(obj_model)
    return obj_model


def get_or_create(db: Session, model: object, defaults=None, **kwargs):
    existing = db.query(model).filter_by(**kwargs).first()
    if existing:
        return existing, False
    else:
        params = dict(**kwargs)
        params.update(defaults or {})
        instance = model(**params)
        db.add(instance)
        return instance, True


def latest_object_revision(db: Session, obj: models.Object) -> models.Revision:
    return (
        db.query(sa.sql.func.max(models.Revision.created))
        .filter(models.Revision.object_id == obj.id)
        .group_by(models.Revision.object_id)
        .first()
    )


def generate(
    db: Session, s: config.Source
) -> List[List[Tuple[str, models.Object, List[models.Object]]]]:

    source, buckets = get_buckets(db, s)
    for name in s.generators:
        generator_module = generators.get_module(name)
        generator_module_version = generator_module.Version
        generator_model = models.Generator(
            name=name, version=generator_module_version, source=source,
        )
        db.commit()
        previous_generator: models.Generator = (
            db.query(models.Generator)
            .filter(
                sa.and_(
                    models.Generator.name == name,
                    models.Generator.version == generator_module_version,
                    models.Generator.status == core.GeneratorStatus.succeeded,
                )
            )
            .order_by(models.Generator.created.desc())
            .first()
        )

        modified_since = 0
        if previous_generator:
            modified_since = int(
                datetime.timestamp(previous_generator.created)
            )

        try:
            for b in buckets:
                nodes = get_nodes(db, b, modified_since)
                for node, _ in nodes:
                    # TODO: if type of node is directory, pass children to checker as well.
                    derivs = generator_module.check(node, None)
                    filtered = filter_outdated(
                        db, generator_model, node, derivs
                    )

            generator_model.status = core.GeneratorStatus.succeeded
            generator_model.ended = datetime.utcnow()
            db.add(generator_model)
            db.commit()
        except:
            db.rollback()
            generator_model.ended = datetime.utcnow()
            generator_model.status = core.GeneratorStatus.failed
            db.add(generator_model)
            db.commit()
            raise Exception(f'generation exception for source {name}')


def filter_outdated(
    db: Session,
    generator: models.Generator,
    primary: models.Object,
    derivatives: List[core.Derivative],
) -> List[Tuple[models.Derivative, List[models.Dependency]]]:
    """
    returns only the outdated derivatives.
    """
    for der in derivatives:
        der_model, created = get_or_create(
            db,
            models.Derivative,
            name=der.name,
            type=der.type,
            generator_id=generator.id,
            object_id=primary.id,
        )

        if created:
            dependency_models = []
            for dep in der.dependencies:
                latest_revision = latest_object_revision(db, dep)
                dependency_models.append(models.Dependency(
                    revision=latest_revision,
                    derivative=der_model,
                ))
            yield (der_model, dependency_models)

        else:

            # TODO: check set intersection of returned dependencies and known ones

            # check the revision versions of the existing dependencies
            deps: List[models.Dependency] = (
                db.query(models.Dependency)
                .filter(models.Dependency.derivative_id == der_model.id)
                .all()
            )
            changed = []
            for dep in deps:
                latest = latest_object_revision(db, dep.revision.object.id)
                if latest.id != dep.revision_id:
                    changed.append(dep)
            if len(changed):
                yield (der_model, changed)


def recompute(
    db: Session,
    outdated_deriv: models.Derivative,
    outdated_deps: List[models.Dependency],
):
    [db.delete(dep) for dep in outdated_deps]
    new_deps
