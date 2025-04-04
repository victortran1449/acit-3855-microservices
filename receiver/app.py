import logging.config
import connexion
from connexion import NoContent
import uuid
import yaml
import time
import random
import json
from datetime import datetime as dt
from pykafka import KafkaClient
from pykafka.exceptions import KafkaException
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

class KafkaWrapper:
    """ Kafka wrapper for producer """
    def __init__(self, hostname, topic):
        self.hostname = hostname
        self.topic = topic
        self.client = None
        self.producer = None
        self.connect()

    def connect(self):
        """Infinite loop: will keep trying"""
        while True:
            logger.debug("Trying to connect to Kafka...")
            if self.make_client():
                if self.make_producer():
                    break
            # Sleeps for a random amount of time (0.5 to 1.5s)
            time.sleep(random.randint(500, 1500) / 1000)

    def make_client(self):
        """
        Runs once, makes a client and sets it on the instance.
        Returns: True (success), False (failure)
        """
        if self.client is not None:
            return True
        try:
            self.client = KafkaClient(hosts=self.hostname)
            logger.info("Kafka client created")
            return True
        except KafkaException as e:
            msg = f"Kafka error when making client: {e}"
            logger.warning(msg)
            self.client = None
            self.consumer = None
            return False

    def make_producer(self):
        """
        Runs once, makes a producer and sets it on the instance.
        Returns: True (success), False (failure)
        """
        if self.producer is not None:
            return True
        if self.client is None:
            return False
        try:
            topic = self.client.topics[self.topic]
            self.consumer = topic.get_sync_producer()
            logger.info("Kafka producer created")
        except KafkaException as e:
            msg = f"Make error when making producer: {e}"
            logger.warning(msg)
            self.client = None
            self.producer = None
            return False

kafka_wrapper = KafkaWrapper(f"{KAFKA_HOST}:{KAFKA_PORT}", str.encode(KAFKA_TOPIC))

def post_chat(body):
    trace_id = str(uuid.uuid4())
    logger.info(f"Received event chat with a trace id of {trace_id}")
    body["trace_id"] = trace_id

    msg = {
        "type": "chat",
        "datetime": dt.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "payload": body
    }
    msg_str = json.dumps(msg)
    kafka_wrapper.producer.produce(msg_str.encode('utf-8'))

    return NoContent, 201

def post_donation(body):
    trace_id = str(uuid.uuid4())
    logger.info(f"Received event donation with a trace id of {trace_id}")
    body["trace_id"] = trace_id

    msg = {
        "type": "donation",
        "datetime": dt.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "payload": body
    }
    msg_str = json.dumps(msg)
    kafka_wrapper.producer.produce(msg_str.encode('utf-8'))

    return NoContent, 201

# Define all required functions
app = connexion.FlaskApp(__name__, specification_dir='')
app.add_api("livestream.yaml", base_path="/receiver", strict_validation=True, validate_responses=True)

if __name__ == "__main__":
    app.run(port=8080, host="0.0.0.0")