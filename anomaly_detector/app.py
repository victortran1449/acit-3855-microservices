import logging.config
import connexion
import time
from connexion import NoContent
import yaml
import json
import random
from pykafka import KafkaClient
from pykafka.exceptions import KafkaException
from pykafka.common import OffsetType
from datetime import datetime as dt, timezone
import os

# Get environment vars
ENVIRONMENT = os.getenv('ENVIRONMENT')
CHAT_REACTION_COUNT_MIN = os.getenv('CHAT_REACTION_COUNT_MIN')
DONATION_AMOUNT_MIN = os.getenv('DONATION_AMOUNT_MIN')

# Logging
with open(f"config/log_conf.{ENVIRONMENT}.yml", "r") as f:
    LOG_CONFIG = yaml.safe_load(f.read())
    logging.config.dictConfig(LOG_CONFIG)

# Config
with open(f'config/app_conf.{ENVIRONMENT}.yml', 'r') as f:
    app_config = yaml.safe_load(f.read())
logger = logging.getLogger('basicLogger')

DATA_FILE = app_config["datastore"]["filename"]

KAFKA_HOST = app_config["kafka"]["events"]["hostname"]
KAFKA_PORT = app_config["kafka"]["events"]["port"]
KAFKA_TOPIC = app_config["kafka"]["events"]["topic"]

class KafkaWrapper:
    """ Kafka wrapper for consumer """
    def __init__(self, hostname, topic):
        self.hostname = hostname
        self.topic = topic
        self.client = None
        self.consumer = None
        self.connect()

    def connect(self):
        """Infinite loop: will keep trying"""
        while True:
            logger.debug("Trying to connect to Kafka...")
            if self.make_client():
                if self.make_consumer():
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
            logger.info("Kafka client created!")
            return True
        except KafkaException as e:
            msg = f"Kafka error when making client: {e}"
            logger.warning(msg)
            self.client = None
            self.consumer = None
            return False

    def make_consumer(self):
        """
        Runs once, makes a consumer and sets it on the instance.
        Returns: True (success), False (failure)
        """
        if self.consumer is not None:
            return True
        if self.client is None:
            return False
        try:
            topic = self.client.topics[str.encode(self.topic)]
            self.consumer = topic.get_simple_consumer(
                consumer_group=b'event_group',
                reset_offset_on_start=True,
                auto_offset_reset=OffsetType.LATEST
            )
            logger.info("Kafka consumer created")
        except KafkaException as e:
            msg = f"Make error when making consumer: {e}"
            logger.warning(msg)
            self.client = None
            self.consumer = None
            return False

    def messages(self):
        """Generator method that catches exceptions in the consumer loop"""
        if self.consumer is None:
            self.connect()
        while True:
            try:
                for msg in self.consumer:
                    yield msg
            except KafkaException as e:
                msg = f"Kafka issue in consumer: {e}"
                logger.warning(msg)
                self.client = None
                self.consumer = None
                self.connect()

kafka_wrapper = KafkaWrapper(f"{KAFKA_HOST}:{KAFKA_PORT}", KAFKA_TOPIC)

def update_anomalies():
    logger.debug("Update anomalies request recieved")
    start_time = time.time()

    anomalies_count = 0
    anomalies = []

    for msg in kafka_wrapper.messages():
        msg_str = msg.value.decode('utf-8')
        msg = json.loads(msg_str)
        logger.info("Message: %s" % msg)
        payload = msg["payload"]
        if msg["type"] == "chat":
            if payload["reaction_count"] < CHAT_REACTION_COUNT_MIN:
                logger.debug(f"Chat event anomaly added. Detected: {payload["reaction_count"]}; too low (threshold {CHAT_REACTION_COUNT_MIN}")
                anomalies.append({
                    "event_id" : payload["event_id"],
                    "trace_id" : payload["trace_id"],
                    "event_type" : msg["type"],
                    "anomaly_type" : "Too Low",
                    "description" : f"Detected: {payload["reaction_count"]}; too low (threshold {CHAT_REACTION_COUNT_MIN})",
                })
                anomalies_count += 1
        elif msg["type"] == "donation":
            if payload["amount"] < DONATION_AMOUNT_MIN:
                logger.debug(f"Donation event anomaly added. Detected: {payload["amount"]}; too low (threshold {DONATION_AMOUNT_MIN}")
                anomalies.append({
                    "event_id" : payload["event_id"],
                    "trace_id" : payload["trace_id"],
                    "event_type" : msg["type"],
                    "anomaly_type" : "Too Low",
                    "description" : f"Detected: {payload["amount"]}; too low (threshold {DONATION_AMOUNT_MIN})",
                })
                anomalies_count += 1

    with open(DATA_FILE, "w") as fd:
        json.dump(anomalies, fd, indent=4)

    processing_time_ms = int((time.time() - start_time) * 1000)
    logger.info(f"Anomalies updated | processing_time_ms={processing_time_ms}")

    return {"anomalies_count": anomalies_count}, 201

def get_anomalies(event_type):
    logger.debug("Anomalies request recieved")
    
    if event_type is not None and event_type not in ["chat", "donation"]:
        logger.error(f"Invalid event_type: {event_type}")
        return {"message": f"Invalid event_type: {event_type}"}, 400

    try:
        with open(DATA_FILE, "r") as fd:
            data = json.load(fd)
            logger.debug(data)
    except:
        logger.error("Failed to get anomalies, data file does not exist yet")
        return {"message": "No anomailes available"}, 404
    
    if event_type is None:
        anomalies = data
    else:
        anomalies = [a for a in data if a["event_type"] == event_type]
    
    if len(anomalies) == 0:
        logger.debug("No anomalies found")
        return NoContent, 204
    else:
        logger.debug("Anomalies request processed")
        return anomalies, 200

app = connexion.FlaskApp(__name__, specification_dir='')
app.add_api("anomaly.yaml", base_path="/anomaly_detector", strict_validation=True, validate_responses=True)

if __name__ == "__main__":
    logger.info(f"Chat event - reaction_count threshold: {CHAT_REACTION_COUNT_MIN}")
    logger.info(f"Donation event - amount threshold: {DONATION_AMOUNT_MIN}")
    app.run(port=8130, host="0.0.0.0")