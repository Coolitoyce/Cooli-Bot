import discord
import logging
import aiosqlite, sqlite3
from datetime import datetime
import time
import re
from discord.ext import commands, tasks
from discord import app_commands

class Reminder(commands.Cog):
    """Reminder cog to set reminders for users"""
    def __init__(self, bot: commands.Bot):
        # Initialize the cog with the bot instance
        self.bot = bot
        # Start the reminder checking loop
        self.check_reminders.start()
    
    
    # Background task to check for reminders every 30 seconds
    @tasks.loop(seconds=30)
    async def check_reminders(self):
        """Checks for any ongoing reminders"""
        # Get the current time in UTC and convert it to a timestamp
        now_dt = discord.utils.utcnow()
        now = int(now_dt.timestamp()) 
        # Connect to the database and fetch reminders that are due
        async with aiosqlite.connect("database.db") as db:
            async with db.execute("SELECT user_id, name FROM reminders WHERE remind_at <= ?", (now, )) as cursor:
                rows = await cursor.fetchall()

            for user_id, name in rows:
                try:
                    user = await self.bot.fetch_user(user_id)
                    if user is None:
                        logging.error(f"[Reminder Error] User ID {user_id} not found (None)")
                        continue
                    
                    # Send a DM to the user with the reminder message
                    embed = discord.Embed(title="Reminder",
                      description=f"Hey {user.mention}, You asked to be reminded of **{name}** {discord.utils.format_dt(now_dt, style='R')}",
                      colour=0x00b0f4,
                      timestamp=discord.utils.utcnow())

                    await user.send(embed=embed)

                except discord.Forbidden:
                    return logging.error(f"[Reminder Error] Cannot send DM to user {user_id} (forbidden).")                
                    
                except Exception as e:
                    logging.error(f"[Reminder Error] Failed to send reminder: {e}")

            # Delete reminders that are sent or expired
            await db.execute("DELETE FROM reminders WHERE remind_at <= ?", (now,))
            await db.commit()

    
    # Ensure the loop runs after the bot is ready
    @check_reminders.before_loop
    async def before_loop(self):
        await self.bot.wait_until_ready()

    # Define a group for reminder commands
    reminder_group = app_commands.Group(name="reminder", description="Reminder commands")

    #===================
    # REMIND ME COMMAND
    #===================
    @reminder_group.command(name="remindme")
    @app_commands.describe(remind_at="When do you want to be reminded? e.g: '5 minutes, 1 min 30 sec, 12 hours'", name="About what?")
    @app_commands.rename(remind_at="when", name="about")
    async def remindme(self, interaction: discord.Interaction, remind_at: str, name: str):
        """Reminds you of something after a certain amount of time"""

        time_in_s = 0
        if remind_at.find(" ") != -1: # Check if the remind_at string contains spaces (valid time format)
            
            # Split the time string into parts and calculate total seconds
            time_list = re.split(r'\s+', remind_at)
            for i in range(len(time_list)):
                # Check if the current part is a digit and the next part is a valid time unit
                if time_list[i].isdigit():
                    if time_list[i+1] in ("s", "sec", "secs", "second", "seconds"):
                        time_in_s += int(time_list[i])
                        
                    elif time_list[i+1] in ("m", "min", "mins", "minute", "minutes"):
                        time_in_s += int(time_list[i]) * 60

                    elif time_list[i+1] in ("h", "hr", "hrs", "hour", "hours"):
                        time_in_s += int(time_list[i]) * 60 * 60

                    elif time_list[i+1] in ("d", "day", "days"):
                        time_in_s += int(time_list[i]) * 60 * 60 * 24
                    
            if time_in_s > 0:
                # Calculate the remind_at timestamp by adding the time_in_s to the current time
                remind_at = time_in_s + int(time.time())
                # Convert the remind_at timestamp to a datetime object in UTC
                remind_at_datetime = datetime.fromtimestamp(remind_at).astimezone()
                
                async with aiosqlite.connect('database.db') as db:
                    # Insert the reminder into the database
                    try:
                        await db.execute(
                            "INSERT INTO reminders (user_id, name, remind_at) VALUES (?, ?, ?)",
                            (interaction.user.id, name, remind_at)
                        )
                        await db.commit()

                    # If the table does not exist, create it and then insert the reminder
                    except sqlite3.OperationalError:
                        async with aiosqlite.connect('database.db') as db:
                            await db.execute("""
                                CREATE TABLE IF NOT EXISTS reminders (
                                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                                    user_id INTEGER NOT NULL,
                                    remind_at INTEGER NOT NULL,
                                    name TEXT
                                )""")
                        await db.execute(
                            "INSERT INTO reminders (user_id, name, remind_at) VALUES (?, ?, ?)",
                            (interaction.user.id, name, remind_at)
                        )
                        await db.commit()

                    except Exception as e:
                        logging.error(f"[Reminder Error] Failed to insert reminder: {e}")
                        return await interaction.response.send_message(f"An error occurred while setting the reminder: {e}")              

                # Reply to the user with a confirmation message with the reminder details
                await interaction.response.send_message(f"Alright {interaction.user.name}, I'll remind you about **{name}** {discord.utils.format_dt(remind_at_datetime, style='R')}.")
                            
            else:
                await interaction.response.send_message("Please enter a valid time. Format: `1 minute/1 day/1 hr 30 min`")
        else:
            await interaction.response.send_message("Please enter a valid time. Format: `1 minute/1 day/1 hr 30 min`")
 
    #=========================
    # CLEAR REMINDERS COMMAND
    #=========================
    @reminder_group.command(name="clear")
    async def reminder_clear(self, interaction: discord.Interaction):
        """Clears ALL your reminders"""  
        # Check if the user has any reminders in the database
        async with aiosqlite.connect('database.db') as db:
            cursor = await db.execute("SELECT 1 FROM reminders WHERE user_id = ? LIMIT 1", (interaction.user.id, ))
            result = await cursor.fetchone()
            
            if result is None:
                await interaction.response.send_message("You don't have any reminders to clear.")

            else:
                # Delete all reminders for the user
                await db.execute("DELETE FROM reminders WHERE user_id = ?", (interaction.user.id, ))
                await db.commit()
                await interaction.response.send_message("Successfully cleared your active reminders.")
        

# Register the cog with the bot and create the database table if it doesn't exist
async def setup(bot: commands.Bot):
    """Registers the cog with the bot"""
    async with aiosqlite.connect('database.db') as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            remind_at INTEGER NOT NULL,
            name TEXT
        )""")
        await db.commit()  

    await bot.add_cog(Reminder(bot))