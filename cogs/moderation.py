import discord
import asyncio
from discord.ext import commands, menus
from discord import app_commands
from typing import Optional

# This class is used to create a paginated menu for the ban list
class BanMenuPages(discord.ui.View, menus.MenuPages):
    def __init__(self, source):
        super().__init__(timeout=None)
        self._source = source
        self.current_page = 0
        self.ctx = None
        self.message = None

    async def start(self, ctx : commands.Context):
        await self._source._prepare_once()
        self.ctx = ctx
        self.message = await self.send_initial_message(ctx, ctx.channel)

    async def _get_kwargs_from_page(self, page):
        """This method calls ListPageSource.format_page class"""
        value = await super()._get_kwargs_from_page(page)
        if 'view' not in value:
            value.update({'view': self})
        return value

    async def interaction_check(self, interaction: discord.Interaction):
        """Only allow the author that invokes the command to be able to use the interaction"""
        return interaction.user == self.ctx.author

    @discord.ui.button(emoji='⏪', style=discord.ButtonStyle.blurple)
    async def first_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.show_page(0)
        await interaction.response.defer(thinking=False)

    @discord.ui.button(emoji='◀', style=discord.ButtonStyle.blurple)
    async def previous_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.show_checked_page(self.current_page - 1)
        await interaction.response.defer(thinking=False)

    @discord.ui.button(emoji='▶', style=discord.ButtonStyle.blurple)
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.show_checked_page(self.current_page + 1)
        await interaction.response.defer(thinking=False)

    @discord.ui.button(emoji='⏩', style=discord.ButtonStyle.blurple)
    async def last_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.show_page(self._source.get_max_pages() - 1)
        await interaction.response.defer(thinking=False)

# This class is used to format the ban list into an embed for the BanMenuPages
class BanSource(menus.ListPageSource):
    async def format_page(self, menu, bans):
        embed = discord.Embed(
            title="Ban List", 
            color=discord.Color.red()
        )
        for entry in bans:
            embed.add_field(name="Name: ", value=f"{entry.user}", inline=False)
            embed.add_field(name="ID: ", value=f"{entry.user.id}", inline=False)
            embed.add_field(name="Reason: ", value=f"{entry.reason}", inline=False)
            embed.add_field(name="===============", value="")

        embed.set_footer(text=f"""Page ({menu.current_page + 1}/{menu._source.get_max_pages()})
        Requested by {menu.ctx.author}""")
        return embed


@app_commands.guild_only()
class Moderation(commands.GroupCog, name="moderation"):
    """Moderation cog that includes all moderation commands"""
    
    # Initialize the cog with the bot instance
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    #==============
    # KICK COMMAND 
    #==============
    @commands.hybrid_command(name="kick", with_app_command=True)
    @commands.guild_only()
    @app_commands.describe(member="Select the member you want to kick", reason="Provide a reason")
    @commands.has_permissions(kick_members=True)
    async def kicks(self, ctx: commands.Context, member: discord.Member, *, reason: Optional[str] = None):
        """Kicks a member from the server"""
        await ctx.defer()

        if member == self.bot.user:
           return await ctx.reply("No, I'm not kicking myself.")

        if member == ctx.author:
           return await ctx.reply("Can't kick yourself.")

        if member == ctx.guild.owner:
           return await ctx.reply("You can not kick the server owner.")

        try:
            await member.kick(reason=reason)
        
        except discord.Forbidden:
            await ctx.reply("I don't have permissions to kick that person.")
            return

        except Exception as e:
            await ctx.reply(f"Error: I couldn't kick that person: {e} ")
            return 

        await ctx.reply(f"Kicked **{member}**. Reason: **{reason}**")

    #=============
    # BAN COMMAND 
    #=============
    @commands.hybrid_command(name="ban", with_app_command=True)
    @commands.guild_only()
    @app_commands.describe(member="Select the member you want to ban", reason="Provide a reason")
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx: commands.Context, member: discord.Member, *, reason: Optional[str] = None):
        """Bans a member from the server"""
        await ctx.defer()

        if member == self.bot.user:
           return await ctx.reply("No, I'm not banning myself.")

        if member == ctx.author:
           return await ctx.reply("Can't ban yourself.")

        if member == ctx.guild.owner:
           return await ctx.reply("You can not ban the server owner.")

        try:
            await member.ban(reason=reason)
        
        except discord.Forbidden:
            return await ctx.reply("I don't have permissions to ban that person.")
            
        except Exception as e:
           return await ctx.reply(f"Error: I couldn't ban that person: {e} ")

        await ctx.reply(f"Banned **{member}**. Reason: **{reason}**")

    #===============
    # UNBAN COMMAND 
    #===============
    @commands.hybrid_command(name="unban", with_app_command=True)
    @commands.guild_only()
    @app_commands.describe(user="Enter User", reason="Provide a reason")
    @commands.has_permissions(ban_members=True)
    async def unban(self, ctx: commands.Context, user: discord.User, *, reason: Optional[str] = None):
        """Unbans a banned member"""
        await ctx.defer()
        try:
            await ctx.guild.fetch_ban(user)

        except discord.NotFound:
            await ctx.reply("That user is not banned.")

        except discord.Forbidden:
            await ctx.reply("You do not have permission to use this command.")
        
        except Exception as e:
            await ctx.reply(f"**Error:** {e}")
            
        else:
            await ctx.guild.unban(user, reason=reason)
            await ctx.reply(f"Unbanned **{user}**. Reason: **{reason}**")              

    #=================
    # BANLIST COMMAND 
    #=================
    @commands.hybrid_command(name="banlist", with_app_command=True)
    @commands.guild_only()
    @commands.has_permissions(ban_members=True)
    async def banlist(self, ctx: commands.Context):
        """Shows a list of all the banned users"""
        bans = [entry async for entry in ctx.guild.bans(limit=500)] # Fetch the list of banned users, limiting to 500 entries
        if not bans:
            return await ctx.reply("No one is banned.")

        formatter = BanSource(bans, per_page=2) # Create a BanSource with the list of bans and set the number of bans per page
        menu = BanMenuPages(source=formatter) # Create a BanMenuPages with the BanSource
        if ctx.interaction:
            await ctx.send("Ban List", ephemeral=False)

        await menu.start(ctx)
 
    #===============
    # PURGE COMMAND 
    #===============   
    @commands.hybrid_command(name="purge", with_app_command=True)
    @commands.guild_only()
    @app_commands.describe(count="Number of messages to delete.")
    @commands.has_permissions(manage_messages=True)
    async def purge(self, ctx: commands.Context, count: int):
        """Deletes messages in the channel"""
        await ctx.defer(ephemeral=True)
        if count <= 0:
            msg = await ctx.reply("Please enter a number greater than 0.")
            await asyncio.sleep(5)
            return await msg.delete()

        try:
            deleted = 0
            while count > 0:
                to_delete = min(100, count) # Discord Limits the number of messages to be deleted to 100 at a time
                purged = await ctx.channel.purge(limit=to_delete + 1)  # +1 for command message
                deleted += len(purged) - 1  # subtract the command message
                count -= to_delete # decrease the count by the number of messages deleted
                await asyncio.sleep(3) # to avoid hitting rate limits
                
        except discord.Forbidden:
            return await ctx.reply("Error, I couldn't delete the messages, no permissions.")
        
        except Exception as e:
            return await ctx.reply(f"Error, I couldn't delete the messages : {e}")

        await ctx.send(f"✅ Deleted {deleted} messages.", delete_after=5)


# Register the cog with the bot
async def setup(bot: commands.Bot):
    await bot.add_cog(Moderation(bot))