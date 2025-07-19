import discord
import asyncio
import logging
from os import listdir
from discord.ext import commands
from config import TOKEN # Import the bot's token from config.py
from cogs.general import generate_user_info_embed # Import the function to generate user info embed
from cogs.prefixes import get_prefix # Import the get_prefix function to set the command prefix dynamically

# Setup logging to a file
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s', # Log format with timestamp and level
    datefmt='%Y-%m-%d %H:%M:%S', # Date format for the timestamp
    handlers= [
        logging.FileHandler(filename='bot.log', encoding='utf-8', mode='a')
    ]
)
handler = logging.FileHandler(filename='bot.log', encoding='utf-8', mode='a')
    
# The bot's Discord activity
activity = discord.Activity(name="my parents fight", type=discord.ActivityType.watching)

class CooliBot(commands.Bot):
    """Bot class that inherits from commands.Bot to use commands and cogs""" 
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True # Enable message content intent to read messages
        super().__init__(intents=intents, command_prefix=get_prefix, activity=activity) 
    
    async def setup_hook(self):
        # Load all cogs from the cogs folder
        cogs_count = 0
        for filename in listdir("./cogs"):
            if filename.endswith(".py"):
                cogs_count += 1
                await self.load_extension(f"cogs.{filename[:-3]}")
                print(f"Loaded cog: {filename[:-3]}")
                
        print(f"Loaded {cogs_count} cogs.")

        # Sync the command tree (application/slash commands)
        synced = await self.tree.sync()
        print(f"Synced {len(synced)} commands.")

    async def on_ready(self):
        # Fired when the bot is ready and connected to Discord
        print(f"Logged in as {self.user} (ID: {self.user.id})")
        print("------")

    async def on_message(self, message: discord.Message):  
        # Ignore messages from the bot itself
        if message.author == self.user:
            return

        # Process prefix commands in guilds only
        if message.guild:
            await self.process_commands(message)
    
    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError):
        # Ignore unknown command errors
        if isinstance(error, commands.CommandNotFound):
            return

        # Custom response for a missing required argument error
        if isinstance(error, commands.MissingRequiredArgument):
            usage = ctx.command.usage or f"{ctx.prefix}{ctx.command.name} {ctx.command.signature}"
            # Format the error message to highlight the missing argument
            msg = (
                f"```{usage}\n"
                f"{' ' * usage.find(error.param.name)}{'^' * len(error.param.name)}\n"
                f"Missing required argument: {error.param.name}```"
            )
            return await ctx.reply(msg, ephemeral=True, mention_author=False)

        await ctx.reply(f"`{error}`", ephemeral=True, mention_author=False)
        

# Create an instance of the bot class        
bot = CooliBot()    

#================
# Owner-only command to reload a specific cog
#================
@bot.command(name="reload")
@commands.is_owner()
async def reload(ctx: commands.Context, cog: str):
    """Reloads a cog from the cogs folder."""
    try:
        await ctx.bot.reload_extension(f"cogs.{cog}")
        msg = await ctx.send(f"🔁 Reloaded `cogs.{cog}` successfully.")
        logging.info(f"Cog {cog} was reloaded using the command.")

    except commands.ExtensionNotLoaded:
        msg = await ctx.send(f"❌ Cog `cogs.{cog}` is not loaded.")

    except commands.ExtensionNotFound:
        msg = await ctx.send(f"❌ Cog `cogs.{cog}` not found.")

    except commands.ExtensionFailed as e:
        msg = await ctx.send(f"❌ Failed to reload cog `cogs.{cog}`:\n```{e}```")

    except Exception as e:
        msg = await ctx.send(f"⚠️ Unexpected error:\n```{e}```")

    await asyncio.sleep(5)
    await msg.delete()
    await ctx.message.delete()

#==============
# Owner-only command to manually sync the command tree
#==============
@bot.command(name="sync")
@commands.is_owner()

async def sync(ctx: commands.Context):
    msg = await ctx.reply("Syncing command tree...")
    synced = await bot.tree.sync()
    await msg.edit(content=f"Synced {len(synced)} commands.")
    logging.info(f"Synced command tree using the command. Synced {len(synced)} Commands")
    await asyncio.sleep(5)
    await msg.delete()
    await ctx.message.delete()  

#================================
# USER INFO CONTEXT MENU COMMAND
#================================
@bot.tree.context_menu(name="Show User Info")
async def show_userinfo(interaction: discord.Interaction, member: discord.Member):
    """Shows user info"""
    await interaction.response.defer()  # Defer the response to avoid timeout
    embed = await generate_user_info_embed(ctx_or_interaction=interaction, member=member, bot=bot)  # Generate the user info embed using the imported function
    try:
        await interaction.edit_original_response(embed=embed)  # Send the embed
    except Exception as e:
        logging.error(
            f"Failed to send user info embed: {e} - Guild:{interaction.guild.name}({interaction.guild_id}), Member:{member.name}({member.id})")
        await interaction.edit_original_response(f"Failed to send user info. {e}", ephemeral=True)


#=============================
# AVATAR CONTEXT MENU COMMAND
#=============================
@bot.tree.context_menu(name="Show Avatar")
async def show_avatar(interaction: discord.Interaction, member: discord.Member):
    """Shows a member's avatar"""
    await interaction.response.defer()
    if not member.display_avatar:
        return await interaction.edit_original_response(content="That member doesn't have an avatar")

    embed = discord.Embed(title=f"{member.display_name}'s avatar",
                    url=member.display_avatar.url,
                    colour=member.color or discord.Color.default())   
    
    embed.set_image(url=member.display_avatar.url)
    await interaction.edit_original_response(embed=embed)

#=============================
# BANNER CONTEXT MENU COMMAND
#=============================
@bot.tree.context_menu(name="Show Banner")
async def show_banner(interaction: discord.Interaction, member: discord.Member):
    """Shows a member's banner"""
    await interaction.response.defer()
    try: 
        user = await bot.fetch_user(member.id) # Fetch the user object from the API to access the banner

        if not user.banner:
            return await interaction.edit_original_response(content="That member doesn't have a banner.")

        embed = discord.Embed(title=f"{member.display_name}'s banner",
                        url=user.banner.url,
                        colour=member.color or discord.Color.default())
        
        embed.set_image(url=user.banner.url)
    
    except Exception as e:
        return await interaction.edit_original_response(content=f"Failed to get banner: {e}")

    await interaction.edit_original_response(embed=embed)


#==========================
# *Temporary* help command 
#==========================
class MyHelpCommand(commands.MinimalHelpCommand):
    async def send_pages(self):
        destination = self.get_destination()
        for page in self.paginator.pages:
            embed = discord.Embed(description=page, colour=0x0097f5)
            await destination.send(embed=embed)

bot.help_command = MyHelpCommand()


# Run the bot with the provided token and log handler
bot.run(TOKEN, log_handler=handler)     