from dataclasses import asdict, dataclass
from typing import Iterable, Callable

import click

from umeta import models, config, crud, source
from umeta.database import cli_get_db


def get_by(iter: Iterable[dataclass], key, value):
    for item in iter:
        if asdict(item)[key] == value:
            return item
    return None


@click.command(name='ls')
@click.option('--bucket', type=click.STRING, required=True)
@click.pass_obj
def ls(ctx, bucket):
    c = ctx['config']
    db = ctx['db']
    b = crud.get_bucket(db, bucket)
    print(crud.get_nodes(db, b))


@click.group()
@click.pass_context
def cli(ctx):
    c = config.config
    db, engine = cli_get_db(c)
    models.Base.metadata.create_all(bind=engine)
    ctx.obj = {
        'db': db,
        'config': c,
    }


@click.command(name='index', help='index a source')
@click.option('--name', type=click.STRING, required=True, help='source name')
@click.pass_obj
def index(ctx, name):
    c = ctx['config']
    db = ctx['db']
    s: config.Source = get_by(c.sources, 'name', name)
    source_model, _ = crud.get_or_create(db, models.Source, name=s.name)
    reindex = models.Reindex(source=source_model)
    db.add(reindex)
    db.add(source_model)
    db.commit()

    buckets = [
        crud.upsert_object(db, b, {}, reindex)
        for b in source.get_module(s.type).scan_for_buckets(s)
    ]
    nodes = []
    for bucket in buckets:
        nodes += crud.get_nodes(db, bucket)
    with click.progressbar(
        crud.index_source(db, s, reindex), length=len(nodes)
    ) as bar:
        for b in bar:
            pass


cli.add_command(index)
cli.add_command(ls)
