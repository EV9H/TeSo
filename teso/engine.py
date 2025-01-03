from telethon import TelegramClient
from telethon.errors import FloodWaitError, ChatAdminRequiredError, UserNotParticipantError
from telethon.tl.functions.channels import JoinChannelRequest
import asyncio
import json
import os
from datetime import datetime
import logging
from typing import Optional, Dict, List
import aiofiles
from dotenv import load_dotenv

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
    def __init__(self, session_name: str, api_id: str, api_hash: str, phone: str):
        self.client = TelegramClient(session_name, api_id, api_hash)
        self.phone = phone
        self.data_dir = "scraped_data"
        self.progress_file = "scraping_progress.json"
        self.batch_size = 50  # Messages per batch
        self.batch_delay = 4  # Seconds between message batches
        self.channel_delay = 30  # Seconds between channels
        self.max_attempts = 3
        
        # Create data directory if it doesn't exist
        os.makedirs(self.data_dir, exist_ok=True)

    async def load_progress(self) -> Dict:
        """Load scraping progress from file"""
        try:
            if os.path.exists(self.progress_file):
                async with aiofiles.open(self.progress_file, 'r') as f:
                    content = await f.read()
                    return json.loads(content)
        except Exception as e:
            logger.error(f"Error loading progress: {e}")
        return {}

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
        """Save messages to a JSON file"""
        filename = os.path.join(self.data_dir, f"{channel}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        data = [{
            'message_id': msg.id,
            'date': msg.date.isoformat(),
            'text': msg.text,
            'views': getattr(msg, 'views', None),
            'forwards': getattr(msg, 'forwards', None)
        } for msg in messages if msg and msg.text]
        
        async with aiofiles.open(filename, 'w', encoding='utf-8') as f:
            await f.write(json.dumps(data, ensure_ascii=False, indent=2))

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

    async def scrape_channel(self, channel: str, min_id: Optional[int] = None, message_limit: int = 100):
        """
        Scrape messages from a channel with rate limiting
        :param channel: Channel username or link
        :param min_id: Minimum message ID to fetch
        :param message_limit: Maximum number of messages to fetch
        """
        attempt = 0
        while attempt < self.max_attempts:
            try:
                channel = channel.replace('https://t.me/', '')
                entity = await self.client.get_entity(channel)
                
                messages = []
                last_id = None
                
                while len(messages) < message_limit:
                    try:
                        # Calculate remaining messages to fetch
                        remaining = message_limit - len(messages)
                        current_batch_size = min(self.batch_size, remaining)
                        
                        # Modified parameters to avoid None comparison
                        params = {
                            'entity': entity,
                            'limit': current_batch_size,
                        }
                        
                        # Only add min_id if it's not None
                        if min_id is not None:
                            params['min_id'] = min_id
                            
                        # Only add max_id if it's not None
                        if last_id is not None:
                            params['max_id'] = last_id
                        
                        batch = await self.client.get_messages(**params)
                        
                        if not batch:
                            break
                            
                        messages.extend(batch)
                        last_id = batch[-1].id
                        
                        # Save batch immediately
                        await self.save_messages(channel, batch)
                        await self.save_progress(channel, last_id)
                        
                        logger.info(f"Scraped {len(messages)}/{message_limit} messages from {channel}")
                        
                        # Rate limiting delay
                        await asyncio.sleep(self.batch_delay)
                        
                    except FloodWaitError as e:
                        wait_time = e.seconds
                        logger.warning(f"FloodWaitError: Waiting {wait_time} seconds")
                        await asyncio.sleep(wait_time)
                        continue
                        
                return messages
                
            except Exception as e:
                attempt += 1
                logger.error(f"Attempt {attempt} failed for {channel}: {e}")
                await asyncio.sleep(self.channel_delay)
        
        logger.error(f"Failed to scrape {channel} after {self.max_attempts} attempts")
        return []

    async def scrape_channels(self, channels: List[str], message_limit: int = 100):
        """
        Scrape multiple channels with proper rate limiting
        :param channels: List of channel usernames or links
        :param message_limit: Maximum number of messages to fetch per channel
        """
        for channel in channels:
            try:
                progress = await self.load_progress()
                last_message_id = progress.get(channel, {}).get('last_message_id')
                
                logger.info(f"Starting to scrape {channel}")
                await self.scrape_channel(channel, min_id=last_message_id, message_limit=message_limit)
                
                # Significant delay between channels
                logger.info(f"Finished {channel}, waiting {self.channel_delay} seconds before next channel")
                await asyncio.sleep(self.channel_delay)
                
            except Exception as e:
                logger.error(f"Error processing channel {channel}: {e}")

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
    scraper = TelegramScraper(
        "my_telegram_session",
        os.getenv('API_ID'),
        os.getenv('API_HASH'),
        os.getenv('PHONE')
    )
    
    channels = ['Qikan2023']  # Add your channel list here
    await scraper.start()
    await scraper.scrape_channels(channels)
    await scraper.client.disconnect()

if __name__ == "__main__":
    asyncio.run(main()) 