from typing import Any, Dict, Iterator, List, Tuple

from umeta import config, core
from . import disk, s3

sources: Dict[str, Any] = {
    'disk': disk,
    's3': s3,
}


def get_module(sourcetype: str):
    return sources[sourcetype]


def scan_for_buckets(
    sources: List[config.Source],
) -> Iterator[Tuple[config.Source, core.Object]]:
    for source in sources:
        for bucket in get_module(source.type).scan_for_buckets(source):
            yield (source, bucket)


def index(
    sources: List[config.Source],
) -> Iterator[Tuple[config.Source, core.Object]]:
    for source in sources:
        for obj in get_module(source.type).index(source):
            yield (source, obj)
