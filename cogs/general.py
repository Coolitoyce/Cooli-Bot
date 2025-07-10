import discord
import logging
import random
from discord import app_commands
from discord.ext import commands
from typing import Optional
from config import kys_gif_list

#==============================
# FUNCTION FOR USER INFO EMBED
#==============================
async def generate_user_info_embed(ctx_or_interaction, member: discord.Member, bot: commands.Bot) -> discord.Embed:
    """Creates an embed with user information""" 
    embed = discord.Embed(description=member.mention,
                        colour=member.color or discord.Color.default(),
                        timestamp=discord.utils.utcnow())
                        
    embed.set_author(name=member.name, icon_url=member.display_avatar.url)
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="Joined", value=discord.utils.format_dt(member.joined_at, "D"), inline=True)
    embed.add_field(name="Registered", value=discord.utils.format_dt(member.created_at, "D"), inline=True)

    try:
        if member.roles:
            roles_count = 0
            for role in member.roles:
                if role != ctx_or_interaction.guild.default_role:
                    roles_count += 1

            embed.add_field(name=f"Roles [{roles_count}]", value=", ".join(role.mention for role in member.roles if role != ctx_or_interaction.guild.default_role), inline=False)

    except Exception as e:
        logging.error(f"Error fetching roles for {member.name}({member.id}) in {ctx_or_interaction.guild.name}({ctx_or_interaction.guild.id}): {e}")    
        
    mod_perms = (
        "administrator",
        "ban_members",
        "kick_members",
        "manage_guild",
        "manage_channels",
        "manage_roles",
        "manage_messages",
        "manage_webhooks",
        "view_audit_log",
        "manage_events",
        "manage_threads",
        "moderate_members",
        "manage_nicknames",
        "mention_everyone",
        "mute_members",
        "deafen_members",
        "move_members",
        "manage_emojis_and_stickers",
        )
    # Check if the member has any of the moderator permissions
    try:
        enabled_mod_perms = [perm.replace("_", " ").title() for perm in mod_perms if getattr(member.guild_permissions, perm)]
        if member.guild_permissions.administrator or enabled_mod_perms:
            embed.add_field(name="Key Permissions",
                            value=", ".join(enabled_mod_perms),
                            inline=False) # Get all permissions that are set to True
    except Exception as e:
        logging.error(f"Error fetching permissions for {member.name}({member.id}) in {ctx_or_interaction.guild.name}({ctx_or_interaction.guild.id}): {e}") 

    if member.guild_permissions.administrator:
        embed.add_field(name="Acknowledgements", value=f"{'Server Owner' if member.id == ctx_or_interaction.guild.owner_id else 'Server Admin'}", inline=False)

    embed.set_footer(text=f"ID: {member.id}")
    user = await bot.fetch_user(member.id) # Fetch the user object from the API to access the banner

    if user.banner:
        embed.set_image(url=user.banner.url)
    
    return embed



