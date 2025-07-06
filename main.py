import discord
import asyncio
import logging
import random
import os
from discord import app_commands
from discord.ext import commands
from typing import Optional

# Import the bot's token and other stuff from config.py
from config import *
# Import the get_prefix function to set the command prefix dynamically
from cogs.prefixes import get_prefix

# Setup logging to a file 
handler = logging.FileHandler(filename='bot.log', encoding='utf-8', mode='w')
# The bot's Discord activity
activity = discord.Activity(name="my parents fight", type=discord.ActivityType.watching)

# Bot class that inherits from commands.Bot to use commands and cogs 
class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True # Enable message content intent to read messages
        super().__init__(intents=intents, command_prefix=get_prefix, activity=activity) 
    
    async def setup_hook(self):
        # Load all cogs from the cogs folder
        cogs_count = 0
        for filename in os.listdir("./cogs"):
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
            await bot.process_commands(message)
    
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
bot = MyBot()    

#================
# Owner-only command to reload a specific cog
#================
@bot.command()
@commands.is_owner()
async def reload(ctx: commands.Context, cog: str):
    """Reloads a cog from the cogs folder."""
    try:
        await ctx.bot.reload_extension(f"cogs.{cog}")
        msg = await ctx.send(f"🔁 Reloaded `cogs.{cog}` successfully.")

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
@bot.command()
@commands.is_owner()
async def sync(ctx: commands.Context):
    msg = await ctx.reply("Syncing command tree...")
    synced = await bot.tree.sync()
    await msg.edit(content=f"Synced {len(synced)} commands.")
    await asyncio.sleep(5)
    await msg.delete()
    await ctx.message.delete()


#==============
# PING COMMAND 
#==============
@bot.hybrid_command(with_app_command=True)
async def ping(ctx: commands.Context):
    """Sends the bot's latency (ping) in milliseconds"""
    msg = await ctx.reply("Ping...", ephemeral=True)
    ping = round(bot.latency * 1000) # Convert to ms
    await msg.edit(content=f"🏓 Pong! {ping}ms")   

#=============
# SAY COMMAND 
#=============
@bot.command()
@commands.guild_only()
@commands.has_permissions(manage_guild=True)
async def say(ctx: commands.Context, *, message: str):
    """Sends a message to the current channel"""
    await ctx.send(message)
 
#=============
# KYS COMMAND 
#=============
@bot.hybrid_command(with_app_command=True, name="kys")
@commands.guild_only()
@app_commands.describe(member="The member to die")
async def kysso(ctx: commands.Context, member: discord.Member):
    """Sends a random kys gif to a member. Don't ask why I made this"""

    if member == bot.user:
        return await ctx.reply("I can't kill myself, I'm already dead inside.")

    if member == ctx.author:
        return await ctx.reply("Nah man don't kys 👍")

    embed = discord.Embed(title=f"Kill Yourself {member.display_name}",
                      color=ctx.author.color or discord.Color.default())

    embed.set_image(url=random.choice(kys_gif_list))
    embed.set_footer(text=f"Requested by {ctx.author.name}")
    await ctx.send(embed=embed)   

#===================
# SLASH SAY COMMAND
#===================
@bot.tree.command(name="say")
@app_commands.guild_only()
@app_commands.default_permissions(manage_guild=True)
@app_commands.describe(message="What do you want the bot to say?", channel="Enter text channel")
async def tree_say(interaction: discord.Interaction, message: str, channel: Optional[discord.TextChannel]):
    """"Sends a message to a channel; if no channel is given, the message is sent into the current channel"""
    await interaction.response.defer(ephemeral=True)
    try:
        if channel:
            await channel.send(message)
            await interaction.response.edit_original_response("✅ Sent!")

        else:
            await interaction.channel.send(message)
            await interaction.response.edit_original_response("✅ Sent!")

    except discord.Forbidden:
        await interaction.response.edit_original_response("I don't have permission to send messages in that channel.")
    
    except Exception as e:
        await interaction.response.edit_original_response(f"❌ Failed to send the message: {e}")

#==================
# SLASH DM COMMAND
#==================
@bot.tree.command()
@commands.guild_only()
@app_commands.describe(message="What do you want the bot to say?", member="The user to send the message to", anonymous="Only mods can choose to send anonymous messages. Defaults to True for mods.") 
async def dm(interaction: discord.Interaction, member: discord.Member, message: str, anonymous: Optional[bool] = None):
    """Sends a direct message to a member in the server"""
    await interaction.response.defer(ephemeral=True)

    if member == bot.user:
        return await interaction.edit_original_response(content="I can't DM myself, silly!")

    if member == interaction.user:
        return await interaction.edit_original_response(content="You can't DM yourself man, do you need a hug?")

    if member.bot:
        return await interaction.edit_original_response(content="You can't DM a bot.")

    permissions = interaction.user.guild_permissions
    # Check if the user has any of these permissions to send an anonymous message
    is_mod = (
        permissions.administrator or
        permissions.manage_guild or
        permissions.manage_channels or
        permissions.manage_messages
        )
    
    # Check if the user is trying to send an anonymous message without permission
    if anonymous == True and not is_mod:
        return await interaction.edit_original_response(content="You don't have permission to send anonymous messages. Please disable the anonymous option.")
    
    if is_mod and anonymous is None:
        anonymous = True # Default to True for moderators

    if anonymous == True:
        # Send an anonymous message without the user's info
        embed = discord.Embed(title=f"Message from {interaction.guild.name}",
                    description=message,
                    timestamp=discord.utils.utcnow())
                    
    else:
        # Send a message with the user's info
        embed = discord.Embed(title=f"Message from {interaction.guild.name} by {interaction.user.display_name}",
                    description=message,
                    colour=interaction.user.color or 0xfdf7ca,
                    timestamp=discord.utils.utcnow())

        embed.set_thumbnail(url=interaction.user.display_avatar.url)
    
    try:
        # Attempt to send the message
        await member.send(embed=embed)
        await interaction.edit_original_response(content="✅ Sent!")

    except Exception as e: 
        await interaction.edit_original_response(content=f"❌ Failed to send the message: {e}")
    
