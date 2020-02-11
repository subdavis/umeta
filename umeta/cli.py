from dataclasses import asdict, dataclass
from typing import Callable, Iterable

import click
import sqlalchemy as sa

from umeta import config, crud, generators, models, sources
from umeta.database import cli_get_db


def get_by(iter: Iterable[dataclass], key, value):
    for item in iter:
        if asdict(item)[key] == value:
            return item
    return None


def index(c: config.Config, db: sa.orm.Session, name: str):
    if name is not None:
        sourcenames = [name]
    else:
        sourcenames = [source.name for source in c.sources]

    for sourcename in sourcenames:
        s: config.Source = get_by(c.sources, 'name', sourcename)
        if s is None:
            click.echo(
                message=f'Source name={sourcename} not found in config.',
                err=True,
            )
            exit(1)
        try:
            source_model, _ = crud.get_or_create(
                db, models.Source, name=s.name
            )
        except sa.exc.OperationalError as err:
            click.echo(
                message=(
                    f'Could not get source entry.\n'
                    f'Did you `umeta migrate`?'
                ),
                err=True,
            )
            exit(1)
        reindex = models.Reindex(source=source_model)
        db.add(reindex)
        db.add(source_model)
        db.commit()

        buckets = [
            crud.upsert_object(db, b, {}, reindex, source_model)
            for b in sources.get_module(s.type).scan_for_buckets(s)
        ]
        bucketnames = ' '.join([b.name for b in buckets])
        click.echo(
            f'reindexing {len(buckets)} bucket(s) from source={sourcename}: {bucketnames}'
        )
        nodes = []
        for bucket in buckets:
            nodes += crud.get_nodes(db, bucket)
        with click.progressbar(
            crud.index_source(db, s, reindex), length=len(nodes)
        ) as bar:
            for b in bar:
                pass


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
def generate(ctx, name):
    c = ctx['config']
    db = ctx['db']
    s: config.Source = get_by(c.sources, 'name', name)
    crud.generate(db, s)


@click.command(name='index', help='index a source')
@click.argument('name', type=click.STRING, required=False)
@click.pass_obj
def _index(ctx, name):
    index(ctx['config'], ctx['db'], name)


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
cli.add_command(_index)
cli.add_command(ls)
cli.add_command(migrate)
