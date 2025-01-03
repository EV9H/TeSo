from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, BigInteger
from datetime import datetime, UTC
from sqlalchemy.types import TypeDecorator

class TZDateTime(TypeDecorator):
    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None:
            if value.tzinfo is None:
                value = value.replace(tzinfo=UTC)
        return value

    def process_result_value(self, value, dialect):
        if value is not None and value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value

Base = declarative_base()

class Channel(Base):
    __tablename__ = 'channels'
    
    id = Column(Integer, primary_key=True)
    channel_id = Column(BigInteger, unique=True)
    username = Column(String(255))
    title = Column(String(255))
    last_scraped_message_id = Column(BigInteger)
    last_scraped_date = Column(TZDateTime)
    messages = relationship("Message", back_populates="channel")

class Message(Base):
    __tablename__ = 'messages'
    
    id = Column(Integer, primary_key=True)
    message_id = Column(BigInteger)
    channel_id = Column(BigInteger, ForeignKey('channels.channel_id'))
    date = Column(TZDateTime, index=True)
    text = Column(Text)
    views = Column(Integer)
    forwards = Column(Integer)
    created_at = Column(TZDateTime, default=lambda: datetime.now(UTC))
    updated_at = Column(TZDateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))
    
    channel = relationship("Channel", back_populates="messages")

async def init_db(database_url: str):
    """Initialize database connection"""
    # Convert the regular PostgreSQL URL to AsyncPG URL
    async_url = database_url.replace('postgresql://', 'postgresql+asyncpg://')
    
    # Create async engine
    engine = create_async_engine(
        async_url,
        echo=True,  # Set to False in production
    )

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    return engine 