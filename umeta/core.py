import enum
from typing import List

from dataclasses import dataclass


class ObjectType(enum.Enum):
    directory = 1
    file = 2


class ReindexStatus(enum.Enum):
    running = 1
    succeeded = 2
    failed = 3


class GeneratorStatus(enum.Enum):
    running = 1
    succeeded = 2
    failed = 3

@dataclass
class Object:
    key: List[str]
    bucket: str
    type: ObjectType
    modified: int
    size: int
