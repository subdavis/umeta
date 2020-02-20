from PIL import ExifTags

from umeta import core, models
from umeta.sources.utils import GetBytesType
from .utils import CheckReturnType, ChildrenArgType


Version = '0.0.1'
ObjectTypes = (core.ObjectType.file,)
Extensions = (
    '.jpg',
    '.tif',
)


def check(
    object: models.Object, children: ChildrenArgType,
) -> CheckReturnType:
    if (object.type == core.ObjectType.file) and (
        object.name.lower().endswith(Extensions)
    ):
        return [
            core.Derivative(
                dependencies=[object],
                type=core.DerivativeType.metadata,
                name='exiftags',
                version=Version,
            )
        ]
    return None


def get(
    object: models.Object,
    dependencies: ChildrenArgType,
    get_bytes: GetBytesType,
):
    pass
