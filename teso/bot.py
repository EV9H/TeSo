from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters, CallbackQueryHandler
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
    # Create custom keyboard with three buttons
    keyboard = [
        ["🔥 热门", "🔍 热搜", "👤 我的"]
    ]
    reply_markup = ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True  # Makes the keyboard smaller
    )
    
    await update.message.reply_text(
        '🔍我是个资源搜索引擎，向我发送关键词来寻找群组、频道、视频、音乐、中文包',
        reply_markup=reply_markup
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

async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button presses."""
    text = update.message.text
    
    if text == "🔥 热门":
        buttons = [
            [InlineKeyboardButton("Option 1", callback_data="hot_1")],
            [InlineKeyboardButton("Option 2", callback_data="hot_2")],
            [InlineKeyboardButton("Option 3", callback_data="hot_3")],
            [InlineKeyboardButton("Option 4", callback_data="hot_4")],
            [InlineKeyboardButton("Option 5", callback_data="hot_5")],
            [InlineKeyboardButton("Option 6", callback_data="hot_6")],
            [InlineKeyboardButton("Option 7", callback_data="hot_7")],
            [InlineKeyboardButton("Option 8", callback_data="hot_8")],
            [InlineKeyboardButton("Option 9", callback_data="hot_9")],
            [InlineKeyboardButton("Option 10", callback_data="hot_10")]
        ]
        reply_markup = InlineKeyboardMarkup(buttons)
        await update.message.reply_text(
            "🔥 热门\n\n选择你感兴趣的类别！",
            reply_markup=reply_markup
        )
        
    elif text == "🔍 热搜":
        buttons = [
            [
                InlineKeyboardButton("Opt 1", callback_data="search_1"),
                InlineKeyboardButton("Opt 2", callback_data="search_2"),
                InlineKeyboardButton("Opt 3", callback_data="search_3"),
                InlineKeyboardButton("Opt 4", callback_data="search_4"),
                InlineKeyboardButton("Opt 5", callback_data="search_5")
            ],
            [
                InlineKeyboardButton("Opt 6", callback_data="search_6"),
                InlineKeyboardButton("Opt 7", callback_data="search_7"),
                InlineKeyboardButton("Opt 8", callback_data="search_8"),
                InlineKeyboardButton("Opt 9", callback_data="search_9"),
                InlineKeyboardButton("Opt 10", callback_data="search_10")
            ],
            [
                InlineKeyboardButton("Opt 11", callback_data="search_11"),
                InlineKeyboardButton("Opt 12", callback_data="search_12"),
                InlineKeyboardButton("Opt 13", callback_data="search_13"),
                InlineKeyboardButton("Opt 14", callback_data="search_14"),
                InlineKeyboardButton("Opt 15", callback_data="search_15")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(buttons)
        await update.message.reply_text(
            "近期热门搜索排行榜",
            reply_markup=reply_markup
        )
        
    elif text == "👤 我的":
        buttons = [
            [InlineKeyboardButton("Option A", callback_data="profile_1")],
            [
                InlineKeyboardButton("Option B", callback_data="profile_2"),
                InlineKeyboardButton("Option C", callback_data="profile_3")
            ],
            [
                InlineKeyboardButton("Option D", callback_data="profile_4"),
                InlineKeyboardButton("Option E", callback_data="profile_5")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(buttons)
        await update.message.reply_text(
            "个人中心\n\n"
            "昵称：\n"
            "ID：\n"
            "👑已提现：0$\n"
            "💰余额：0$\n"
            "💰存入账余额：0$",
            reply_markup=reply_markup
        )

# Add this function to handle button callbacks
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button callbacks."""
    query = update.callback_query
    await query.answer()  # Answer the callback query
    
    if query.data == "recharge":
        # Send the QR code image from the correct path
        with open('./img/qrcode.jpg', 'rb') as photo:
            await context.bot.send_photo(
                chat_id=query.message.chat_id,
                photo=photo,
                caption="扫码充值"
            )

async def privacy_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send privacy policy when the command /privacy is issued."""
    await update.message.reply_text(
        "隐私政策内容在这里..."  # Replace with your actual privacy policy
    )

async def pc_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /pc (个人中心) command."""
    await update.message.reply_text(
        "欢迎来到个人中心"  # Replace with your actual personal center content
    )

async def ad_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /ad (广告投放) command."""
    buttons = [[InlineKeyboardButton("充值", callback_data="recharge")]]
    reply_markup = InlineKeyboardMarkup(buttons)
    await update.message.reply_text(
        "广告投放相关信息",
        reply_markup=reply_markup
    )

async def more_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /more (更多功能) command."""
    await update.message.reply_text(
        "更多功能列表"  # Replace with your actual features list
    )

TOKEN =  os.getenv("TELEGRAM_BOT_TOKEN")

def run_bot():
    """Run the bot."""
    # Create the Application
    application = Application.builder().token(TOKEN).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    
    # Add new command handlers
    application.add_handler(CommandHandler("privacy", privacy_command))
    application.add_handler(CommandHandler("pc", pc_command))
    application.add_handler(CommandHandler("ad", ad_command))
    application.add_handler(CommandHandler("more", more_command))
    
    # Add handler for button presses
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND, 
        handle_button
    ))
    
    # Keep the general text handler last
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search))

    # Add this line
    application.add_handler(CallbackQueryHandler(button_callback))

    # Start the bot
    print("Starting bot...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    run_bot()
    