import logging

import httpx
from core.config import settings
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from tenacity import after_log, before_log, retry, stop_after_attempt, wait_fixed

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("BackendPreStart")

max_tries = 60 * 5  # 5 minutes
wait_seconds = 1


@retry(
    stop=stop_after_attempt(max_tries),
    wait=wait_fixed(wait_seconds),
    before=before_log(logger, logging.INFO),
    after=after_log(logger, logging.WARN),
)
def wait_for_db() -> None:
    try:
        logger.info(settings.DB_URI)        
        client = MongoClient(settings.DB_URI)
        client.admin.command("ismaster")
    except ConnectionFailure as e:
        # Expected error
        raise e
    except Exception as e:
        logger.error(str(e), exc_info=e)
        raise e


@retry(
    stop=stop_after_attempt(max_tries),
    wait=wait_fixed(wait_seconds),
    before=before_log(logger, logging.INFO),
    after=after_log(logger, logging.WARN),
)
def wait_for_file_storage() -> None:
    try:
        file_storage_status_response = httpx.get(
            f"{settings.SEAWEED_MASTER_URL}/vol/status"
        )
        assert file_storage_status_response.status_code == 200
        assert file_storage_status_response.json()["Volumes"]["Free"] > 0
    except (httpx.ReadTimeout, AssertionError) as e:
        # Expected errors
        raise e
    except Exception as e:
        logger.error(str(e), exc_info=e)
        raise e


def main() -> None:
    logger.info("Waiting for DB to become ready")
    wait_for_db()
    logger.info("DB is ready!")

    logger.info("Waiting for file storage to become ready")
    wait_for_file_storage()
    logger.info("File storage is ready!")


if __name__ == "__main__":
    main()
