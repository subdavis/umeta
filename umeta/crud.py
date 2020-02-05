from datetime import datetime
from typing import Dict, List, Tuple, Union
from uuid import uuid4

import sqlalchemy as sa
from sqlalchemy.orm import Session, aliased
from sqlalchemy.sql import label

from umeta import models, config, core, source


class BucketDoesNotExist(Exception):
    pass


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
        upsert_object(db, obj, bucket, parent_cache, reindex)
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
    bucket: models.Object,
    parent_cache: Dict[str, models.Object],
    reindex: models.Reindex,
) -> models.Object:
    if obj.bucket != bucket.name:
        raise ValueError(
            f'object {obj.bucket}/{"/".join(obj.key)} not from bucket {bucket.name}'
        )
    parent = bucket
    for i, name in enumerate(obj.key):
        cache_key = f'__%%{parent.id}__%%{name}'
        cache_hit = cache_key in parent_cache
        if cache_hit:
            obj_model: models.Object = parent_cache[cache_key]
        else:
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
            db.flush()
        elif (len(obj.key) - 1) == i and (
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
        if not cache_hit and obj_model.type == core.ObjectType.directory:
            parent_cache[cache_key] = obj_model
        parent = obj_model


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
