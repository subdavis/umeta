from datetime import datetime

import sqlalchemy as sa
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import as_declarative, declared_attr
from sqlalchemy.orm import sessionmaker

from umeta.config import Config


@as_declarative()
class Base(object):
    @declared_attr
    def __tablename__(cls):
        return cls.__name__.lower()

    id = sa.Column(sa.Integer, primary_key=True, index=True)
    created = sa.Column(sa.DateTime, nullable=False, default=datetime.utcnow)


def get_db(config: Config):
    try:
        engine = create_engine(
            config.database_uri, connect_args={'check_same_thread': False}
        )
        SessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=engine
        )

        db = SessionLocal()
        yield (db, engine)
    finally:
        db.close()


def cli_get_db(config):
    return get_db(config).__next__()
