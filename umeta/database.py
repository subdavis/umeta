from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from umeta.config import Config


Base = declarative_base()


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
