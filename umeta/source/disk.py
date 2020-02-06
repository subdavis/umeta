from datetime import datetime
from glob import glob
import os
import stat
from typing import Iterator, List, Tuple, Union

from umeta import core, config


def parse_path(relpath: str) -> Tuple[str, List[str]]:
    split = relpath.split(os.sep)
    bucket = split[0]
    key = split[1:]
    if len(key) == 0 or key[0] == '':
        return bucket, None
    else:
        return bucket, os.sep.join(key)


def scan_for_buckets(source: config.Source) -> Iterator[core.Object]:
    results = os.listdir(source.properties.root)
    buckets = []
    for r in results:
        f = os.stat(os.path.join(source.properties.root, r))
        if stat.S_ISDIR(f.st_mode):
            bucket, key = parse_path(r)
            yield core.Object(
                type=ObjectType.directory,
                key=key,
                bucket=bucket,
                modified=int(
                    datetime.utcfromtimestamp(f.st_mtime).timestamp()
                ),
                size=f.st_size,
            )


def get_bytes(source: config.Source, obj: core.Object):
    if obj.type == ObjectType.directory:
        raise ValueError('cannot open directory for reading')
    abspath = os.path.abspath(source.properties.root)
    path = os.path.join(abspath, obj.bucket, obj.bucket_key)
    return open(path, 'rb')


def index(source: config.Source) -> Iterator[core.Object]:
    search = os.path.join(os.path.abspath(source.properties.root), '**/*')
    result = glob(search, recursive=True)
    for r in result:
        f = os.stat(r)
        relpath = os.path.relpath(r, source.properties.root)
        bucket, key = parse_path(relpath)
        yield core.Object(
            type=(
                core.ObjectType.directory
                if stat.S_ISDIR(f.st_mode)
                else core.ObjectType.file
            ),
            bucket=bucket,
            key=key,
            modified=int(datetime.utcfromtimestamp(f.st_mtime).timestamp()),
            size=f.st_size,
        )
