# CooliBot

CooliBot is a multifunctional Discord bot built with [**`discord.py`**](https://discordpy.readthedocs.io/en/stable/).
This bot highlights my learning journey with the library — showcasing command design, moderation tools, context menus, buttons, API integrations, and more.
> Designed for simplicity, fun, and utility — all wrapped in a modular, scalable structure.

---

## Features

- ### Customizable Prefix per Server

  - Each server can set its own command prefix.
  - Mentioning the bot displays the current prefix.
  - Prefixes are stored and managed via an SQLite database.

- ### Moderation Commands

  - Commands like `/kick`, `/ban`, `/banlist`, and more
  
- ### Utility Commands

  - `/ping`: Shows bot latency.
  - `/say`: Make the bot say something in a channel.
  - `/dm`: Sends a DM to another user in a server.
  - `/whois`, `/avatar`, `/banner`: User profile information.
  - Context menus like
    - `Show Avatar`
    - `Show Banner`
    - `Show User Info`.

- ### Game Commands

  - `/game <name>` retrieves detailed information about a game using the RAWG API.
    - Includes cover image, genres, ratings, release date, developers, and more.
  - `/games rps` play a game of rock, paper, scissors with another user in the server.
  - More to come soon!

- ### Reminder Commands
  
  - Set reminders using simple time formats `3 days 1 hr 30 min`
  - The bot will DM you when the time is up.

- ### Fun Commands

  - `/choose`: Randomly select from your given options.
  - `/kys`: Sends a random _family friendly_ GIF. ;)

- ### Modular Cog System

  - Commands are split into organized cogs for scalability and maintainability.
  - Live cog reloading with `.reload <cog>`.

- ### Logging

  - Logs bot activity and errors to `bot.log`.

---

## Installation

### 1. Clone the repo

```bash
git clone https://github.com/Coolitoyce/Cooli-Bot.git
cd CooliBot
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Set your environment variables

- Create a `.env` file in the root directory:

  ```env
  DISCORD_TOKEN=your_discord_bot_token_here
  RAWG_API_KEY=your_rawg_api_key_here
  ```

### 4. Run the bot

```bash
python main.py
```
