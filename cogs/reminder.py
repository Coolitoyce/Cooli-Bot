import discord
import logging
import re
import pytz, dateparser
import aiosqlite, sqlite3
from datetime import datetime
from dateutil.relativedelta import relativedelta
from itertools import product
from discord.ext import commands, tasks
from discord import app_commands
from typing import List

class ConfirmView(discord.ui.View):
    """A simple confirmation view with Cancel and Confirm buttons"""
    def __init__(self, user: discord.User, timeout: int = 30):
        super().__init__(timeout=timeout)
        self.value = None  # Store the user's choice
        self.user = user # The user who needs to confirm the action
        self.message = None # Store the message to disable the button for it later

    async def on_timeout(self):
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                child.disabled = True # Disable all buttons on timeout
        if self.message:
            try:
                await self.message.edit(view=self)  # Edit the message to disable buttons on timeout
            except discord.NotFound:
                logging.warning(f"[ConfirmView] Message {self.message} not found when trying to edit on timeout.")

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.user: # Check if the interaction user is the same as the user who needs to confirm
            return await interaction.response.send_message("This confirmation is not for you!", ephemeral=True)
        await interaction.response.send_message("Canceled.", ephemeral=True)
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                child.disabled = True # Disable all buttons when canceled
        self.value = False
        self.stop()

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.success)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.user:
            return await interaction.response.send_message("This confirmation is not for you!", ephemeral=True)
        await interaction.response.send_message("Confirmed.", ephemeral=True)
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                child.disabled = True # Disable all buttons when confirmed
        self.value = True
        self.stop()

