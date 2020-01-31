from typing import Dict, Any

from umeta.source import disk, s3

sources: Dict[str, Any] = {
    'disk': disk,
    's3': s3,
}