class General(commands.Cog):
    """General cog that contains uncategorized commands."""
    def __init__(self, bot: commands.Bot):
    # Initialize the cog with the bot instance
        self.bot = bot

    #==============
    # PING COMMAND 
    #==============
    @commands.hybrid_command(with_app_command=True)
    async def ping(self, ctx: commands.Context):
        """Sends the bot's latency (ping) in milliseconds"""
        msg = await ctx.reply("Ping...", ephemeral=True) 
        ping = round(self.bot.latency * 1000) # Convert to ms
        await msg.edit(content=f"🏓 Pong! {ping}ms")   

    #=============
    # SAY COMMAND 
    #=============
    @commands.command()
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    async def say(self, ctx: commands.Context, *, message: str):
        """Sends a message to the current channel"""
        await ctx.send(message)    
    #===================
    # SLASH SAY COMMAND
    #===================
    @app_commands.command(name="say")
    @app_commands.guild_only()
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.describe(message="What do you want the bot to say?", channel="Enter text channel")
    async def slash_say(self, interaction: discord.Interaction, message: str, channel: Optional[discord.TextChannel]):
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

    #=============
    # KYS COMMAND 
    #=============
    @commands.hybrid_command(with_app_command=True, name="kys")
    @commands.guild_only()
    @app_commands.describe(member="The member to die")
    async def kysso(self, ctx: commands.Context, member: discord.Member):
        """Sends a random kys gif to a member. Don't ask why I made this"""

        if member == self.bot.user:
            return await ctx.reply("I can't kill myself, I'm already dead inside.")

        if member == ctx.author:
            return await ctx.reply("Nah man don't kys 👍")

        embed = discord.Embed(title=f"Kill Yourself {member.display_name}",
                        color=ctx.author.color or discord.Color.default())

        embed.set_image(url=random.choice(kys_gif_list))
        embed.set_footer(text=f"Requested by {ctx.author.name}")
        await ctx.send(embed=embed) 


    #==================
    # SLASH DM COMMAND
    #==================
    @app_commands.command()
    @commands.guild_only()
    @app_commands.describe(message="What do you want the bot to say?", member="The user to send the message to", anonymous="Only mods can choose to send anonymous messages. Defaults to True for mods.") 
    async def dm(self, interaction: discord.Interaction, member: discord.Member, message: str, anonymous: Optional[bool] = None):
        """Sends a direct message to a member in the server"""
        await interaction.response.defer(ephemeral=True)

        if member == self.bot.user:
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
    # WHOIS COMMAND
    #==================
    @commands.hybrid_command(name="whois", with_app_command=True)
    @commands.guild_only()
    @app_commands.describe(member="The user to get information for; defaults to the user who runs the command")
    async def userinfo(self, ctx: commands.Context, member: Optional[discord.Member] = None):
        """Gets user information"""
        member = member or ctx.author
        
        embed = await generate_user_info_embed(ctx, member, self.bot)

        try:
            await ctx.reply(embed=embed)
        except Exception as e:
            await ctx.reply(f"❌ Failed to get user information: {e}", ephemeral=True)

    #================
    # AVATAR COMMAND
    #================
    @commands.hybrid_command(name="avatar", with_app_command=True)
    @commands.guild_only()
    @app_commands.describe(member="The member you want to get the avatar from; defaults to the user who runs the command")
    async def avatar(self, ctx: commands.Context, member: Optional[discord.Member] = None):
        """Shows a member's avatar"""
        await ctx.defer()
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
    @commands.hybrid_command(name="banner", with_app_command=True)
    @commands.guild_only()
    @app_commands.describe(member="The member you want to get the banner from; defaults to the user who runs the command")
    async def banner(self, ctx: commands.Context, member: Optional[discord.Member] = None):
        """Shows a member's banner"""
        await ctx.defer()
        member = member or ctx.author
        try:
            user = await self.bot.fetch_user(member.id) # Fetch the user object from the API to access the banner

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
    @commands.command(name="choose")
    async def choose(self, ctx, *choices: str):
        """Randomly chooses one of the choices you provide"""
        await ctx.send(f"I choose `{random.choice(choices)}`")

    #======================
    # SLASH CHOOSE COMMAND
    #======================
    @app_commands.command(name="choose")
    @app_commands.describe(
        choice1="Choice 1",
        choice2="Choice 2",
        choice3="Choice 3",
        choice4="Choice 4",
        choice5="Choice 5",
        choice6="Choice 6"
    )
    async def slash_choose(self, interaction: discord.Interaction,
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

    #================
    # TEST COMMAND 
    #================
    # This command is only for testing purposes and can only be run by the bot owner 
    @commands.command()
    @commands.is_owner()
    async def test(self, ctx: commands.Context):
        for gif in kys_gif_list:
            await ctx.send(gif)  


    
async def setup(bot: commands.Bot):
    """Registers the cog with the bot"""
    await bot.add_cog(General(bot))