from dataclasses import asdict, dataclass
from typing import Iterable, Callable

import click

from umeta import models, config, crud
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
    source: config.Source = get_by(c.sources, 'name', name)
    db = ctx['db']
    bucket = crud.get_bucket(db, 'node_modules')
    with click.progressbar(
        crud.index_source(db, source),
        length=len(crud.get_nodes(db, bucket)),
        label='Indexing',
    ) as bar:
        for i in bar:
            pass


cli.add_command(index)
cli.add_command(ls)
