import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from teso.channels import ALL_CHANNELS
from telethon import TelegramClient
from telethon.errors import FloodWaitError, ChatAdminRequiredError, UserNotParticipantError
from telethon.tl.functions.channels import JoinChannelRequest
import asyncio
import json
import os
from datetime import datetime, UTC
import logging
from typing import Optional, Dict, List
import aiofiles
from dotenv import load_dotenv
from .channels import ALL_CHANNELS  # or TELEGRAM_CHANNELS if you prefer
import sys
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from .database import init_db, Channel, Message

# Configure logging to handle Unicode characters
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer)
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scraper.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class TelegramScraper:
    def __init__(self, session_name: str, api_id: str, api_hash: str, phone: str, database_url: str):
        self.client = TelegramClient(session_name, api_id, api_hash)
        self.phone = phone
        # Convert database URL to async format
        self.database_url = database_url.replace('postgresql://', 'postgresql+asyncpg://')
        self.Session = None
        self.data_dir = "scraped_data"
        self.progress_file = "scraping_progress.json"
        self.batch_size = 50  # Messages per batch
        self.batch_delay = 2  # Seconds between message batches
        self.channel_delay = 30  # Seconds between channels
        self.max_attempts = 3
        
        # Create data directory if it doesn't exist
        os.makedirs(self.data_dir, exist_ok=True)

    async def init_database(self):
        """Initialize database connection"""
        engine = create_async_engine(self.database_url)
        self.Session = sessionmaker(
            engine, 
            class_=AsyncSession, 
            expire_on_commit=False
        )

    async def load_progress(self) -> Dict:
        """Load scraping progress from database"""
        async with self.Session() as session:
            result = await session.execute(select(Channel))
            channels = result.scalars().all()
            return {
                str(c.channel_id): {
                    'last_message_id': c.last_scraped_message_id,
                    'timestamp': c.last_scraped_date.isoformat() if c.last_scraped_date else None
                }
                for c in channels
            }

    async def save_progress(self, channel: str, last_message_id: Optional[int]):
        """Save scraping progress to file"""
        progress = await self.load_progress()
        progress[channel] = {
            'last_message_id': last_message_id,
            'timestamp': datetime.now().isoformat()
        }
        async with aiofiles.open(self.progress_file, 'w') as f:
            await f.write(json.dumps(progress, indent=2))

    async def save_messages(self, channel: str, messages: List):
        """Save messages to database"""
        async with self.Session() as session:
            try:
                channel_entity = await self.client.get_entity(channel)
                result = await session.execute(
                    select(Channel).filter_by(channel_id=channel_entity.id)
                )
                db_channel = result.scalar_one_or_none()
                
                if not db_channel:
                    db_channel = Channel(
                        channel_id=channel_entity.id,
                        username=channel_entity.username,
                        title=getattr(channel_entity, 'title', None),
                        last_scraped_message_id=None,
                        last_scraped_date=None
                    )
                    session.add(db_channel)
                
                # Track message IDs for this batch
                processed_ids = set()
                
                for msg in messages:
                    if not msg or not msg.text:
                        continue
                    
                    # Skip if we've already processed this message in this batch
                    if msg.id in processed_ids:
                        continue
                        
                    processed_ids.add(msg.id)
                    
                    result = await session.execute(
                        select(Message).filter_by(
                            message_id=msg.id,
                            channel_id=channel_entity.id
                        )
                    )
                    existing_msg = result.scalar_one_or_none()
                    
                    msg_date = msg.date if msg.date.tzinfo else msg.date.replace(tzinfo=UTC)
                    current_time = datetime.now(UTC)
                    
                    if existing_msg:
                        # Update only if views/forwards have changed
                        new_views = getattr(msg, 'views', None)
                        new_forwards = getattr(msg, 'forwards', None)
                        if existing_msg.views != new_views or existing_msg.forwards != new_forwards:
                            existing_msg.views = new_views
                            existing_msg.forwards = new_forwards
                            existing_msg.updated_at = current_time
                    else:
                        new_msg = Message(
                            message_id=msg.id,
                            channel_id=channel_entity.id,
                            date=msg_date,
                            text=msg.text,
                            views=getattr(msg, 'views', None),
                            forwards=getattr(msg, 'forwards', None),
                            created_at=current_time,
                            updated_at=current_time
                        )
                        session.add(new_msg)
                
                # Update channel's last scraped info only if we got new messages
                if messages:
                    newest_message = max(messages, key=lambda m: m.id)
                    if (db_channel.last_scraped_message_id is None or 
                        newest_message.id > db_channel.last_scraped_message_id):
                        db_channel.last_scraped_message_id = newest_message.id
                        db_channel.last_scraped_date = current_time
                
                await session.commit()
                
            except Exception as e:
                await session.rollback()
                logger.error(f"Database error: {e}")

    async def join_channel(self, channel: str) -> bool:
        """Attempt to join a channel if not already joined"""
        try:
            # Remove t.me/ if present in the channel username
            channel = channel.replace('https://t.me/', '')
            
            # Get the channel entity
            entity = await self.client.get_entity(channel)
            
            # Try to join the channel
            await self.client.join_channel(entity)
            logger.info(f"Successfully joined {channel}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to join {channel}: {e}")
            return False

    async def scrape_channel(self, channel: str, min_id: Optional[int] = None, message_limit: Optional[int] = None):
        """
        Scrape messages from a channel with rate limiting
        :param channel: Channel username or link
        :param min_id: Minimum message ID to fetch (messages newer than this ID)
        :param message_limit: Maximum number of messages to fetch (None for unlimited)
        """
        try:
            channel = channel.replace('https://t.me/', '')
            entity = await self.client.get_entity(channel)
            
            messages = []
            last_id = None
            total_messages = 0
            
            while True:
                try:
                    # Calculate batch size
                    current_batch_size = min(
                        self.batch_size,
                        message_limit - total_messages if message_limit else self.batch_size
                    )
                    
                    if current_batch_size <= 0:
                        break
                    
                    params = {
                        'entity': entity,
                        'limit': current_batch_size,
                    }
                    
                    if min_id is not None:
                        params['min_id'] = min_id
                        
                    if last_id is not None:
                        params['max_id'] = last_id
                    
                    batch = await self.client.get_messages(**params)
                    
                    if not batch:
                        break
                        
                    messages.extend(batch)
                    last_id = batch[-1].id
                    total_messages += len(batch)
                    
                    await self.save_messages(channel, batch)
                    await self.save_progress(channel, last_id)
                    
                    logger.info(f"Scraped {total_messages} messages from {channel}")
                    
                    # Break if we've reached the message limit
                    if message_limit and total_messages >= message_limit:
                        break
                    
                    await asyncio.sleep(self.batch_delay)
                    
                except FloodWaitError as e:
                    logger.critical(f"FLOOD WARNING DETECTED! Waiting time: {e.seconds} seconds")
                    logger.critical("Stopping all operations to protect account...")
                    await self.save_progress(channel, last_id)
                    await self.client.disconnect()
                    sys.exit(1)
                    
            return messages
            
        except Exception as e:
            logger.error(f"Error scraping {channel}: {e}")
            return []

    async def scrape_channels(self, channels: List[str], message_limit: int = 100):
        """
        Scrape multiple channels with proper rate limiting
        :param channels: List of channel usernames or links
        :param message_limit: Maximum number of messages to fetch per channel
        """
        try:
            for channel in channels:
                try:
                    progress = await self.load_progress()
                    last_message_id = progress.get(channel, {}).get('last_message_id')
                    
                    logger.info(f"Starting to scrape {channel}")
                    await self.scrape_channel(channel, min_id=last_message_id, message_limit=message_limit)
                    
                    logger.info(f"Finished {channel}, waiting {self.channel_delay} seconds before next channel")
                    await asyncio.sleep(self.channel_delay)
                    
                except FloodWaitError as e:
                    logger.critical(f"FLOOD WARNING DETECTED! Waiting time: {e.seconds} seconds")
                    logger.critical("Stopping all operations to protect account...")
                    await self.client.disconnect()
                    sys.exit(1)
                    
                except Exception as e:
                    logger.error(f"Error processing channel {channel}: {e}")
                    
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt, gracefully shutting down...")
            await self.client.disconnect()
            sys.exit(0)

    async def start(self):
        """Initialize the client and start scraping"""
        await self.client.connect()
        if not await self.client.is_user_authorized():
            await self.client.send_code_request(self.phone)
            try:
                await self.client.sign_in(self.phone, input('Enter the code: '))
            except SessionPasswordNeededError:
                await self.client.sign_in(password=input('Password: '))

load_dotenv()
async def main():
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        raise ValueError("DATABASE_URL environment variable is required")
        
    scraper = TelegramScraper(
        "my_telegram_session",
        os.getenv('API_ID'),
        os.getenv('API_HASH'),
        os.getenv('PHONE'),
        database_url
    )
    
    await scraper.init_database()
    await scraper.start()
    await scraper.scrape_channels(ALL_CHANNELS)
    await scraper.client.disconnect()

if __name__ == "__main__":
    asyncio.run(main()) 