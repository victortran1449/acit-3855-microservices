import logging.config
import connexion
from connexion import NoContent
import uuid
import yaml
import json
from datetime import datetime as dt
from pykafka import KafkaClient
import os

# Get environment
ENVIRONMENT = os.getenv('ENVIRONMENT')

# Config
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

def post_chat(body):
    trace_id = str(uuid.uuid4())
    logger.info(f"Received event chat with a trace id of {trace_id}")
    body["trace_id"] = trace_id

    client = KafkaClient(hosts=f"{KAFKA_HOST}:{KAFKA_PORT}")
    topic = client.topics[str.encode(KAFKA_TOPIC)]
    producer = topic.get_sync_producer()
    msg = {
        "type": "chat",
        "datetime": dt.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "payload": body
    }
    msg_str = json.dumps(msg)
    producer.produce(msg_str.encode('utf-8'))

    return NoContent, 201

def post_donation(body):
    trace_id = str(uuid.uuid4())
    logger.info(f"Received event donation with a trace id of {trace_id}")
    body["trace_id"] = trace_id

    client = KafkaClient(hosts=f"{KAFKA_HOST}:{KAFKA_PORT}")
    topic = client.topics[str.encode(KAFKA_TOPIC)]
    producer = topic.get_sync_producer()
    msg = {
        "type": "donation",
        "datetime": dt.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "payload": body
    }
    msg_str = json.dumps(msg)
    producer.produce(msg_str.encode('utf-8'))

    return NoContent, 201

# Define all required functions
app = connexion.FlaskApp(__name__, specification_dir='')
app.add_api("livestream.yaml", base_path="/receiver", strict_validation=True, validate_responses=True)

if __name__ == "__main__":
    app.run(port=8080, host="0.0.0.0")