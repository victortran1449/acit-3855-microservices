from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import Column, Integer, String, DateTime, Float
from sqlalchemy.sql.functions import now

class Base(DeclarativeBase):
    pass


class Chat(Base):
    """ Chat """

    __tablename__ = "chat"

    id = Column(Integer, primary_key=True)
    event_id = Column(String(250), nullable=False)
    user_id = Column(String(250), nullable=False)
    message = Column(String(1000), nullable=False)
    reaction_count = Column(Integer, nullable=False)
    timestamp = Column(String(100), nullable=False)
    date_created = Column(DateTime, nullable=False, default=now)
    trace_id = Column(String(250), nullable=False)

    def __init__(self, event_id, user_id, message, reaction_count, timestamp, trace_id):
        """ Initializes a chat message """
        self.event_id = event_id
        self.user_id = user_id
        self.message = message
        self.reaction_count = reaction_count
        self.timestamp = timestamp
        self.trace_id = trace_id
        self.date_created = now()

    def to_dict(self):
        """ Dictionary Representation of a chat message """
        return {
            'id': self.id,
            'event_id': self.event_id,
            'user_id': self.user_id,
            'message': self.message,
            'reaction_count': self.reaction_count,
            'timestamp': self.timestamp,
            'trace_id': self.trace_id,
            'date_created': self.date_created
        }

    def to_event_ids(self):
        """ Dictionary Representation of a chat event IDs """
        return {
            'event_id': self.event_id,
            'trace_id': self.trace_id,
        }

class Donation(Base):
    """ Donation """

    __tablename__ = "donation"

    id = Column(Integer, primary_key=True)
    event_id = Column(String(250), nullable=False)
    user_id = Column(String(250), nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String(10), nullable=False)
    message = Column(String(1000), nullable=False)
    timestamp = Column(String(100), nullable=False)
    date_created = Column(DateTime, nullable=False, default=now)
    trace_id = Column(String(250), nullable=False)

    def __init__(self, event_id, user_id, amount, currency, message, timestamp, trace_id):
        """ Initializes a donation """
        self.event_id = event_id
        self.user_id = user_id
        self.amount = amount
        self.currency = currency
        self.message = message
        self.timestamp = timestamp
        self.trace_id = trace_id
        self.date_created = now()

    def to_dict(self):
        """ Dictionary Representation of a donation """
        return {
            'id': self.id,
            'event_id': self.event_id,
            'user_id': self.user_id,
            'amount': self.amount,
            'currency': self.currency,
            'message': self.message,
            'timestamp': self.timestamp,
            'trace_id': self.trace_id,
            'date_created': self.date_created
        }

    def to_event_ids(self):
        """ Dictionary Representation of a donation event IDs """
        return {
            'event_id': self.event_id,
            'trace_id': self.trace_id,
        }
