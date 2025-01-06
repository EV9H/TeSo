# TeSo

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org/downloads/)
[![Poetry](https://img.shields.io/badge/packaging-poetry-cyan)](https://python-poetry.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

TeSo is a Telegram message scraping and search engine that allows you to collect and analyze messages from Telegram channels using both user-bot and bot interfaces.

## 🚀 Features

- Automated message scraping from Telegram channels
- PostgreSQL database integration for message storage
- Configurable batch processing with rate limiting
- Search functionality through a Telegram bot interface
- Docker support for easy database setup

## 📋 Prerequisites

- Python 3.8 or higher
- Poetry for dependency management
- Docker (optional, for local database setup)
- Telegram account and bot token

## ⚙️ Installation

1. Clone the repository
2. Install dependencies using Poetry:
```bash
poetry install
```

## 🔧 Configuration

1. Create a `.env` file in the project root with the following variables:
```env
API_ID=your_api_id                # Telegram API ID
API_HASH=your_api_hash           # Telegram API Hash
PHONE=your_phone_number          # Phone number for user-bot
DATABASE_URL=postgresql_url      # PostgreSQL connection URL
TELEGRAM_BOT_TOKEN=bot_token     # Telegram Bot Token
```

### Obtaining Credentials

- **API_ID** and **API_HASH**: Get from [my.telegram.org/apps](https://my.telegram.org/apps)
- **TELEGRAM_BOT_TOKEN**: Create a new bot through [@BotFather](https://t.me/BotFather)
- **DATABASE_URL** format: `postgresql://user:password@localhost:5432/dbname`

## 🏃‍♂️ Running the Application

### 1. Start the Database

If using Docker for local development:
```bash
docker compose up -d
```

### 2. Activate Poetry Environment
```bash
poetry shell
```

### 3. Run Message Scraper
```bash
python teso.engine
```

#### Scraping Configuration
Current settings (configurable in code):
```python
batch_size = 50      # Messages per batch
batch_delay = 2      # Seconds between batches
channel_delay = 30   # Seconds between channels
max_attempts = 3     # Retry attempts
```

### 4. Launch the Bot
```bash
python -m teso.bot
```

### 5. Optional: Test Search Functionality
```bash
python -m teso.search
```

## 🔍 Search Features

- Full-text search across scraped messages
- Channel-specific filtering
- Date range filtering
- Customizable result limits

## ⚠️ Rate Limiting

The scraper implements rate limiting to avoid Telegram's FloodWaitError:
- Batch processing with configurable delays
- Automatic retry mechanism
- Channel-specific delays

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 📮 Contact

For questions and support, please open an issue in the GitHub repository.

---
**Note**: This project is under active development. Features and documentation may change.
