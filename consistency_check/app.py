import logging.config
import connexion
import time
from connexion import NoContent
import uuid
import yaml
import json
from datetime import datetime as dt
import os

# Get environment
ENVIRONMENT = os.getenv('ENVIRONMENT')

# Logging
with open(f"config/log_conf.{ENVIRONMENT}.yml", "r") as f:
    LOG_CONFIG = yaml.safe_load(f.read())
    logging.config.dictConfig(LOG_CONFIG)

# Config
with open(f'config/app_conf.{ENVIRONMENT}.yml', 'r') as f:
    app_config = yaml.safe_load(f.read())
logger = logging.getLogger('basicLogger')

DATA_FILE = app_config["datastore"]["filename"]
PROCESSING_URL = app_config['processing']['url']
ANALYZER_URL = app_config['analyzer']['url']
STORAGE_URL = app_config['storage']['url']

def request(method, url):
    event_data = None
    response = httpx.request(method, url)
    if response.status_code != 200:
        logger.error(f"Request for {url} events failed: {response.status_code}")
    else:
        event_data = json.loads(response.content.decode("utf-8"))
        logger.info(f"Request for {url} was successful")
    return event_data

def run_consistency_checks(body):
    start_time = time.time()
    logger.info("Starting consistency checks")

    processing_stats = request("GET", f"{PROCESSING_URL}/stats")
    analyzer_stats = request("GET", f"{ANALYZER_URL}/stats")
    analyzer_chat_event_ids = request("GET", f"{ANALYZER_URL}/event_ids/chat") or []
    analyzer_donation_event_ids = request("GET", f"{ANALYZER_URL}/event_ids/donation") or []
    storage_stats = request("GET", f"{STORAGE_URL}/count")
    storage_chat_event_ids = request("GET", f"{STORAGE_URL}/event_ids/chat") or []
    storage_donation_event_ids = request("GET", f"{STORAGE_URL}/event_ids/donation") or []

    # process counts
    queue_count = {
        "chat_count": analyzer_stats["num_chats"],
        "donation_count": analyzer_stats["num_donations"],
    }
    processing_count = {
        "chat_count": processing_stats["num_chats"],
        "donation_count": processing_stats["num_donations"],
    }

    # compare
    analyzer_event_ids = analyzer_chat_event_ids + analyzer_donation_event_ids
    storage_event_ids = storage_chat_event_ids + storage_donation_event_ids
    not_in_db = [event for event in analyzer_event_ids if event not in storage_event_ids]
    not_in_queue = [event for event in storage_event_ids if event not in analyzer_event_ids]

    # write data
    last_updated = dt.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    data = {
        "last_updated": last_updated,
        "counts": {
            "db": storage_stats,
            "queue": queue_count,
            "processing": processing_count,
        },
        "not_in_db": not_in_db,
        "not_in_queue": not_in_queue
    }

    with open(DATA_FILE, "w") as fd:
        json.dump(data, fd, indent=4)

    processing_time_ms = int((time.time() - start_time) * 1000)
    logger.info(f"Consistency checks completed | processing_time_ms={processing_time_ms} | missing_in_db={len(not_in_db)} | missing_in_queue={len(not_in_queue)}")

    return {"processing_time_ms": processing_time_ms}

def get_checks():
    logger.info("Received check request")
    try:
        with open(DATA_FILE, "r") as fd:
            data = json.load(fd)
            logger.debug(data)
    except:
        logger.error("Failed to get latest consistency check, data file does not exist yet")
        return {"message": "No checks available"}, 404
    return data, 200

app = connexion.FlaskApp(__name__, specification_dir='')
app.add_api("consistency_check.yaml", base_path="/consistency_check", strict_validation=True, validate_responses=True)

if __name__ == "__main__":
    app.run(port=8120, host="0.0.0.0")