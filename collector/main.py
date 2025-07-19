from shared.db.pg import engine
import logging
logger = logging.getLogger(__name__)


try:
    conn = engine.connect()
    conn.close()
except Exception as e:
    logger.error("Cannot connect to Postgres", exc_info=e)
    raise