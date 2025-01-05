from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
import os
from dotenv import load_dotenv
from .search import search_messages
import asyncio
import nest_asyncio

# Apply nest_asyncio to handle nested event loops
nest_asyncio.apply()

# Load environment variables
load_dotenv()

# Bot command handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /start is issued."""
    await update.message.reply_text(
        'Hi! I can help you search through telegram messages.\n'
        'Just send me any keyword, and I will return the top 5 most viewed messages containing that keyword.\n'
        'Try it now!'
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /help is issued."""
    await update.message.reply_text(
        'Send me any keyword to search through messages.\n'
        'I will return the top 5 most viewed messages containing your keyword.'
    )

async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Search messages based on user input."""
    keyword = update.message.text
    
    # Send typing action while processing
    await update.message.chat.send_action('typing')
    
    try:
        # Get search results
        results = await search_messages(keyword)
        
        if not results:
            await update.message.reply_text(
                f"No messages found containing '{keyword}'"
            )
            return
        
        # Format and send results
        response = f"🔍 Top 5 results for '{keyword}':\n\n"
        
        for i, result in enumerate(results, 1):
            response += (
                f"{i}. Channel: @{result['channel_name']}\n"
                f"👁 Views: {result['views']:,}\n"
                f"📅 Date: {result['date']}\n"
                f"💬 Message: {result['message_text']}\n\n"
                f"{'─' * 30}\n\n"
            )
        
        await update.message.reply_text(response)
        
    except Exception as e:
        await update.message.reply_text(
            f"Sorry, an error occurred while searching: {str(e)}"
        )
TOKEN =  os.getenv("TELEGRAM_BOT_TOKEN")

def run_bot():
    """Run the bot."""
    # Create the Application
    application = Application.builder().token(TOKEN).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search))

    # Start the bot
    print("Starting bot...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    run_bot()