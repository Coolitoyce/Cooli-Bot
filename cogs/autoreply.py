import discord
import aiosqlite
import logging
from discord.ext import commands
from discord import app_commands


@app_commands.guild_only()
@app_commands.default_permissions(manage_guild=True)
class AutoReply(commands.GroupCog, name="autoreply"):
    """Cog for managing autoreplies in a server."""
    def __init__(self, bot: commands.Bot):
        # Initialize the cog with the bot instance
        self.bot = bot

    # on message listener to check for autoreply triggers
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):  
        # Ignore messages from bots or messages not sent in a guild
        if message.author.bot or not message.guild:
            return

        # Check if the message content matches any autoreply triggers in the database
        async with aiosqlite.connect("database.db") as db:
            async with db.execute("SELECT trigger, response FROM autoreplies WHERE guild_id = ?", (message.guild.id, )) as cursor:
                rows = await cursor.fetchall()
            
            for trigger, response in rows:
                if trigger.lower() in message.content.lower():
                    # If the trigger is found, send the corresponding response
                    await message.reply(response)

    #===========================
    # ADD NEW AUTOREPLY COMMAND 
    #===========================
    @app_commands.command(name="add")
    @app_commands.describe(trigger="The message that will trigger the autoreply when sent", reply="What will the bot reply to the trigger message?")
    async def add_reply(self, interaction: discord.Interaction, trigger: str, reply: str):
        """Add a new autoreply trigger in this server"""
        # Check if the trigger starts with a special character to prevent conflicts with the bot's commands prefix
        if trigger[0] in "`~!@#$%^&*()_+-=\\|[]{}<>?,.;:'/\"":
            return await interaction.response.send_message("The trigger message can't begin with a special character.")

        # Connect to the database and insert the new autoreply trigger and response
        async with aiosqlite.connect('database.db') as db:
            try:
                await db.execute(
                    "INSERT INTO autoreplies (guild_id, trigger, response) VALUES (?, ?, ?)",
                    (interaction.guild.id, trigger, reply)
                )
                await db.commit()

            except Exception as e:
                logging.error(f"Error inserting autoreply into database: `{e}`")
                return await interaction.response.send_message(f"Error adding autoreply")
            
            await interaction.response.send_message(f"✅ Added a new autoreply with trigger: `{trigger}`")
    
    #==========================
    # UPDATE AUTOREPLY COMMAND
    #==========================
    @app_commands.command(name="update")
    @app_commands.describe(trigger="The trigger to update", reply="The bot's new reply to the trigger message")
    async def update_reply(self, interaction: discord.Interaction, trigger: str, reply: str):
        """Update the bot's reply to an existing trigger"""
        # Check if the trigger starts with a special character to prevent conflicts with the bot's commands prefix
        if trigger[0] in "`~!@#$%^&*()_+-=\\|[]{}<>?,.;:'/\"":
            return await interaction.response.send_message("The trigger message can't begin with a special character.")

        # Connect to the database and check if the trigger specified exists
        async with aiosqlite.connect('database.db') as db:
            try:
                cursor = await db.execute("SELECT * FROM autoreplies WHERE guild_id = ? AND trigger = ?", (interaction.guild.id, trigger))
                result = await cursor.fetchone()
                
                if result is None:
                    return await interaction.response.send_message("No such trigger was found.")

                # If the trigger exists, update the response in the database
                await db.execute(
                    "REPLACE INTO autoreplies (guild_id, trigger, response) VALUES (?, ?, ?)",
                    (interaction.guild.id, trigger, reply)
                )
                await db.commit()

            except Exception as e:
                logging.error(f"Error updating autoreply {trigger} for guild {interaction.guild.name}({interaction.guild_id}): `{e}`")   
                return await interaction.response.send_message(f"Error updating autoreply")

            await interaction.response.send_message(f"✅ Successfully updated the autoreply:\nTrigger: `{trigger}`\nNew reply: `{reply}`")

    #==========================
    # REMOVE AUTOREPLY COMMAND
    #==========================
    @app_commands.command(name="remove")
    @app_commands.describe(trigger="The trigger message to be deleted")
    async def remove_reply(self, interaction: discord.Interaction, trigger: str):
        """Remove an existing autoreply trigger in this server"""
        # Connect to the database and check if the trigger specified exists
        async with aiosqlite.connect('database.db') as db:
            try:
                cursor = await db.execute("SELECT * FROM autoreplies WHERE guild_id = ? AND trigger = ?", (interaction.guild.id, trigger))
                result = await cursor.fetchone()
                
                if result is None:
                    return await interaction.response.send_message("No such trigger was found.")

                # If the trigger exists, delete it from the database
                await db.execute(
                    "DELETE FROM autoreplies WHERE guild_id = ? AND trigger = ?",
                    (interaction.guild.id, trigger)
                )
                await db.commit()

            except Exception as e:
                logging.error(f"Error deleting autoreply {trigger} from guild {interaction.guild.name}({interaction.guild_id}): `{e}`") 
                return await interaction.response.send_message(f"Error deleting autoreply")  

            await interaction.response.send_message(f"✅ Successfully removed the autoreply for trigger: `{trigger}`")

    #===============================
    # CLEAR ALL AUTOREPLIES COMMAND
    #===============================
    @app_commands.command(name="clear")
    async def clear_reply(self, interaction: discord.Interaction):
        """Clear all autoreplies in this server"""
        # Connect to the database and check if there are any autoreplies set for the server
        async with aiosqlite.connect('database.db') as db:
            try:
                cursor = await db.execute("SELECT 1 FROM autoreplies WHERE guild_id = ? LIMIT 1", (interaction.guild.id, ))
                result = await cursor.fetchone()
                
                if result is None:
                    return await interaction.response.send_message("No autoreplies were found to clear.")

                # If autoreplies are found, delete all of them from the server
                await db.execute("DELETE FROM autoreplies WHERE guild_id = ?", (interaction.guild.id, ))
                await db.commit()

            except Exception as e:
                logging.error(f"Error clearing autoreplies for guild {interaction.guild.name}({interaction.guild_id}): `{e}`")  
                return await interaction.response.send_message(f"Error clearing autoreplies`")  

            await interaction.response.send_message("✅ Successfully cleared all autoreplies for this server.")
    
    #==========================
    # LIST AUTOREPLIES COMMAND
    #==========================
    @app_commands.command(name="list")
    async def list_replies(self, interaction: discord.Interaction):
        """View all autoreplies in this server."""
        # Get all autoreplies set for the server from the database
        await interaction.response.defer()
        try:
            async with aiosqlite.connect('database.db') as db:
                async with db.execute("SELECT trigger, response FROM autoreplies WHERE guild_id = ?", (interaction.guild.id,)) as cursor:
                    rows = await cursor.fetchall()

        except Exception as e:
            logging.error(f"Error fetching autoreplies: {e}")
            return await interaction.edit_original_response(content=f"Error fetching autoreplies.")
            
        if not rows:
            return await interaction.edit_original_response(content="No autoreplies were set for this server.")
        
        # Format the autoreplies into a message
        entries = []
        for trigger, response in rows:
            # Check if the response is a URL or an attachment
            if response.startswith(
                (
                    "https://cdn.discordapp.com",
                    "https://tenor.com",
                    "https://imgur.com",
                    "https://giphy.com"
                )
            ) or response.endswith((".png", ".jpg", ".jpeg", ".gif", ".webp", ".mp4", ".webm", "mkv", ".mp3")):
                # Format the response as a hyperlink to the attachment or URL so Discord doesn't embed it in the message
                entries.append(f"> `{trigger}` → **[Attachment](<{response}>)**")

            elif response.startswith(("https://", "http://")):
                entries.append(f"> `{trigger}` → **[URL](<{response}>)**")
            
            else:
                entries.append(f"> `{trigger}` → {response}")

        msg = "\n".join(entries)
        await interaction.followup.send(content=f"**Autoreplies in this server:**\n\n{msg}")


# Registers the cog with the bot and creates the database table if it doesn't exist
async def setup(bot: commands.Bot):
    """Registers the cog with the bot"""
    async with aiosqlite.connect('database.db') as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS autoreplies (
            guild_id INTEGER NOT NULL,
            trigger TEXT NOT NULL,
            response TEXT NOT NULL,
            PRIMARY KEY (guild_id, trigger)
        )""")
        await db.commit()

    await bot.add_cog(AutoReply(bot))