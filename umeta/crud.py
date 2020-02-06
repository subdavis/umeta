from datetime import datetime
import os
from typing import Dict, List, Tuple, Union
from uuid import uuid4

import sqlalchemy as sa
from sqlalchemy.orm import Session, aliased
from sqlalchemy.sql import label

from umeta import models, config, core, source


def get_nodes(db: Session, root: models.Object):
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
    return (
        db.query(models.Object, hierarchy.c.level)
        .select_entity_from(hierarchy)
        .all()
    )


def index_source(db: Session, s: config.Source):
    source_model, _ = get_or_create(db, models.Source, name=s.name)
    reindex = models.Reindex(source=source_model)
    db.add(reindex)
    db.add(source_model)
    db.commit()
    bucket = None
    parent_cache = {}
    for i, obj in enumerate(source.get_module(s.type).index(s)):
        if bucket is None or bucket.name != obj.bucket:
            bucket = upsert_bucket(db, obj.bucket, reindex, source_model)
            db.flush()
        if obj.key is not None:
            upsert_object(db, obj, parent_cache, reindex)
        yield i
    reindex.ended = datetime.utcnow()
    reindex.status = models.ReindexStatus.succeeded
    db.add(reindex)
    db.commit()


def get_bucket(db: Session, name: str) -> models.Object:
    return (
        db.query(models.Object)
        .filter(
            sa.and_(
                models.Object.name == name, models.Object.parent_id == None
            )
        )
        .first()
    )


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
        b = get_bucket(db, obj.bucket)
        return b
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


def upsert_bucket(
    db: Session, name: str, reindex: models.Reindex, sm: models.Source
):
    bucket = get_bucket(db, name)
    if not bucket:
        bucket = models.Object(
            name=name,
            type=core.ObjectType.directory,
            modified=datetime.utcnow(),
            reindex=reindex,
            source=sm,
            size=0,
        )
        db.add(bucket)
    return bucket


def upsert_object(
    db: Session,
    obj: core.Object,
    parent_cache: Dict[str, models.Object],
    reindex: models.Reindex,
) -> models.Object:
    parent = get_parent(db, obj, parent_cache)
    if parent is None:
        raise ValueError(f'cannot create object without existing parent {obj.key}')
    name = os.path.basename(obj.key)
    obj_model: models.Object = db.query(models.Object).filter(
        sa.and_(
            models.Object.name == name,
            models.Object.parent_id == parent.id,
        )
    ).first()
    revised = False
    if not obj_model:
        # need to create model
        # TODO: check for copy or move
        obj_model = models.Object(
            name=name,
            parent_id=parent.id,
            type=obj.type,
            size=obj.size,
            modified=obj.modified,
            reindex=reindex,
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
        db.add(obj_model)
    if revised:
        revision = models.Revision(object=obj_model)
        db.add(revision)
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
