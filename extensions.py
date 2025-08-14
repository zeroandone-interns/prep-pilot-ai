from flask_sqlalchemy import SQLAlchemy
import logging

db = SQLAlchemy()


def get_logger(level=logging.INFO):
    logger = logging.getLogger(__name__)
    if not logger.hasHandlers():
        logging.basicConfig(level=level)
    logger.setLevel(level)
    return logger