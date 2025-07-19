import logging
import aiosqlite, sqlite3
from discord.ext import commands


# This cog contains owner-only commands to manage the SQLite database for the bot
class DBAdmin(commands.Cog):
    """Cog for managing the SQLite database."""
    def __init__(self, bot: commands.Bot):
        # Initialize the cog with the bot instance
        self.bot = bot
    
    # This command shows the data in a specified table of the database as a message 
    @commands.command(name="showdb")
    @commands.is_owner()
    async def show_db(self, ctx: commands.Context, name: str):
        async with aiosqlite.connect('database.db') as db:
            try:
                # Fetch all rows from the specified table
                cursor = await db.execute(f"SELECT * FROM {name}")
                rows = await cursor.fetchall()
                
                if not rows:
                    return await ctx.reply(f"No data found in table {name}.")
                
                # Format the response with column names and data
                response = f"Data in table {name}:\nColumns: {[description[0] for description in cursor.description]}\nData:\n"
                
                # Convert each row to a string and add it to the response
                for row in rows:
                    response += str(row) + "\n" 
                
                # Reply with the formatted data
                await ctx.reply(response)
            
            except sqlite3.OperationalError as e:
                logging.error(f"[DB Admin] Show DB command - Error accessing table {name}: {e}")
                return await ctx.reply(f"Error accessing the table: {e}")
            
            except Exception as e:
                logging.error(f"[DB Admin] Show DB command - Unexpected error: {e}")
                return await ctx.reply(f"An unexpected error occurred: {e}")


    # This command deletes a table from the database
    @commands.command(name="deletedb")
    @commands.is_owner()
    async def delete_db(self, ctx: commands.Context, name: str):
        async with aiosqlite.connect('database.db') as db:
            try:
                await db.execute(f"DROP TABLE {name}")
                await db.commit()
            
            except Exception as e: 
                logging.error(f"[DB Admin] Delete DB command - Error deleting table {name}: {e}")
                return await ctx.reply(f"Error when deleting the table: {e}")

            await ctx.reply(f"Successfully deleted table {name}")
            logging.info(f"[DB Admin] deleted table {name} using command.")

    # This command creates a table in the database with the specified name and columns
    @commands.command(name="createdb")
    @commands.is_owner()
    async def create_db(self, ctx: commands.Context, name: str, *args):
        query = f"CREATE TABLE IF NOT EXISTS {name} ("
        try:
            # Collect column definitions from all arguments
            columns = []
            for arg in args:
                columns.extend(str(arg).split(","))
            
            for index, item in enumerate(columns):
                if index == len(columns) - 1:
                    query += f"{item}"
                else:
                    query += f"{item},"
                    
        except Exception as e:
            logging.error(f"[DB Admin] Create DB command - Error formatting the database rows entered: {e}")
            return await ctx.reply(f"Error formatting the database rows entered: {e}")

        query += ")"

        async with aiosqlite.connect('database.db') as db:
            try:
                await db.execute(query)
                await db.commit()
            
            except Exception as e: 
                return await ctx.reply(f"Error creating the table: {e}")
            
            await ctx.reply(f"Successfully created table {name} if it didn't exist.")
            logging.info(f"[DB Admin] created table {name} using command with columns: {', '.join(columns)}.")

    @commands.command(name="renamecol")
    @commands.is_owner()
    async def rename_column(self, ctx: commands.Context, table_name: str, column_name: str, new_name: str):
        query = f"ALTER TABLE {table_name} RENAME COLUMN {column_name} TO {new_name}"
        try:
            async with aiosqlite.connect('database.db') as db:
                await db.execute(query)
                await db.commit()

        except Exception as e: 
            return await ctx.reply(f"Error renaming column: {e}")
            
        await ctx.reply(f"Successfully renamed column {column_name} to {new_name} in table {table_name}")
        logging.info(f"[DB ADmin] renamed column {column_name} to {new_name} in table {table_name} using command.")

# Register the cog with the bot
async def setup(bot: commands.Bot):
    """Registers the cog with the bot"""
    await bot.add_cog(DBAdmin(bot))