import disnake as discord
from disnake.ext import commands
import sqlite3

db = sqlite3.connect('cogs/databases/db.db')
cur = db.cursor()
cur.execute('CREATE TABLE IF NOT EXISTS log_key (discord_id, canvas, key)')
cur.close()

CANVASES = [76, 77, 78, 79, 80]

class Points(commands.Cog):
    def __init__(self, bot: discord.Bot):
        self.bot = bot
    
    logkey = commands.SlashCommandGroup(name='logkey', description='Commands for managing log keys')

    @logkey.command(name='set', description='Set your log key')
    @discord.option(name='canvas', type=int, description='The canvas to set the log key for', required=True, choices=CANVASES)
    async def set(self, ctx: discord.ApplicationCommandInteraction, canvas: str):
        modal = LogKeyModal(canvas=canvas)
        await ctx.send_modal(modal)

    @logkey.command(name='get', description='Get your log key')
    @commands.option(name='canvas', type=int, description='The canvas to get the log key for', required=True, choices=CANVASES)
    async def get(self, ctx: discord.ApplicationCommandInteraction, canvas: str):
        cur = db.cursor()
        key = cur.execute('SELECT key FROM log_key WHERE discord_id = ? AND canvas = ?', (ctx.author.id, canvas)).fetchone()
        cur.close()
        if key is None:
            await ctx.response.send_message('No log key set', ephemeral=True)
        else:
            await ctx.response.send_message(f'Your log key is {key[0]}', ephemeral=True)
    
    @logkey.command(name='list', description='List which canvases you have log keys for')
    async def list(self, ctx: discord.ApplicationCommandInteraction):
        cur = db.cursor()
        canvases = cur.execute('SELECT canvas FROM log_key WHERE discord_id = ?', (ctx.author.id,)).fetchall()
        cur.close()
        if len(canvases) == 0:
            await ctx.response.send_message('No log keys set', ephemeral=True)
        else:
            await ctx.response.send_message(f'You have log keys for canvases {", ".join([str(canvas[0]) for canvas in canvases])}', ephemeral=True)
    
    @logkey.command(name='delete', description='Delete your log key')
    @commands.option(name='canvas', type=int, description='The canvas to delete the log key for', required=True, choices=CANVASES)
    async def delete(self, ctx: discord.ApplicationCommandInteraction, canvas: str):
        cur = db.cursor()
        cur.execute('DELETE FROM log_key WHERE discord_id = ? AND canvas = ?', (ctx.author.id, canvas))
        db.commit()
        cur.close()
        await ctx.response.send_message('Log key deleted', ephemeral=True)


class LogKeyModal(discord.ui.Modal):
    def __init__(self, canvas: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.key = None
        self.canvas = canvas
        self.add_item(discord.ui.InputText(label="Log Key", placeholder="Enter your log key", style=discord.InputTextStyle.short))
    
    async def callback(self, interaction: discord.Interaction):
        self.key = self.children[0].value
        cur = db.cursor()
        cur.execute('DELETE FROM log_key WHERE discord_id = ? AND canvas = ?', (interaction.user.id, self.canvas))
        cur.execute('INSERT INTO log_key VALUES (?, ?, ?)', (interaction.user.id, self.canvas, self.key))
        db.commit()
        cur.close()
        await interaction.response.send_message('Added log key for canvas ' + str(self.canvas), ephemeral=True)


def setup(bot: commands.Bot):
    bot.add_cog(Points(bot))