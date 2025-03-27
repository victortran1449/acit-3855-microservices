import connexion
from pykafka import KafkaClient
import json
import yaml
import logging.config
import os
from connexion.middleware import MiddlewarePosition
from starlette.middleware.cors import CORSMiddleware

# Get environment
ENVIRONMENT = os.getenv('ENVIRONMENT')

# App Config
with open(f'config/app_conf.{ENVIRONMENT}.yml', 'r') as f:
    app_config = yaml.safe_load(f.read())
KAFKA_HOST = app_config["kafka"]["events"]["hostname"]
KAFKA_PORT = app_config["kafka"]["events"]["port"]
KAFKA_TOPIC = app_config["kafka"]["events"]["topic"]

# Logging
with open(f"config/log_conf.{ENVIRONMENT}.yml", "r") as f:
    LOG_CONFIG = yaml.safe_load(f.read())
    logging.config.dictConfig(LOG_CONFIG)
logger = logging.getLogger('basicLogger')

def get_events():
    client = KafkaClient(hosts=f"{KAFKA_HOST}:{KAFKA_PORT}")
    topic = client.topics[str.encode(KAFKA_TOPIC)]
    consumer = topic.get_simple_consumer(reset_offset_on_start=True, consumer_timeout_ms=1000)
    return consumer

def get_event_index(index, event_type):
    events = get_events()
    counter = 0
    event = None
    for msg in events:
        message = msg.value.decode("utf-8")
        data = json.loads(message)
        if data["type"] == event_type:
            if counter == index:
                event = data["payload"]
                break
            counter += 1
    return event

def get_chat(index):
    logger.info(f"Received get chat request for index: {index}")
    chat = get_event_index(index, "chat")
    if chat:
        logger.info(chat)
        return chat, 200
    else:
        return { "message": f"No chat message at index {index}!"}, 404

def get_donation(index):
    logger.info(f"Received get donation request for index: {index}")
    donation = get_event_index(index, "donation")
    if donation:
        logger.info(donation)
        return donation, 200
    else:
        return { "message": f"No donation message at index {index}!"}, 404

def get_event_stats():
    logger.info(f"Received get event stats request")
    events = get_events()
    num_chats = 0
    num_donations = 0
    for msg in events:
        message = msg.value.decode("utf-8")
        data = json.loads(message)
        if data["type"] == "chat":
            num_chats += 1
        elif data["type"] == "donation":
            num_donations += 1

    stats = {
        "num_chats": num_chats,
        "num_donations": num_donations
    }
    logger.info(stats)

    return stats

# Define all required functions
app = connexion.FlaskApp(__name__, specification_dir='')
app.add_api("livestream.yaml", base_path="/analyzer", strict_validation=True, validate_responses=True)

if "CORS_ALLOW_ALL" in os.environ and os.environ["CORS_ALLOW_ALL"] == "yes":
    app.add_middleware(
        CORSMiddleware,
        position=MiddlewarePosition.BEFORE_EXCEPTION,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

if __name__ == "__main__":
    app.run(port=8110, host="0.0.0.0")