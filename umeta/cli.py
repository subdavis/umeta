from dataclasses import asdict, dataclass
from typing import Callable, Iterable, List, Union

import click
import sqlalchemy as sa

from umeta import config, crud, generators, models, sources
from umeta.database import cli_get_db


def get_sources(
    c: config.Config, name: Union[str, None]
) -> List[config.Source]:
    if name is not None:
        sourcenames = [name]
    else:
        sourcenames = [source.name for source in c.sources]
    for sourcename in sourcenames:
        yield get_by(c.sources, 'name', sourcename)


def get_by(iter: Iterable[dataclass], key, value):
    for item in iter:
        if asdict(item)[key] == value:
            return item
    return None


def generate(c: config.Config, db: sa.orm.Session, name: str):
    for s in get_sources(c, name):
        crud.generate(db, s)


def index(c: config.Config, db: sa.orm.Session, name: str):
    for s in get_sources(c, name):
        if s is None:
            click.echo(
                message=f'Source name={name} not found in config.', err=True,
            )
            exit(1)
        source_model, _ = crud.get_or_create(db, models.Source, name=s.name)
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
            f'reindexing {len(buckets)} bucket(s) from source={s.name}: {bucketnames}'
        )
        nodes = []
        for bucket in buckets:
            nodes += crud.get_nodes(db, bucket)
        with click.progressbar(
            crud.index_source(db, s, reindex), length=len(nodes)
        ) as bar:
            for b in bar:
                pass


def list_buckets(
    c: config.Config, db: sa.orm.Session, source_name: Union[str, None]
):
    allbuckets = []
    for s in get_sources(c, source_name):
        allbuckets.append(crud.get_buckets(db, s))
    return allbuckets


def do_crud(func: Callable, *args, **kwargs):
    try:
        return func(*args, **kwargs)
    except sa.exc.OperationalError as err:
        click.echo(
            message=('Could not get source entry.  Did you `umeta migrate`?'),
            err=True,
        )
        exit(1)


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
@click.option('--name', type=click.STRING, required=False, help='source name')
@click.pass_obj
def _generate(ctx, name):
    do_crud(generate, ctx['config'], ctx['db'], name)


@click.command(name='index', help='index a source')
@click.option('--name', type=click.STRING, required=False, help='source name')
@click.pass_obj
def _index(ctx, name):
    do_crud(index, ctx['config'], ctx['db'], name)


@click.command(name='ls')
@click.option('--bucket', type=click.STRING, required=True)
@click.pass_obj
def ls(ctx, bucket):
    c = ctx['config']
    db = ctx['db']
    b = crud.get_bucket(db, bucket)
    click.echo(crud.get_nodes(db, b))


@click.command(name='list-buckets')
@click.option(
    '--source-name', type=click.STRING, required=False, help='source name'
)
@click.pass_obj
def _list_buckets(ctx, source_name):
    bucketlist = do_crud(list_buckets, ctx['config'], ctx['db'], source_name)
    for source, buckets in bucketlist:
        for b in buckets:
            click.echo(f'{source.name}: {b.name}')


@click.command(name='list-derivs')
@click.pass_obj
def _list_derivs(ctx):
    pass


@click.command(name='migrate', help='run datbase migrations')
@click.pass_obj
def migrate(ctx):
    engine = ctx['engine']
    models.Base.metadata.create_all(bind=engine)


cli.add_command(_generate)
cli.add_command(_index)
cli.add_command(ls)
cli.add_command(_list_buckets)
cli.add_command(migrate)
