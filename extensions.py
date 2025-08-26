from flask_sqlalchemy import SQLAlchemy
import logging

db = SQLAlchemy()


def get_logger(name=__name__, level=logging.INFO):
    logger = logging.getLogger(name)
    if not logger.hasHandlers():
        logging.basicConfig(level=level)
    logger.setLevel(level)
    return logger