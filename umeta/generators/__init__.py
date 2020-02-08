from typing import Any, Dict, List

from umeta import models

from . import exiftags

generators: Dict[str, Any] = {
    'exiftags': exiftags,
}


def get_module(name: str):
    return generators[name]


def generate(candidates: List[models.Object]):
    pass
