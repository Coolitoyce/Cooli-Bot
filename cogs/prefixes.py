import discord
import logging
import re
import aiosqlite
from discord import app_commands
from discord.ext import commands


async def get_prefix(bot: commands.Bot, message: discord.Message):
    """Retrieves the prefix for a specific guild from the database"""
    # Check if there is a guild 
    if not message.guild: 
        return # Prefix commands are only used in guilds
        
    # Get the prefix from the database for the guild
    async with aiosqlite.connect('database.db') as db:
        try:
            cursor = await db.execute("SELECT prefix FROM prefixes WHERE guild_id = ?", (message.guild.id, ))
            result = await cursor.fetchone()
        
        except Exception as e:
            logging.error(f"Error fetching prefix for guild {message.guild.id}: {e}")
            return "."

    return result[0] if result else "."

class Prefix(commands.Cog):
    """Prefix cog that handles the bot's prefix commands and events"""

    # Initialize the cog with the bot instance
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    # on message listener to respond to mentions of the bot with its prefix
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):  
        # Ignore messages from the bots or messages not sent in a guild
        if message.author.bot or not message.guild:
            return
            
        # Check if the message mentions the bot and respond with the prefix
        if re.fullmatch(rf"<@!?{self.bot.user.id}>", message.content):
            prefix = await get_prefix(self.bot, message) 
            return await message.reply(f"My prefix for this server is: `{prefix}`")


    #====================
    # SET PREFIX COMMAND 
    #====================
    # Command to set a new prefix for the bot in a specific guild
    @commands.hybrid_command(name="setprefix", with_app_command=True)
    @app_commands.describe(new_prefix="The new prefix for the bot")
    @app_commands.rename(new_prefix="prefix")
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    async def setprefix(self, ctx: commands.Context, new_prefix: str):
        """Sets a new command prefix for this server"""
        if len(new_prefix) > 5:
            return await ctx.send(f"{ctx.author.mention}, Prefix cannot be more than 5 characters.")

        async with aiosqlite.connect('database.db') as db:
            try:
                await db.execute("INSERT OR REPLACE INTO prefixes (guild_id, prefix) VALUES (?, ?)", (ctx.guild.id, new_prefix))
                await db.commit()
                
            except Exception as e:
                logging.error(f"Error setting prefix for guild {ctx.guild.name} ({ctx.guild.id}): {e}")
                return await ctx.reply(f"❌ An error occurred while setting the prefix: `{e}`")
        
        await ctx.reply(f"✅ Set the prefix to: **`{new_prefix}`**")

    #================
    # PREFIX COMMAND 
    #================
    @commands.hybrid_command(name="prefix", with_app_command=True)
    @commands.guild_only()
    async def prefix(self, ctx: commands.Context):
        """Shows the bot prefix for this server"""
        
        prefix = await get_prefix(self.bot, ctx.message)
        await ctx.reply(f"My prefix for this server is: **`{prefix}`**")


# Register the cog with the bot and create the database table if it doesn't exist
async def setup(bot: commands.Bot):
    """Registers the cog with the bot"""
    async with aiosqlite.connect('database.db') as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS prefixes (
            guild_id INTEGER PRIMARY KEY,
            prefix TEXT
        )""")
        await db.commit()
    
    await bot.add_cog(Prefix(bot))