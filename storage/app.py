"""
storage app
"""

import os
from datetime import datetime as dt
import yaml
import logging.config
from pykafka import KafkaClient
import json
from threading import Thread
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
import connexion
import pykafka.common
import pykafka
from models import Base, Chat, Donation

# Get environment
ENVIRONMENT = os.getenv('ENVIRONMENT')

# Config
with open(f'config/app_conf.{ENVIRONMENT}.yml', 'r', encoding="utf-8") as f:
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
with open(f"config/log_conf.{ENVIRONMENT}.yml", "r", encoding="utf-8") as f:
    LOG_CONFIG = yaml.safe_load(f.read())
    logging.config.dictConfig(LOG_CONFIG)

logger = logging.getLogger('basicLogger')
engine = create_engine(f"mysql://{DB_USER}:{DB_PASSWORD}@{DB_HOSTNAME}:{DB_PORT}/{DB_SCHEMA}")
def start_session():
    """ Start db session """
    Base.metadata.bind = engine
    return sessionmaker(bind=engine)()

def process_messages():
    """ Process event messages """
    client = KafkaClient(hosts=f"{KAFKA_HOST}:{KAFKA_PORT}")
    topic = client.topics[str.encode(KAFKA_TOPIC)]

    # Create a consume on a consumer group, that only reads new messages
    # (uncommitted messages) when the service re-starts (i.e., it doesn't
    # read all the old messages from the history in the message queue).
    consumer = topic.get_simple_consumer(
        consumer_group=b'event_group',
        reset_offset_on_start=False,
        auto_offset_reset=pykafka.common.OffsetType.LATEST
    )

    # This is blocking - it will wait for a new message
    for msg in consumer:
        msg_str = msg.value.decode('utf-8')
        msg = json.loads(msg_str)
        logger.info(f"Message: {msg}")
        payload = msg["payload"]
        if msg["type"] == "chat":
            # Store the event1 (i.e., the payload) to the DB
            post_chat(payload)
        elif msg["type"] == "donation": # Change this to your event type
        # Store the event2 (i.e., the payload) to the DB
            post_donation(payload)

        # Commit the new message as being read
        consumer.commit_offsets()

def setup_kafka_thread():
    """ Set up Kafka thread """
    thread = Thread(target=process_messages)
    thread.setDaemon(True)
    thread.start()

def post_chat(body):
    """ Receives a chat """
    session = start_session()

    chat = Chat(body['stream_id'],
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

    donation = Donation(body['stream_id'],
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
    """ Get chats from db """

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
    """ Get donations from db """

    session = start_session()
    start = dt.strptime(start_timestamp, "%Y-%m-%dT%H:%M:%S.%fZ")
    end = dt.strptime(end_timestamp, "%Y-%m-%dT%H:%M:%S.%fZ")
    statement = (
        select(Donation)
        .where(Donation.date_created >= start)
        .where(Donation.date_created < end)
    )
    results = [
        result.to_dict()
        for result in session.execute(statement).scalars().all()
    ]
    session.close()
    logger.info("Found %d donations (start: %s, end: %s)", len(results), start, end)
    return results

app = connexion.FlaskApp(__name__, specification_dir='')
app.add_api("livestream.yaml", strict_validation=True, validate_responses=True)

if __name__ == "__main__":
    setup_kafka_thread()
    app.run(port=8090, host="0.0.0.0")
