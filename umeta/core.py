import enum
from typing import List

from dataclasses import dataclass


class ObjectType(enum.Enum):
    directory = 1
    file = 2


class DerivativeType(enum.Enum):
    metadata = 1
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
    key: str
    bucket: str
    type: ObjectType = ObjectType.file
    modified: int = 0
    size: int = 0


@dataclass
class Derivative:
    dependencies: List[Object]
    type: DerivativeType
    name: str
    version: str
