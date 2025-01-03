import asyncio
from sqlalchemy import select, desc, or_
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import os
from .database import Message, Channel

async def search_messages(keyword: str, limit: int = 5):
    """
    Search for messages containing the keyword and return top viewed results
    """
    load_dotenv()
    database_url = os.getenv('DATABASE_URL')
    print(database_url)
    if not database_url:
        raise ValueError("DATABASE_URL environment variable is required")
        
    # Convert to async URL
    database_url = database_url.replace('postgresql://', 'postgresql+asyncpg://')
    
    # Create async engine and session
    engine = create_async_engine(database_url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        # Query messages and join with channels
        query = (
            select(Message, Channel)
            .join(Channel, Message.channel_id == Channel.channel_id)
            .where(
                or_(
                    Message.text.ilike(f'%{keyword}%')
                )
            )
            .order_by(desc(Message.views))
            .limit(limit)
        )
        
        result = await session.execute(query)
        messages = result.all()
        
        # Format results
        search_results = []
        for msg, channel in messages:
            search_results.append({
                'channel_name': channel.username or channel.title,
                'message_text': msg.text[:200] + '...' if len(msg.text) > 200 else msg.text,
                'views': msg.views or 0,
                'date': msg.date.strftime('%Y-%m-%d %H:%M:%S')
            })
            
        return search_results

async def main():
    keyword = input("Enter search keyword: ")
    try:
        results = await search_messages(keyword)
        print("\nTop 5 most viewed messages containing your keyword:")
        print("-" * 80)
        for i, result in enumerate(results, 1):
            print(f"\n{i}. Channel: @{result['channel_name']}")
            print(f"Views: {result['views']:,}")
            print(f"Date: {result['date']}")
            print(f"Message: {result['message_text']}")
            print("-" * 80)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main()) 