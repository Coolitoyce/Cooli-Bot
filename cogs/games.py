import discord
import logging
import aiohttp
import html
import re
from datetime import datetime
from discord import app_commands
from discord.ext import commands
from config import RAWG_API_KEY  # Import the RAWG API key from config.py


class Games(commands.Cog):
    """Games cog for game commands"""
    # Initialize the cog with the bot instance
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.hybrid_command(name="game", with_app_command=True)
    @app_commands.describe(title="Name of the game to search for")
    async def game(self, ctx: commands.Context, title: str):
        """Search for a game by name and return its details. Uses RAWG API."""
        await ctx.defer()
        try:
            async with aiohttp.ClientSession() as session:
                search_url = f"https://api.rawg.io/api/games?search={title}&key={RAWG_API_KEY}"

                async with session.get(search_url) as response:
                    if response.status != 200:
                        return await ctx.reply("❌ Error fetching game data. Please try again later.")

                    data = await response.json() # Parse the JSON response
                    results = data.get("results") # Get the results from the response
                    if not results:
                        return await ctx.reply(f"❌ No results found. Please make sure you spelled the game title correctly, and the name is in English.")

                    game = results[0]  # Get the top result
                    slug = game["slug"] # Get the slug for detailed information

                details_url = f"https://api.rawg.io/api/games/{slug}?key={RAWG_API_KEY}"
                # Fetch detailed game information
                async with session.get(details_url) as response:
                    data = await response.json() # Parse the JSON response
                    game = results[0] # Get the top result
                    game_name = game["name"] # Get the game name
                    raw_desc = data.get("description", "N/A") # Get the raw description (may contain HTML tags)
                    text_desc = html.unescape(re.sub(r'<.*?>', '', raw_desc))  # Remove HTML tags from the description
                    text_desc = text_desc[:1000] + "..." if len(text_desc) > 1000 else text_desc  # Limit description to 1000 characters
                    
                    game_website = data.get("website", "N/A") or f"https://rawg.io/games/{slug}" # Get the website or fallback to rawg.io URL
                    released_dt_object = datetime.strptime(game["released"], "%Y-%m-%d") # Get and convert release date to a datetime object

                    developers = data.get("developers") # Get developers list
                    publishers = data.get("publishers") # Get publishers list
                    
                    platforms_str = ", ".join(p["platform"]["name"] for p in game["platforms"]) or "N/A" # Get platform names and join them with commas
                    developers_str = ", ".join(d["name"] for d in developers) if developers else "N/A" # Get developer names and join them with commas
                    publishers_str = ", ".join(p["name"] for p in publishers) if publishers else "N/A" # Get publisher names and join them with commas
                    genres_str = ", ".join(g['name'] for g in game["genres"]) or "N/A" # Get genre names and join them with commas
                    background_image = game["background_image"] if game["background_image"] else None # Get background image URL if available
                    game_rating = game["rating"] if game["rating"] else "N/A" # Get game rating or N/A if not available
                    game_metacritic = game["metacritic"] if game["metacritic"] else "N/A" # Get Metacritic score or N/A if not available
      
        except aiohttp.ClientError as e:
            logging.error(f"Network error while fetching game data: {e}")
            await ctx.reply("❌ Network error. Please try again later.")

        except Exception as e:
            logging.error(f"An error occurred while processing the game command: {e}")
            await ctx.reply("❌ An unexpected error occurred.")            

        embed = discord.Embed(title=game_name, url=game_website, description=text_desc, colour=discord.Color.random()) #old color 0xf0ff80
        embed.add_field(name="🎮 Platforms:", value=platforms_str, inline=False)
        embed.add_field(name="🗓️ Release Date:", value=discord.utils.format_dt(released_dt_object, "D"), inline=True)
        embed.add_field(name="👨🏻‍💻 Developers:", value=developers_str, inline=True)
        embed.add_field(name="🏢 Publishers:", value=publishers_str, inline=True)
        embed.add_field(name="🎭 Genres:", value=genres_str, inline=True)
        embed.add_field(name="⭐ Rating:", value=game_rating, inline=True)
        embed.add_field(name="<:metacritic:1392461113983238225> Metacritic:", value=game_metacritic, inline=True)

        if background_image is not None:
            embed.set_image(url=background_image)
        
        await ctx.send(embed=embed)


# Register the cog with the bot 
async def setup(bot: commands.Bot):
    """Registers the cog with the bot"""
    await bot.add_cog(Games(bot))