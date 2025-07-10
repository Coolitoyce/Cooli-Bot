import os
from dotenv import load_dotenv
load_dotenv() # Load environment variables from .env file 
# The bot's authentication token
TOKEN = os.getenv("BOT_TOKEN") # Get the bot token from the environment variable
# The RAWG API key for game data retrieval
RAWG_API_KEY = os.getenv("RAWG_API_KEY") # Get the RAWG API key from the environment variable

# The GIF list for the kys command
kys_gif_list = [
    "https://media.tenor.com/bKcyO__96TUAAAAM/anime-kys-meme.gif",
    "https://media.tenor.com/GcwuOZkNZBoAAAAM/tuyu-you-should.gif",
    "https://media.tenor.com/WtvDgjflNG0AAAAM/drake-drake-computer.gif",
    "https://c.tenor.com/OOLHNThR3YYAAAAC/tenor.gif",
    "https://media.tenor.com/sAhYu4Wd7IcAAAAM/blm.gif",
    "https://media.tenor.com/2MWwMN5GDtoAAAAM/roblox.gif",
    "https://media.tenor.com/vt7Yka9X3dwAAAAM/ltg-low-tier-god.gif",
    "https://media.tenor.com/jsILb_lKgw8AAAAM/mean-kill-you.gif",
    "https://media.tenor.com/BXC7Bvc1X8kAAAAM/chara-undertale.gif",
    "https://media.tenor.com/PM9lmuoyFpQAAAAM/sonic-tails.gif",
    "https://media.tenor.com/zMz9oqXlBC4AAAAM/die-death.gif",
    "https://media.tenor.com/hnpYfXqWm1wAAAAM/kill-yourself-easter-island.gif", 
    "https://media.tenor.com/cEi3fqVNza8AAAAM/kys-kill.gif",
    "https://media.tenor.com/8qIEMzjGhHoAAAAd/yoda.gif",  
    "https://media.tenor.com/IqckdTSNNKoAAAAd/kys-sonic.gif",
    "https://media.tenor.com/dqRgUeLfiHwAAAAd/spongebob-kill-yourself.gif",
    "https://media.tenor.com/wB5nDaZLms0AAAAj/meme-anime.gif",
    "https://media.tenor.com/rrCJT45p7RoAAAAd/good-night.gif",
    "https://media.tenor.com/IOjE3r5yw5sAAAAj/pixel-dialogue.gif",
    "https://media.tenor.com/V0OEda1WNSsAAAA1/kasane-teto-teto.webp",
    "https://media.tenor.com/uk8wCbxqndwAAAAM/vegito-blue-kill-yourself.gif",
    "https://media.tenor.com/KDmomBC8yhUAAAAM/kys-frieren.gif",
    "https://media.tenor.com/OtT2NeyRHXUAAAAM/kill-yourself-kill.gif",
    "https://media.tenor.com/xT4bpgxW0OEAAAAm/sans-kill-yourself.webp",
    "https://media.tenor.com/2MWwMN5GDtoAAAAM/roblox.gif",
    "https://media.tenor.com/Tplc18G7JBYAAAAm/comet-goombas.webp",
    "https://media.tenor.com/VkkrUXys_TcAAAAM/kill-yourself-suicide.gif"
]