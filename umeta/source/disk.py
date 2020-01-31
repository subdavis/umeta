from glob import glob
from itertools import chain
import os

from umeta.config import Source
from umeta.models import Object


def get_bytes(source: Source, object: Object):
    pass


def index(source: Source):
    search = os.path.join(os.path.abspath(source.properties.root), '**/*')
    result = glob(search, recursive=True)

    print([r for r in result])
