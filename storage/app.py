import connexion
from connexion import NoContent
import pykafka.common
from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import sessionmaker
from models import Base, Chat, Donation
from datetime import datetime as dt
import yaml
import logging.config
from pykafka import KafkaClient
import pykafka
import json
from threading import Thread
import os

# Get environment
ENVIRONMENT = os.getenv('ENVIRONMENT')

# Config
with open(f'config/app_conf.{ENVIRONMENT}.yml', 'r') as f:
    app_config = yaml.safe_load(f.read())

DB_USER = app_config.get("datastore", {}).get("user")
DB_PASSWORD = app_config.get("datastore", {}).get("password")
DB_HOSTNAME = app_config.get("datastore", {}).get("hostname")
DB_SCHEMA = app_config.get("datastore", {}).get("db")
DB_PORT = app_config.get("datastore", {}).get("port")

KAFKA_HOST = app_config["kafka"]["events"]["hostname"]
KAFKA_PORT = app_config["kafka"]["events"]["port"]
KAFKA_TOPIC = app_config["kafka"]["events"]["topic"]

# Logging
with open(f"config/log_conf.{ENVIRONMENT}.yml", "r") as f:
    LOG_CONFIG = yaml.safe_load(f.read())
    logging.config.dictConfig(LOG_CONFIG)

logger = logging.getLogger('basicLogger')
engine = create_engine(f"mysql://{DB_USER}:{DB_PASSWORD}@{DB_HOSTNAME}:{DB_PORT}/{DB_SCHEMA}")

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
            topic = self.client.topics[self.topic]
            self.consumer = topic.get_simple_consumer(
                consumer_group=b'event_group',
                reset_offset_on_start=False,
                auto_offset_reset=OffsetType.LATEST
            )
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

kafka_wrapper = KafkaWrapper(f"{KAFKA_HOST}:{KAFKA_PORT}", str.encode(KAFKA_TOPIC))

def start_session():
    Base.metadata.bind = engine
    return sessionmaker(bind=engine)()

def process_messages():
    """ Process event messages """
    # This is blocking - it will wait for a new message
    for msg in kafka_wrapper.messages():
        msg_str = msg.value.decode('utf-8')
        msg = json.loads(msg_str)
        logger.info("Message: %s" % msg)
        payload = msg["payload"]
        if msg["type"] == "chat":
            # Store the event1 (i.e., the payload) to the DB
            post_chat(payload)
        elif msg["type"] == "donation": # Change this to your event type
        # Store the event2 (i.e., the payload) to the DB
            post_donation(payload)

        # Commit the new message as being read
        if kafka_wrapper.consumer is not None:
            kafka_wrapper.consumer.commit_offsets()

def setup_kafka_thread():
    t1 = Thread(target=process_messages)
    t1.setDaemon(True)
    t1.start()

def post_chat(body):
    """ Receives a chat """

    session = start_session()

    chat = Chat(body['event_id'],
                body['user_id'],
                body['message'],
                body['reaction_count'],
                body['timestamp'],
                body['trace_id'])
    session.add(chat)
    
    session.commit()
    session.close()

    logger.debug(f"Stored event chat with a trace id of {body['trace_id']}")

def post_donation(body):
    """ Receives a donation """

    session = start_session()

    donation = Donation(body['event_id'],
                body['user_id'],
                body['amount'],
                body['currency'],
                body['message'],
                body['timestamp'],
                body['trace_id'])
    session.add(donation)

    session.commit()
    session.close()

    logger.debug(f"Stored event donation with a trace id of {body['trace_id']}")

def get_chats(start_timestamp, end_timestamp):
    session = start_session()
    start = dt.strptime(start_timestamp, "%Y-%m-%dT%H:%M:%S.%fZ")
    end = dt.strptime(end_timestamp, "%Y-%m-%dT%H:%M:%S.%fZ")
    statement = select(Chat).where(Chat.date_created >= start).where(Chat.date_created < end)
    results = [
        result.to_dict()
        for result in session.execute(statement).scalars().all()
    ]
    session.close()
    logger.info("Found %d chats (start: %s, end: %s)", len(results), start, end)
    return results

def get_donations(start_timestamp, end_timestamp):
    session = start_session()
    start = dt.strptime(start_timestamp, "%Y-%m-%dT%H:%M:%S.%fZ")
    end = dt.strptime(end_timestamp, "%Y-%m-%dT%H:%M:%S.%fZ")
    statement = select(Donation).where(Donation.date_created >= start).where(Donation.date_created < end)
    results = [
        result.to_dict()
        for result in session.execute(statement).scalars().all()
    ]
    session.close()
    logger.info("Found %d donations (start: %s, end: %s)", len(results), start, end)
    return results

def get_count():
    logger.info("Received count request")
    session = start_session()
    chat_count = session.scalar(select(func.count()).select_from(Chat))
    donation_count = session.scalar(select(func.count()).select_from(Donation))
    session.close()
    count = {"chat_count": chat_count, "donation_count": donation_count}
    logger.info(count)
    return count

def get_chat_event_ids():
    logger.info("Received chat event IDs request")
    session = start_session()
    statement = select(Chat)
    results = [
        result.to_event_ids()
        for result in session.execute(statement).scalars().all()
    ]
    session.close()
    return results

def get_donation_event_ids():
    logger.info("Received donation event IDs request")
    session = start_session()
    statement = select(Donation)
    results = [
        result.to_event_ids()
        for result in session.execute(statement).scalars().all()
    ]
    session.close()
    return results

app = connexion.FlaskApp(__name__, specification_dir='')
app.add_api("livestream.yaml", base_path="/storage", strict_validation=True, validate_responses=True)

if __name__ == "__main__":
    setup_kafka_thread()
    app.run(port=8090, host="0.0.0.0")