class NewReminderView(discord.ui.View):
    def __init__(self, timeout: int = None, remind_at: str = None, about: str = None, og_reminder_creator: discord.User = None):
        super().__init__(timeout=timeout)
        self.message = None # Store the message to disable the button for it later
        self.remind_at = remind_at
        self.reminder_about = about
        self.og_reminder_creator = og_reminder_creator # The user who created the original reminder, if any


    @discord.ui.button(label="Remind me too", style=discord.ButtonStyle.secondary, emoji="🔔")
    async def remindme_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Check if the user already has the reminder in the database
        async with aiosqlite.connect('database.db') as db:
            cursor = await db.execute(
                "SELECT 1 FROM reminders WHERE remind_at = ? AND reminder_about = ? AND user_id = ?",
                (self.remind_at, self.reminder_about, interaction.user.id)
            )
            result = await cursor.fetchone()
            if result is None:
                try:
                    remind_at_datetime = datetime.fromtimestamp(self.remind_at) # Convert the remind_at timestamp to a datetime object
                    timezone = await get_user_timezone(self.og_reminder_creator) # Get the timezone of the original reminder creator
                    remind_at_datetime = timezone.localize(remind_at_datetime) # Localize the datetime to the original creator's timezone
                    now = datetime.now(tz=timezone) # Get the current time in the original creator's timezone
                    # Check if the reminder time is in the past
                    if now > remind_at_datetime:
                        logging.warning(f"[Reminder] User {interaction.user.name} ({interaction.user.id}) tried to set a reminder for a past time: Now = {now}, Reminder at = ({remind_at_datetime}).")
                        await interaction.response.send_message("This reminder has expired.", ephemeral=True)

                    else:
                        # Insert the reminder into the database for the user
                        await db.execute(
                            "INSERT INTO reminders (user_id, reminder_about, remind_at) VALUES (?, ?, ?)",
                            (interaction.user.id, self.reminder_about, self.remind_at)
                        )
                        await db.commit()
                        await interaction.response.send_message(
                            f"Alright {interaction.user.name}, I will also remind you about **{self.reminder_about}** {discord.utils.format_dt(remind_at_datetime, style='R')}.", ephemeral=True
                        )
                except ValueError as e:
                    logging.error(f"[Reminder Error] Failed to parse timestamp {self.remind_at}: {e}")
                    return await interaction.response.send_message("An unexpected error occurred while setting the reminder. Please try again.", ephemeral=True)

                except Exception as e:
                    logging.error(
                        f"[Reminder Error] Failed to insert reminder for user {interaction.user.name} ({interaction.user.id}) with time {self.remind_at}: {e}")
                    return await interaction.response.send_message(f"An unexpected error occurred while setting the reminder.", ephemeral=True)
                       

            else:
                await interaction.response.send_message("Error: Duplicate reminder. You already have a reminder set with the same time and reason.", ephemeral=True)

    @discord.ui.button(label="Cancel for me", style=discord.ButtonStyle.secondary, emoji="❌")
    async def cancel_reminder(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Check if the user already has the reminder in the database
        async with aiosqlite.connect('database.db') as db:
            cursor = await db.execute(
                "SELECT 1 FROM reminders WHERE remind_at = ? AND reminder_about = ? AND user_id = ?",
                (self.remind_at, self.reminder_about, interaction.user.id)
            )
            result = await cursor.fetchone()
            if result is None:
                await interaction.response.send_message("You don't have this reminder set.", ephemeral=True)
            else:
                try:
                    # Delete the reminder for the user
                    await db.execute(
                        "DELETE FROM reminders WHERE remind_at = ? AND reminder_about = ? AND user_id = ?",
                        (self.remind_at, self.reminder_about, interaction.user.id)
                    )
                    await db.commit()
                    logging.info(f"[Reminder] Deleted reminder for user {interaction.user.name} ({interaction.user.id}) with time {self.remind_at} and about {self.reminder_about}.")
                    await interaction.response.send_message(f"✅ Successfully canceled reminder for **{self.reminder_about}**", ephemeral=True)

                except Exception as e:
                    logging.error(f"[Reminder Error] Failed to delete reminder with id for user {interaction.user.name}({interaction.user.id}) with time {self.remind_at} and about {self.reminder_about}: {e}")
                    await interaction.response.send_message(f"Error: Failed to remove reminder.", ephemeral=True)


def get_datetime_format(remind_at: str):
    """Gets the datetime format from the user input string"""
    date_formats = [
        # Year first
        "%Y-%m-%d", "%Y/%m/%d", "%Y %m %d", # 2025-01-25, 2025/01/25, 2025 01 25
        "%Y-%b-%d", "%Y/%b/%d", "%Y %b %d", # 2025-Jan-25, 2025/Jan/25, 2025 Jan 25
        "%Y-%B-%d", "%Y/%B/%d", "%Y %B %d", # 2025-January-25, 2025/January/25, 2025 January 25
        "%Y-%m", "%Y/%m", "%Y %m", # 2025-01, 2025/01, 2025 01
        "%Y-%b", "%Y/%b", "%Y %b", # 2025-Jan, 2025/Jan, 2025 Jan
        "%Y-%B", "%Y/%B", "%Y %B", # 2025-January, 2025/January, 2025 January
        # Day first
        "%d-%m-%Y", "%d/%m/%Y", "%d %m %Y", # 25-01-2025, 25/01/2025, 25 01 2025
        "%d-%b-%Y", "%d/%b/%Y", "%d %b %Y", # 25-Jan-2025, 25/Jan/2025, 25 Jan 2025
        "%d-%B-%Y", "%d/%B/%Y", "%d %B %Y", # 25-January-2025, 25/January/2025, 25 January 2025
        "%d-%m", "%d/%m", "%d %m", # 25-01, 25/01, 25 01
        "%d-%b", "%d/%b", "%d %b", # 25-Jan, 25/Jan, 25 Jan
        "%d-%B", "%d/%B", "%d %B", # 25-January, 25/January, 25 January
        "%a", "%A", # Wed, Wednesday
        # Month first
        "%m-%d", "%m/%d", "%m %d", # 01-25, 01/25, 01 25
        "%b-%d", "%b/%d", "%b %d", # Jan-25, Jan/25, Jan 25
        "%B-%d", "%B/%d", "%B %d", # January-25, January/25, January 25
    ]
    time_formats = [
        "%I:%M %p", # 12:00 PM
        "%I:%M%p", # 12:00PM
        "%H:%M", # 12:00
        "%I %p", # 12 PM
        "%I%p" # 12PM
    ]
    # Combined format for both date and time format lists
    combined_formats = [f"{date} {time}" for date, time in product(date_formats, time_formats)]
    valid_formats = combined_formats + date_formats + time_formats
    
    for frmt in valid_formats: 
        try:
            # Try to parse the remind_at string with the current format
            datetime.strptime(remind_at, frmt) 
            return frmt

        except ValueError:
            continue
    return None

def parse_relative_time(remind_at: str, user_timezone: str):
    """Parsed the relative time string into a datetime object"""
    now = datetime.now(tz=user_timezone)
    result = now
    # Split the time string by (space) into componenets and get total time
    time_list = re.split(r'\s+', remind_at.strip())
    i = 0
    valid = False
    while i < len(time_list) - 1: # Ensure i+1 exists
        try:
            num = float(time_list[i])
            unit = time_list[i + 1].lower()
            if num <= 0:
                i += 2
                continue
            if unit in ("y", "year", "years"):
                result += relativedelta(years=int(num))
            elif unit in ("m", "month", "months"):
                result += relativedelta(months=int(num))
            elif unit in ("w", "week", "weeks"):
                result += relativedelta(weeks=int(num))
            elif unit in ("d", "day", "days"):
                result += relativedelta(days=int(num))
            elif unit in ("h", "hr", "hrs", "hour", "hours"):
                result += relativedelta(hours=int(num))
            elif unit in ("min", "mins", "minute", "minutes"):
                result += relativedelta(minutes=int(num))
            elif unit in ("s", "sec", "secs", "second", "seconds"):
                result += relativedelta(seconds=int(num))
            else:
                i += 1
                continue
            valid = True
            i += 2
        except (ValueError, IndexError):
            i += 1
            continue
    return result if valid else None

async def get_user_timezone(user: discord.User):
    """Gets the user's timezone from the database"""
    try:
        async with aiosqlite.connect('database.db') as db:
            cursor = await db.execute("SELECT timezone FROM user_timezones WHERE user_id = ?", (user.id, ))
            result = await cursor.fetchone()
            if result:
                timezone = result[0] # Get the timezone string from the result tuple
                timezone = pytz.timezone(timezone) # Convert the timezone string to a pytz timezone object
                return timezone if timezone else pytz.UTC # Return UTC if no timezone is set or if the timezone is None
            else:
                return pytz.UTC # Return UTC if no result is found

    except Exception as e:
        logging.error(f"[Reminder Error] Failed to get timezone for user {user.name} ({user.id}), timezone = {result}: {e}")
        return pytz.UTC
    

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
        now_datetime = discord.utils.utcnow()
        now = int(now_datetime.timestamp()) 
        # Connect to the database and fetch reminders that are due
        async with aiosqlite.connect("database.db") as db:
            async with db.execute("SELECT user_id, reminder_about FROM reminders WHERE remind_at <= ?", (now, )) as cursor:
                rows = await cursor.fetchall()

            for user_id, reminder_about in rows:
                try:
                    user = await self.bot.fetch_user(user_id)
                    if user is None:
                        logging.error(f"[Reminder Error] User ID {user_id} not found (None)")
                        continue
                    
                    # Send a DM to the user with the reminder message
                    embed = discord.Embed(title="Reminder",
                      description=f"Hey {user.mention}, You asked me to remind you of **{reminder_about}** {discord.utils.format_dt(now_datetime, style='R')}",
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
            if len(rows) > 0:
                logging.info(f"[Reminder] Checked reminders at {now_datetime}, deleted {len(rows)} reminders that were due.")

    
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
    @app_commands.describe(remind_at="When? e.g: '1 hour 30 min, Monday, tomorrow at 9 pm'.", about="About what?")
    @app_commands.rename(remind_at="when")
    async def remindme(self, interaction: discord.Interaction, remind_at: str, about: str):
        """Reminds you of something after a certain amount of time"""
        await interaction.response.defer()
        if len(about) > 30:
            logging.warning(f"[Reminder] User {interaction.user.name} ({interaction.user.id}) tried to set a reminder with too long reason: {about}")
            return await interaction.edit_original_response(content="Reminder reason is too long! Maximum length is 30 characters.")
        # Get the user's timezone
        user_timezone = await get_user_timezone(interaction.user)
        logging.info(f"[Reminder] User timezone: {user_timezone} for user {interaction.user.name} ({interaction.user.id})")
        # Get the current time in the user's timezone
        now = datetime.now(tz=user_timezone)
        # Get the datetime format from the user input
        format_str = get_datetime_format(remind_at)
        # Try relative time parsing
        relative_time = parse_relative_time(remind_at, user_timezone)
        # Try natural language parsing using dateparser
        natural_parsed = dateparser.parse(
            remind_at, settings={'TIMEZONE': user_timezone.zone, 'RETURN_AS_TIMEZONE_AWARE': True}
        ) 
        # Try datetime parsing if the user input is a valid datetime format
        if format_str:
            time_only_formats = ["%I:%M %p", "%I:%M%p", "%H:%M", "%I %p", "%I%p"] # Formats that only contain time, no date
            month_only_formats = ["%Y-%m", "%Y/%m", "%Y %m", "%Y-%b", "%Y/%b", "%Y %b", "%Y-%B", "%Y/%B", "%Y %B"] # Formats that only contain month and year
            formatstr_has_day_name = "%a" in format_str or "%A" in format_str # Check if the format string contains a day name
            try:
                remind_at_datetime = datetime.strptime(remind_at, format_str) # Parse the time with the correct format
                logging.info(f"[Reminder] Parsed datetime '{remind_at}' with format '{format_str}' for user {interaction.user.name} ({interaction.user.id})")

            except ValueError as e: 
                logging.error(f"[Reminder Error] Failed to parse datetime '{remind_at}' with format '{format_str}'")
                return await interaction.edit_original_response(
                    content=f"Invalid datetime format. Use formats like `2025-07-20`, `20-7 10 AM`, or `9 PM`."
                )
            # Set year, month, and day for time only formats or day formats
            if format_str in time_only_formats or formatstr_has_day_name: 
                remind_at_datetime = remind_at_datetime.replace(year=now.year, month=now.month, day=now.day)

             # Check if there's a day name in the user input
            if "%a" in format_str or "%A" in format_str:
                # Week days and their corresponding integer value
                WEEKDAYS = {
                    "monday": 0, "mon": 0,
                    "tuesday": 1, "tue": 1, "tues": 1,
                    "wednesday": 2, "wed": 2,
                    "thursday": 3, "thu": 3, "thurs": 3,
                    "friday": 4, "fri": 4,
                    "saturday": 5, "sat": 5,
                    "sunday": 6, "sun": 6
                }
                weekday_str = remind_at.split()[0].lower() # Get the week day string from user input
                target_weekday = WEEKDAYS.get(weekday_str) # Get the corresponding integer value of the week day
                if target_weekday is not None:
                    current_weekday = now.weekday() # Integer value of today
                    days_until = (target_weekday - current_weekday + 7) % 7 or 7 # Get the number of days until the target week day
                    # Construct the correct datetime
                    remind_at_datetime = datetime(
                        year=now.year,
                        month=now.month,
                        day=now.day,
                        hour=remind_at_datetime.hour,
                        minute=remind_at_datetime.minute,
                    ) + relativedelta(days=days_until)
                else:
                    logging.warning(f"[Reminder] Invalid weekday in '{remind_at}' for day format '{format_str}'")
                    return await interaction.edit_original_response(
                        content="Invalid day name. Use formats like `Monday 9:30 PM` or `Wednesday`."
                    )
            # Set default day to today for formats with month and year only
            if format_str in month_only_formats:
                remind_at_datetime = remind_at_datetime.replace(day=now.day)
            # Set default year to current year for formats with no year 
            if "%Y" not in format_str:
                remind_at_datetime = remind_at_datetime.replace(year=now.year)
            
            # Localize the datetime to the user's timezone
            remind_at_datetime = user_timezone.localize(remind_at_datetime)
            logging.info(f"[Reminder] Localized datetime '{remind_at_datetime}' for user {interaction.user.name} ({interaction.user.id}) with timezone {user_timezone}")

            # Handle past dates
            if now > remind_at_datetime:
                # Set day to next day for past time only formats
                if format_str in time_only_formats:
                    remind_at_datetime += relativedelta(days=1)
                # Set the day to the same day in next week if the target day is today 
                elif formatstr_has_day_name:
                    remind_at_datetime += relativedelta(days=7)
                # Set year to next year for past formats with no year
                elif "%Y" not in format_str:
                    remind_at_datetime += relativedelta(years=1)

                else:
                    logging.warning(f"[Reminder] Rejected past datetime: '{remind_at}' = {remind_at_datetime}")
                    return await interaction.edit_original_response(content="Please enter a valid time in the future.")

        # Try relative time parsing if the custom datetime parsing didn't work    
        elif relative_time:
            remind_at_datetime = relative_time
            if not remind_at_datetime or now > remind_at_datetime:
                logging.warning(f"[Reminder] Invalid or past relative time: '{remind_at}', result={remind_at_datetime}")
                return await interaction.edit_original_response(
                    content="Invalid relative time. Use formats like `5 minutes`, `1.5 hours`, `2 days`, or `1 month`."
                )
        # Try natural language parsing if the custom datetime parsing and relative time parsing didn't work
        elif natural_parsed:
            remind_at_datetime = natural_parsed
            if now > natural_parsed: # If parsing using dateparser has failed
                logging.warning(f"[Reminder] Invalid or past dateparser time: '{remind_at}', result={remind_at_datetime}")
                return await interaction.edit_original_response(
                    content="Invalid time format or time provided is in the past. Use formats like:\n```3 days\n5 hours 30 min\n2025-07-20 9:00 PM\n20-7 10 AM\n2025-7-20\n9 PM\nWednesday```"
                )
        # If everything fails
        else:
            logging.warning(f"[Reminder] Invalid time format: '{remind_at}'")
            return await interaction.edit_original_response(
                content="Invalid time format. Use formats like:\n```3 days\n5 hours 30 min\n2025-07-20 9:00 PM\n20-7 10 AM\n2025-7-20\n9 PM\nWednesday```"
            )
        
        # Finally convert the remind_at datetime object to a UTC timestamp for storage
        remind_at = int(remind_at_datetime.astimezone(pytz.UTC).timestamp())
        async with aiosqlite.connect('database.db') as db:
            # Insert the reminder into the database
            try:
                cursor = await db.execute(
                    "SELECT reminder_about FROM reminders WHERE remind_at = ? AND user_id = ?",
                    (remind_at, interaction.user.id)
                )
                result = await cursor.fetchall()
                for (reminder_about, ) in result:
                    # Check if the reminder already exists for the user
                    if about.strip().lower() == reminder_about.strip().lower():
                        return await interaction.edit_original_response(
                            content="Error: Duplicate reminder. You already have a reminder set with the same time and reason."
                        )

                await db.execute(
                    "INSERT INTO reminders (user_id, reminder_about, remind_at) VALUES (?, ?, ?)",
                    (interaction.user.id, about, remind_at)
                )
                logging.info(f"[Reminder] Inserted reminder: user={interaction.user.id}, about='{about}', remind_at={remind_at}")
                await db.commit()

            except Exception as e:
                logging.error(f"[Reminder Error] Failed to insert reminder: {e}")
                return await interaction.edit_original_response(content=f"An unexpected error occurred while setting the reminder.")

        embed = discord.Embed(title="New Reminder", timestamp=discord.utils.utcnow(), color=discord.Color.blurple())
        embed.description = f"Alright {interaction.user.name}, I'll remind you about **{about}** {discord.utils.format_dt(remind_at_datetime, style='R')}."
        view = NewReminderView(remind_at=remind_at, about=about, og_reminder_creator=interaction.user)
        await interaction.followup.send(embed=embed, view=view)
        if user_timezone == pytz.UTC:
            await interaction.followup.send(
                "**Note:** You do not have a timezone set! Default is UTC.\nPlease make sure to set your timezone using `/reminder timezone` else the reminder may not trigger at the expected time.", ephemeral=True)

    #=========================
    # REMOVE REMINDER COMMAND
    #=========================
    async def reminder_autocomplete(self, interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
        """Autocompletes timezone input"""
        matches =  [
            app_commands.Choice(name=tz, value=tz)
            for tz in (pytz.all_timezones) if current.lower() in tz.lower() and len(tz) < 100
        ]
        return matches[:25]
        
    @reminder_group.command(name="remove")
    @app_commands.describe(id="ID of the reminder to remove")
    async def reminder_remove(self, interaction: discord.Interaction, id: int):
        """Removes a reminder by its ID"""
        async with aiosqlite.connect('database.db') as db:
            cursor = await db.execute("SELECT 1 FROM reminders WHERE id = ? AND user_id = ?", (id, interaction.user.id))
            result = await cursor.fetchone()

            if result is None:
                return await interaction.response.send_message("No reminder for you was found with that ID.")

            try:
                await db.execute("DELETE FROM reminders WHERE id = ? AND user_id = ?", (id, interaction.user.id))
                await db.commit()
            except Exception as e:
                logging.error(f"[Reminder Error] Failed to delete reminder with id {id} for user {interaction.user.name}({interaction.user.id}): {e}")
                return await interaction.response.send_message(f"Error: Failed to remove reminder with ID: {id}.")

        await interaction.response.send_message(f"Successfully removed reminder with ID: {id}.")

    #=========================
    # CLEAR REMINDERS COMMAND
    #=========================
    @reminder_group.command(name="clear")
    async def reminder_clear(self, interaction: discord.Interaction):
        """Clears ALL your active reminders""" 
        await interaction.response.defer() 
        view = ConfirmView(user=interaction.user)
        embed = discord.Embed(
            title="Pending Confirmation",
            description="Are you sure you want to clear all of your reminders?",
            color=discord.Color.default()
        )
        # Check if the user has any reminders in the database
        async with aiosqlite.connect('database.db') as db:
            cursor = await db.execute("SELECT 1 FROM reminders WHERE user_id = ? LIMIT 1", (interaction.user.id, ))
            result = await cursor.fetchone()
            
            if result is None:
                return await interaction.edit_original_response(content="You don't have any reminders to clear.")

            else:
                view.message = await interaction.followup.send(content=interaction.user.mention, embed=embed, view=view, wait=True)  # Send the confirmation message
                await view.wait() # Wait for the confirmation view to finish
                if view.value is None:
                    embed.color = discord.Color.red()
                    embed.title = "Timed Out"
                    embed.description = f"~~{embed.description}~~" 
                    return await interaction.edit_original_response(embed=embed, view=view)  # Edit the original response to indicate timeout

                if view.value == False:
                    embed.color = discord.Color.red()
                    embed.title = "Action Canceled"
                    embed.description = f"~~{embed.description}~~" 
                    return await interaction.edit_original_response(embed=embed, view=view)  # Edit the original response to indicate cancellation
                
                embed.title = "Action Confirmed"
                embed.color = discord.Color.green()
                await interaction.edit_original_response(embed=embed, view=view)
                try:
                    # Delete all reminders for the user
                    await db.execute("DELETE FROM reminders WHERE user_id = ?", (interaction.user.id, ))
                    await db.commit()

                except Exception as e:
                    logging.error(f"[Reminder Error] Failed to clear reminders for user {interaction.user}({interaction.user.id}): {e}")
                    embed.title = "Action Failed"
                    embed.description = "Error: Failed to clear your reminders."
                    embed.color = discord.Color.red()
                    return await interaction.edit_original_response(embed=embed, view=None)

        embed.description = "Successfully cleared your reminders."
        await interaction.edit_original_response(embed=embed, view=None)

    #========================
    # LIST REMINDERS COMMAND
    #========================
    @reminder_group.command(name="list")
    async def reminder_list(self, interaction: discord.Interaction):
        """View all your active reminders"""
        await interaction.response.defer()
        try:
            async with aiosqlite.connect('database.db') as db:
                cursor = await db.execute("SELECT id, remind_at, reminder_about FROM reminders WHERE user_id = ?", (interaction.user.id, ))
                rows = await cursor.fetchall()

        except Exception as e:
            logging.error(f"[Reminder Error] Error fetching reminders for user {interaction.user.name}({interaction.user.id}): {e}")
            return await interaction.edit_original_response(content=f"Error fetching reminders.")
            
        if not rows:
            return await interaction.edit_original_response(content="You don't have any reminders to view.")
        
        entries = []
        for id, remind_at, reminder_about in rows:
            try:
                remind_at = int(remind_at) # Ensure remind_at is an integer timestamp
                user_timezone = await get_user_timezone(interaction.user) # Get the user's timezone
                remind_at_datetime = datetime.fromtimestamp(remind_at, tz=pytz.UTC).astimezone(user_timezone) # Convert the timestamp to a datetime object in the user's timezone
                entries.append(f"> ID: {id} - {discord.utils.format_dt(remind_at_datetime, 'R')} - About: **{reminder_about}**")
            except Exception as e:
                logging.error(f"[Reminder Error] Failed to view reminder with id: {id}, time: {remind_at}: {e}")

            
        msg = "\n".join(entries)
        user_timezone = await get_user_timezone(interaction.user) # Get the user's timezone
        utc_offset = user_timezone.utcoffset(datetime.now()).total_seconds() / 3600 # Get the UTC offset in hours
        utc_offset = ('+' + str(utc_offset)) if utc_offset > 0 else utc_offset # Format the UTC offset with a '+' sign if it's positive
        if user_timezone == pytz.UTC:
            msg += "\n\n**Timezone:** UTC (Default).\nNote: Set your timezone using `/reminder timezone`." # Add a note about the user's timezone
        else: 
            msg += f"\n\n**Timezone:** {user_timezone.zone} ({utc_offset} UTC)" # Add the user's timezone to the message
        embed = discord.Embed(title="Reminders List", color=discord.Color.green(), timestamp=discord.utils.utcnow())
        embed.description = msg
        await interaction.edit_original_response(embed=embed)

    #======================
    # SET TIMEZONE COMMAND
    #======================
    async def timezone_autocomplete(self, interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
        """Autocompletes timezone input"""
        matches =  [
            app_commands.Choice(name=tz, value=tz)
            # Show timezones that match the current input and are less than 100 characters long
            for tz in (pytz.all_timezones) if current.lower() in tz.lower() and len(tz) < 100
        ]
        # Limit the number of options to 25 to avoid hitting Discord's limit
        return matches[:25] 
        
    @reminder_group.command(name="timezone")
    @app_commands.describe(timezone="Your timezone (e.g., Africa/Cairo, America/New_York). Just type and it will autocomplete for you.")
    @app_commands.autocomplete(timezone=timezone_autocomplete)
    async def settimezone(self, interaction: discord.Interaction, timezone: str):
        """Set your preferred timezone for your reminders"""
        await interaction.response.defer()
        try:
            # Check if the timezone is valid
            pytz.timezone(timezone)

        except pytz.exceptions.UnknownTimeZoneError:
            logging.warning(f"[Reminder] Invalid timezone input: user={interaction.user.id}, timezone='{timezone}'")
            return await interaction.edit_original_response(
                content="Invalid timezone. Use a valid timezone like `Europe/Helsinki` or `America/New_York`. Try the autocomplete!"
            )
            
        utc_offset = pytz.timezone(timezone).utcoffset(datetime.now()).total_seconds() / 3600 # Get the UTC offset in hours
        utc_offset = ('+' + str(utc_offset)) if utc_offset > 0 else utc_offset # Format the UTC offset with a '+' sign if it's positive

        async with aiosqlite.connect('database.db') as db:
            try:
                # Insert or replace the user's timezone in the database
                await db.execute(
                    "INSERT OR REPLACE INTO user_timezones (user_id, timezone) VALUES (?, ?)",
                    (interaction.user.id, timezone)
                )
                await db.commit()
                logging.info(f"[Reminder] Set timezone for user {interaction.user.id}: {timezone}, {utc_offset} hours offset")

            except Exception as e:
                logging.error(f"[Reminder Error] Failed to set timezone for user {interaction.user.id}: {e}")
                return await interaction.edit_original_response(
                    content=f"An unexpected error occurred while setting timezone."
                )

        embed = discord.Embed(
            title="Timezone Set",
            description=f"Your timezone is now set to **{timezone} ({utc_offset} UTC)**.",
            color=discord.Color.green(),
            timestamp=discord.utils.utcnow()
        )
        await interaction.edit_original_response(embed=embed)



# Register the cog with the bot and create the database tables if they don't exist
async def setup(bot: commands.Bot):
    """Registers the cog with the bot"""
    async with aiosqlite.connect('database.db') as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            remind_at INTEGER NOT NULL,
            reminder_about TEXT
        )""")
        await db.execute("""
        CREATE TABLE IF NOT EXISTS user_timezones (
            user_id INTEGER NOT NULL PRIMARY KEY,
            timezone TEXT NOT NULL
        )""")
        await db.commit()  

    await bot.add_cog(Reminder(bot))