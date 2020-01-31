from dataclasses import asdict, dataclass
from typing import Iterable

import click

from umeta import models, config
from umeta.database import cli_get_db

from umeta.source import sources


def get_by(iter: Iterable[dataclass], key, value):
    for item in iter:
        if asdict(item)[key] == value:
            return item
    return None


@click.group()
@click.pass_context
def cli(ctx):
    c = config.get_config()
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
    c: config.Config = ctx['config']
    source: config.Source = get_by(c.sources, 'name', name)
    indexer: Callable = sources.get(source.type).index
    objects = indexer(source)
    print(objects)


cli.add_command(index)
