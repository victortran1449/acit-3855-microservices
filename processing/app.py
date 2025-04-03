"""
processing app
"""

import logging.config
import os
import json
from datetime import datetime as dt, timezone
import yaml
import httpx
from apscheduler.schedulers.background import BackgroundScheduler
import connexion
from connexion.middleware import MiddlewarePosition
from starlette.middleware.cors import CORSMiddleware

# Get environment
ENVIRONMENT = os.getenv('ENVIRONMENT')

# Logging
with open(f"config/log_conf.{ENVIRONMENT}.yml", "r", encoding="utf-8") as f:
    LOG_CONFIG = yaml.safe_load(f.read())
    logging.config.dictConfig(LOG_CONFIG)

# Config
with open(f'config/app_conf.{ENVIRONMENT}.yml', 'r', encoding="utf-8") as f:
    app_config = yaml.safe_load(f.read())

DATA_FILE = app_config["datastore"]["filename"]

logger = logging.getLogger('basicLogger')

def get_stats():
    """ Get stats from data file """
    logger.info("Request for stats received")

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as fd:
            data = json.load(fd)
            logger.debug(data)
            logger.info("Request for stats completed")
    except:
        logger.error("Failed to get statistics, stats data file does not exist yet")
        return "Statistics do not exist", 404
    
    return data, 200

def populate_stats():
    """ Populate stats to data file """

    logger.info("Processing started")

    # Load data
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as fd:
            data = json.load(fd)
    except:
        data = {
            "num_chats": 0,
            "total_chat_reactions": 0,
            "num_donations": 0,
            "total_donations": 0.00,
        }

    # Query data and process
    default_timestamp = f"{dt.now().year}-01-01T00:00:00.000Z"
    start_timestamp = data.get("last_updated") or default_timestamp
    end_timestamp = dt.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")

    # Request chat events
    for event in ["chat", "donation"]:
        response = httpx.get(f"{app_config['eventstores'][event]['url']}?start_timestamp={start_timestamp}&end_timestamp={end_timestamp}")
        if response.status_code != 200:
            logger.error(f"Request for {event} events failed: {response.status_code}")
        else:
            event_data = json.loads(response.content.decode("utf-8"))
            logger.info(f"Received {len(event_data)} {event} events")

            # Calculate stats
            if event == "chat":
                data["num_chats"] += len(event_data)
                for chat in event_data:
                    data["total_chat_reactions"] += chat.get("reaction_count", 0)
            elif event == "donation":
                data["num_donations"] += len(event_data)
                for donation in event_data:
                    data["total_donations"] += donation.get("amount", 0)

    logger.debug(data)
    
    # Update last_updated and write data
    data["last_updated"] = end_timestamp
    with open(app_config["datastore"]["filename"], "w") as fd:
        json.dump(data, fd, indent=4)

    logger.info("Processing ended")

def init_scheduler():
    """ Init scheduler """

    sched = BackgroundScheduler(daemon=True)
    sched.add_job(populate_stats, 'interval', seconds=app_config['scheduler']['interval'])
    sched.start()

app = connexion.FlaskApp(__name__, specification_dir='')
app.add_api("stats.yaml", strict_validation=True, validate_responses=True)
app.add_middleware(
    CORSMiddleware,
    position=MiddlewarePosition.BEFORE_EXCEPTION,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if __name__ == "__main__":
    init_scheduler()
    app.run(port=8100, host="0.0.0.0")
