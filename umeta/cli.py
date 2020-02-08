from dataclasses import asdict, dataclass
from typing import Iterable, Callable

import click
import sqlalchemy as sa

from umeta import models, config, crud, sources, generators
from umeta.database import cli_get_db


def get_by(iter: Iterable[dataclass], key, value):
    for item in iter:
        if asdict(item)[key] == value:
            return item
    return None


@click.group()
@click.pass_context
def cli(ctx):
    c = config.config
    db, engine = cli_get_db(c)
    ctx.obj = {
        'db': db,
        'engine': engine,
        'config': c,
    }


@click.command(name='generate', help='generate derivitaves')
@click.option('--name', type=click.STRING, required=True, help='source name')
@click.pass_obj
def generate(ctx, generator):
    c = ctx['config']
    db = ctx['db']
    s: config.Source = get_by(c.sources, 'name', name)
    crud.generate(db, s)


@click.command(name='index', help='index a source')
@click.option('--name', type=click.STRING, required=True, help='source name')
@click.pass_obj
def index(ctx, name):
    c = ctx['config']
    db = ctx['db']
    s: config.Source = get_by(c.sources, 'name', name)
    try:
        source_model, _ = crud.get_or_create(db, models.Source, name=s.name)
    except sa.exc.OperationalError as err:
        click.echo(message=f'Could not get source entry.\nDid you `umeta migrate`?', err=True)
        exit(1)
    reindex = models.Reindex(source=source_model)
    db.add(reindex)
    db.add(source_model)
    db.commit()

    buckets = [
        crud.upsert_object(db, b, {}, reindex)
        for b in sources.get_module(s.type).scan_for_buckets(s)
    ]
    nodes = []
    for bucket in buckets:
        nodes += crud.get_nodes(db, bucket)
    with click.progressbar(
        crud.index_source(db, s, reindex), length=len(nodes)
    ) as bar:
        for b in bar:
            pass


@click.command(name='ls')
@click.option('--bucket', type=click.STRING, required=True)
@click.pass_obj
def ls(ctx, bucket):
    c = ctx['config']
    db = ctx['db']
    b = crud.get_bucket(db, bucket)
    click.echo(crud.get_nodes(db, b))


@click.command(name='migrate', help='run datbase migrations')
@click.pass_obj
def migrate(ctx):
    engine = ctx['engine']
    models.Base.metadata.create_all(bind=engine)


cli.add_command(generate)
cli.add_command(index)
cli.add_command(ls)
cli.add_command(migrate)