#==================
# JOINDATE COMMAND
#==================
@bot.hybrid_command(name="joindate", with_app_command=True)
@commands.guild_only()
@app_commands.describe(member="The member you want to get the joined date from; defaults to the user who runs the command")
async def joindate(ctx: commands.Context, member: Optional[discord.Member] = None):
    """Says when a member joined."""
    member = member or ctx.author
    await ctx.reply(f"{member.display_name} joined {discord.utils.format_dt(member.joined_at)}", ephemeral=True)

#================
# AVATAR COMMAND
#================
@bot.hybrid_command(name="avatar", with_app_command=True)
@commands.guild_only()
@app_commands.describe(member="The member you want to get the avatar from; defaults to the user who runs the command")
async def get_avatar(ctx: commands.Context, member: Optional[discord.Member] = None):
    """Shows a member's avatar"""
    member = member or ctx.author
    if not member.display_avatar:
        return await ctx.reply("That member doesn't have an avatar")

    embed = discord.Embed(title=f"{member.display_name}'s avatar",
                      url=member.display_avatar.url,
                      colour=member.color or discord.Color.default())
    
    embed.set_image(url=member.display_avatar.url)
    await ctx.reply(embed=embed)

#================
# BANNER COMMAND
#================
@bot.hybrid_command(name="banner", with_app_command=True)
@commands.guild_only()
@app_commands.describe(member="The member you want to get the banner from; defaults to the user who runs the command")
async def get_banner(ctx: commands.Context, member: Optional[discord.Member] = None):
    """Shows a member's banner"""
    member = member or ctx.author
    try:
        user = await bot.fetch_user(member.id) # Fetch the user object from the API to access the banner

        if not user.banner:
            return await ctx.reply("That member doesn't have a banner.")

        embed = discord.Embed(title=f"{member.display_name}'s banner",
                        url=user.banner.url,
                        colour=member.color or discord.Color.default())
        
        embed.set_image(url=user.banner.url)
    
    except Exception as e:
        return await ctx.reply(f"Failed to get the banner: {e}")

    await ctx.reply(embed=embed)

#================
# CHOOSE COMMAND
#================
@bot.command()
async def choose(ctx, *choices: str):
    """Randomly chooses one of the choices you provide"""
    await ctx.send(f"I choose `{random.choice(choices)}`")

#======================
# SLASH CHOOSE COMMAND
#======================
@bot.tree.command()
@app_commands.describe(
    choice1="Choice 1",
    choice2="Choice 2",
    choice3="Choice 3",
    choice4="Choice 4",
    choice5="Choice 5",
    choice6="Choice 6"
)
async def tree_choose(interaction: discord.Interaction,
                choice1: str,
                choice2: str,
                choice3: Optional[str],
                choice4: Optional[str],
                choice5: Optional[str],
                choice6: Optional[str]):
    """Randomly chooses one of the choices you provide"""
    choices = [choice1, choice2]
    optional_choices = [choice3, choice4, choice5, choice6]
    choices.extend(choice for choice in optional_choices if choice is not None)
    await interaction.response.send_message(f"I choose **{random.choice(choices)}**")    

#===============================
# JOINDATE CONTEXT MENU COMMAND
#===============================
@bot.tree.context_menu(name="Show Join Date")
async def show_joindate(interaction: discord.Interaction, member: discord.Member):
    """Shows when a member joined"""
    await interaction.response.send_message(f"{member.display_name} joined {discord.utils.format_dt(member.joined_at)}", ephemeral=True)

#=============================
# AVATAR CONTEXT MENU COMMAND
#=============================
@bot.tree.context_menu(name="Show Avatar")
async def show_avatar(interaction: discord.Interaction, member: discord.Member):
    """Shows a member's avatar"""
    member = member or ctx.author
    if not member.display_avatar:
        return await interaction.response.send_message("That member doesn't have an avatar", ephemeral=True)

    embed = discord.Embed(title=f"{member.display_name}'s avatar",
                      url=member.display_avatar.url,
                      colour=member.color or discord.Color.default())   
    
    embed.set_image(url=member.display_avatar.url)
    await interaction.response.send_message(embed=embed, ephemeral=True)

#=============================
# BANNER CONTEXT MENU COMMAND
#=============================
@bot.tree.context_menu(name="Show Banner")
async def show_banner(interaction: discord.Interaction, member: discord.Member):
    """Shows a member's banner"""
    member = member or ctx.author
    try:
        user = await bot.fetch_user(member.id) # Fetch the user object from the API to access the banner

        if not user.banner:
            return await interaction.response.send_message("That member doesn't have a banner.", ephemeral=True)

        embed = discord.Embed(title=f"{member.display_name}'s banner",
                        url=user.banner.url,
                        colour=member.color or discord.Color.default())
        
        embed.set_image(url=user.banner.url)
    
    except Exception as e:
        return await interaction.response.send_message(f"Failed to get the banner: {e}", ephemeral=True)

    await interaction.response.send_message(embed=embed, ephemeral=True)

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