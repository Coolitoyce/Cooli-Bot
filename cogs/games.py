import discord
import logging
import aiohttp
import html
import re
from datetime import datetime
from discord import app_commands
from discord.ext import commands
from config import RAWG_API_KEY  # Import the RAWG API key from config.py
from random import choice as random_choice

class ConfirmView(discord.ui.View):
    """A simple confirmation view with Cancel and Confirm buttons"""
    def __init__(self, user: discord.User, timeout: int = 30):
        super().__init__(timeout=timeout)
        self.value = None  # Store the user's choice
        self.user = user # The user who needs to confirm the action
        self.message = None # Store the message to edit the button's state later

    async def on_timeout(self):
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                child.disabled = True # Disable all buttons on timeout
        if self.message:
            try:
                await self.message.edit(view=self)  # Edit the message to disable buttons on timeout
            except discord.NotFound:
                logging.warning(f"Message {self.message} not found when trying to edit on timeout.")

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.danger)
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

class RPSView(discord.ui.View):
    def __init__(self, user: discord.User, timeout: int = 60):
        super().__init__(timeout=timeout)
        self.user = user
        self.player_choice = None  # Store the user's choice
        self.message = None  # Store the message to edit the button's state later
    
    async def on_timeout(self):
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                child.disabled = True
        if self.message:
            try:
                await self.message.edit(view=self)  # Edit the message to disable buttons on timeout
            except discord.NotFound:
                logging.warning("Message not found when trying to edit on timeout.")

    @discord.ui.button(label="Rock", emoji="🪨", style=discord.ButtonStyle.blurple, custom_id='rps:rock')
    async def rock(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.user:
            await interaction.response.send_message("It's not your turn.", ephemeral=True)
        await interaction.response.defer(thinking=False)
        self.player_choice = "🪨 Rock"  
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                child.disabled = True
        self.stop()
    
    @discord.ui.button(label="Paper", emoji="📄", style=discord.ButtonStyle.blurple, custom_id='rps:paper')
    async def paper(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.user:
            await interaction.response.send_message("It's not your turn.", ephemeral=True)
        await interaction.response.defer(thinking=False)
        self.player_choice = "📄 Paper"
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                child.disabled = True
        self.stop()
    
    @discord.ui.button(label="Scissors", emoji="✂️", style=discord.ButtonStyle.blurple, custom_id='rps:scissors')
    async def scissors(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.user:
            await interaction.response.send_message("It's not your turn.", ephemeral=True)
        await interaction.response.defer(thinking=False)
        self.player_choice = "✂️ Scissors"
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                child.disabled = True
        self.stop()


class Games(commands.Cog):
    """Games cog for game commands"""
    def __init__(self, bot: commands.Bot):
    # Initialize the cog with the bot instance
        self.bot = bot

    @commands.hybrid_command(name="game", with_app_command=True)
    @app_commands.describe(title="Title of the game to search for")
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

    games_group = app_commands.Group(name="games", description="Games related commands")
    games_group.guild_only = True  
    
    @games_group.command(name="rps")
    @app_commands.describe(member="The member to play with")
    async def rps(self, interaction: discord.Interaction, member: discord.Member):
        """Play a nice game of Rock, Paper, Scissors with a member"""
        if member.bot and member.id != interaction.guild.me.id:
            return await interaction.response.send_message("You can't play with a bot _other than me_.", ephemeral=True)
        if member == interaction.user:
            return await interaction.response.send_message("You can't play with yourself.", ephemeral=True)
        await interaction.response.defer()
        player1 = interaction.user 
        player2 = member
        if player2 != interaction.guild.me: # Check if the member is not the bot itself
            confirmview = ConfirmView(user=player2) # Create a confirmation view for the second player
            embed = discord.Embed(title="Pending Confirmation", description=f"{player1.mention} is challenging you to a game of Rock, Paper, Scissors! Do you accept?", color=discord.Color.default())
            confirmview.message = await interaction.followup.send(content=player2.mention, embed=embed, view=confirmview, wait=True)  # Send the confirmation message
            await confirmview.wait() # Wait for the confirmation view to finish
            if confirmview.value is None:
                embed.color = discord.Color.red()
                embed.title = "Timed Out"
                embed.description = f"~~{embed.description}~~" 
                return await interaction.edit_original_response(embed=embed, view=confirmview)  # Edit the original response to indicate timeout

            if confirmview.value == False:
                embed.color = discord.Color.red()
                embed.title = "Action Canceled"
                embed.description = f"~~{embed.description}~~" 
                return await interaction.edit_original_response(embed=embed, view=confirmview)  # Edit the original response to indicate cancellation
            
            embed.color = discord.Color.green()
            embed.title = "Action Confirmed"
            await interaction.edit_original_response(embed=embed, view=confirmview)  # Edit the original response to indicate confirmation
        
        # If the member is the bot itself, skip confirmation
        embed = discord.Embed(
            title=f"[RPS] {player1.display_name} vs {player2.display_name}",
            description=f"{player1.display_name} is selecting...\n{player2.display_name} is waiting...",
            color=0xf0ff80
        )
        gameview = RPSView(user=player1) # Create a view with rock, paper, scissors buttons for the first player to select their choice
        game_msg = await interaction.followup.send(embed=embed, view=gameview, wait=True) # Send the message with the buttons
        gameview.message = game_msg # Store the message in the view to edit the button's state later
        await gameview.wait() # Wait for the first player to make their choice
        player1_choice = gameview.player_choice # Get the first player's choice
        if player1_choice is None:
            embed.description = f"Welp, {player1.display_name} did not select in time. Game canceled."
            return await game_msg.edit(embed=embed, view=gameview) # Edit the message to indicate time out
        
        embed.description = f"{player1.display_name} has selected.\n{player2.display_name} is selecting..."
        if player2 != interaction.guild.me: # If the second player is not the bot itself, wait for their choice
            gameview = RPSView(user=player2)
            gameview.message = game_msg # The message which has the buttons
            await game_msg.edit(embed=embed, view=gameview) # Edit the message to show that the first player is done selecting and wait for the second player's choice
            await gameview.wait()
            player2_choice = gameview.player_choice
            if player2_choice is None:
                embed.description = f"Welp, {player2.display_name} did not select in time. Game canceled."
                return await game_msg.edit(embed=embed, view=gameview)
        else: # If the second player is the bot itself, Make the bot randomly choose
            player2_choice = random_choice(["🪨 Rock", "📄 Paper", "✂️ Scissors"]) 
        embed.description = f"{player1.display_name} selected {player1_choice}.\n{player2.display_name} selected {player2_choice}."
        await game_msg.edit(embed=embed, view=gameview)
        
        choices = {
            "🪨 Rock": "✂️ Scissors",
            "📄 Paper": "🪨 Rock",
            "✂️ Scissors": "📄 Paper"
        }
        if player1_choice == player2_choice:
            if player2 == interaction.guild.me:
                ending_sentence = random_choice(
                    [
                        "Great minds think alike.\n⚔️ It's a draw!",
                        "Woah, you chose the same option as me? Are you a genius?! Are you onto me?!\n⚔️ It's a draw!"
                    ]
                )
            ending_sentence = "Great minds think alike.\n⚔️ It's a draw!"
            return await interaction.followup.send(content=f"{ending_sentence}")

        # Check if player1's choice beats player2's choice
        # if the value of player1_choice in the choices dictionary matches player2_choice, then player1 wins (or vice versa)
        if choices[player1_choice] == player2_choice: 
            winner = player1.display_name
            loser = player2.display_name
        else:
            winner = player2.display_name
            loser = player1.display_name
        
        game_outcomes = {
            ("🪨 Rock", "✂️ Scissors"): [
                f"{winner} smashed {loser}'s scissors into shiny dust!",
                f"{loser} tried to cut a rock... classic mistake.",
                f"Scissors met their rocky demise, courtesy of {winner}."
            ],
            ("📄 Paper", "🪨 Rock"): [
                f"{winner} wrapped up {loser}'s rock like a sad birthday gift.",
                f"Rock was no match for a well-placed piece of paper.",
                f"Rock was buried beneath paper's might."
            ],
            ("✂️ Scissors", "📄 Paper"): [
                f"{winner} sliced {loser}'s dreams — and their paper.",
                f"{loser} brought paper to a scissors fight.",
                f"{winner} snipped {loser}'s paper into confetti!"
            ]
        }
        # Pick a random ending sentence based on the choices made
        if (player1_choice, player2_choice) in game_outcomes:
            ending_sentence = random_choice(game_outcomes[(player1_choice, player2_choice)])
        else:
            ending_sentence = random_choice(game_outcomes[(player2_choice, player1_choice)])
        
        # Send the final result message with the winner
        await interaction.followup.send(content=f"{ending_sentence}\n 🏆 **{winner}** wins!")



# Register the cog with the bot 
async def setup(bot: commands.Bot):
    """Registers the cog with the bot"""
    await bot.add_cog(Games(bot))