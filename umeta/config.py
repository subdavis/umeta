from dataclasses import dataclass, field
import json
import os
from typing import List, Optional, Union

import marshmallow_dataclass


DEFAULT_CONFIG_FILE_PATH = 'config/umeta.config.json'


@dataclass
class S3:
    access_key: str
    secret_key: str
    endpoint: str


@dataclass
class Disk:
    root: str
    cmd: str


@dataclass
class Source:
    type: str
    name: Optional[str]
    properties: Union[S3, Disk]


@dataclass
class Config:
    database_uri: str = field(default='config/umeta.config.json')
    sources: List[Source] = field(default_factory=list)


ConfigSchema = marshmallow_dataclass.class_schema(Config)


def get_config() -> Config:
    config_filepath = os.getenv('CONFIG_PATH', DEFAULT_CONFIG_FILE_PATH)
    with open(config_filepath, 'r') as config_str:
        config_json = json.load(config_str)
        config = ConfigSchema().load(config_json)
        config.database_uri = os.getenv('DATABASE_URI', config.database_uri)
        return config
