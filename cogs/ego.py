import disnake as discord
from disnake.ext import commands, tasks
import sqlite3
import dotenv
import os
import aiohttp

dotenv.load_dotenv()
pxls_auth = os.environ['PXLS_AUTH']

db = sqlite3.connect('cogs/databases/db.db')
cur = db.cursor()
cur.execute('CREATE TABLE IF NOT EXISTS usernames (discord_id, pxls_username)')
cur.execute('CREATE TABLE IF NOT EXISTS egos (pxls_username, ego)')
cur.execute('CREATE TABLE IF NOT EXISTS canvasegos (pxls_username, ego)')
db.commit()
cur.close()

class Ego(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.background_task.start()
    
    async def fetch_stats(self):
        headers = {
            "x-pxls-cfauth": pxls_auth
        }
        timeout = aiohttp.ClientTimeout(sock_connect=10, sock_read=10)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get("https://pxls.space/stats/stats.json", headers=headers) as response:
                return await response.json()
    
    async def parse_ego(self, username: str):
        lst = self.stats['toplist']['alltime']
        for i in range(len(lst)):
            if lst[i]['username'] == username:
                return int(lst[i]['pixels']) // 1000
        return -1

    async def parse_canvas_ego(self, username: str):
        lst = self.stats['toplist']['canvas']
        for i in range(len(lst)):
            if lst[i]['username'] == username:
                return int(lst[i]['pixels']) // 1000
        return -1

    async def parse_egos(self):
        c = db.cursor()
        users = c.execute('SELECT * FROM egos').fetchall()
        print(users)
        for user in users:
            user_count = await self.parse_ego(user[0])
            if user_count == -1:
                print(f"Failed to parse ego for {user[0]}")
                continue
            if user_count > int(user[1]):
                c.execute('UPDATE egos SET ego = ? WHERE pxls_username = ?', (user_count, user[0]))
                db.commit()
                discord_id = c.execute('SELECT discord_id FROM usernames WHERE pxls_username = ?', (user[0],)).fetchone()
                member = await self.bot.fetch_user(discord_id[0])
                await member.send(f"{user[0]} has reached {user_count}k pixels")
            c.execute('UPDATE egos SET ego = ? WHERE pxls_username = ?', (user_count, user[0]))
        db.commit()
        c.close()

    async def parse_canvas_egos(self):
        c = db.cursor()
        users = c.execute('SELECT * FROM canvasegos').fetchall()
        print(users)
        for user in users:
            user_count = await self.parse_canvas_ego(user[0])
            if user_count == -1:
                print(f"Failed to parse ego for {user[0]}")
                continue
            if user_count > int(user[1]):
                c.execute('UPDATE canvasegos SET ego = ? WHERE pxls_username = ?', (user_count, user[0]))
                db.commit()
                discord_id = c.execute('SELECT discord_id FROM usernames WHERE pxls_username = ?', (user[0],)).fetchone()
                member = await self.bot.fetch_user(discord_id[0])
                await member.send(f"{user[0]} has reached {user_count}k canvas pixels")
            c.execute('UPDATE canvasegos SET ego = ? WHERE pxls_username = ?', (user_count, user[0]))
        db.commit()
        c.close()

    def cog_unload(self):
        self.background_task.cancel()
    
    @tasks.loop(seconds=900)
    async def background_task(self):
        # Fetch the stats every 15 minutes
        self.stats = await self.fetch_stats()
        await self.parse_egos()
        await self.parse_canvas_egos()
    
    @background_task.before_loop
    async def before_background_task(self):
        import asyncio
        import time
        self.stats = await self.fetch_stats()
        current = time.time()
        # Wait until the next 15 minute mark, plus 30 seconds to ensure the stats are updated
        wanted = current - (current % 900) + 930
        print('Waiting for ', wanted - current, 's to fetch stats')
        await asyncio.sleep(wanted - current)
    
    @commands.slash_command(name="egotrack", description="Get notifications when you need to update your ego")
    async def egotrack(self, ctx: discord.ApplicationCommandInteraction):
        # Check if the username is in the database
        c = db.cursor()
        username = c.execute('SELECT pxls_username FROM usernames WHERE discord_id = ?', (str(ctx.author.id),)).fetchone()
        if username is None:
            c.close()
            await ctx.response.send_message("You need to link your username first (/user link)")
            return
        username = username[0]
        # Add the username to the egos table
        c.execute('INSERT INTO egos VALUES (?, ?)', (username, 0))
        db.commit()
        c.close()
        # Respond to the user
        try:
            await ctx.author.send("Ego tracking enabled")
        except discord.Forbidden:
            await ctx.response.send_message("You have DMs disabled, so I can't send ego tracking notifications")
            return
        await ctx.response.send_message("Ego tracking enabled")

    @commands.slash_command(name="egotrack_canvas", description="Get notifications when you need to update your canvas count ego")
    async def egotrack_canvas(self, ctx: discord.ApplicationCommandInteraction):
        # Check if the username is in the database
        c = db.cursor()
        username = c.execute('SELECT pxls_username FROM usernames WHERE discord_id = ?', (str(ctx.author.id),)).fetchone()
        if username is None:
            c.close()
            await ctx.response.send_message("You need to link your username first (/user link)")
            return
        username = username[0]
        # Add the username to the egos table
        c.execute('INSERT INTO canvasegos VALUES (?, ?)', (username, 0))
        db.commit()
        c.close()
        # Respond to the user
        try:
            await ctx.author.send("Canvas ego tracking enabled")
        except discord.Forbidden:
            await ctx.response.send_message("You have DMs disabled, so I can't send ego tracking notifications")
            return
        await ctx.response.send_message("Canvas ego tracking enabled")
    
    @commands.slash_command(name="egotrack-disable", description="Disable ego tracking")
    async def egotrack_disable(self, ctx: discord.ApplicationCommandInteraction):
        # Check if the username is in the database
        c = db.cursor()
        username = c.execute('SELECT pxls_username FROM usernames WHERE discord_id = ?', (str(ctx.author.id),)).fetchone()
        if username is None:
            await ctx.response.send_message("You need to link your username first (/user link)")
            return
        username = username[0]
        # Remove the username from the egos table
        c.execute('DELETE FROM egos WHERE pxls_username = ?', (username,))
        db.commit()
        c.close()
        # Respond to the user
        await ctx.response.send_message("Ego tracking disabled")

    @commands.slash_command(name="egotrack_canvas-disable", description="Disable canvas ego tracking")
    async def egotrack_canvas_disable(self, ctx: discord.ApplicationCommandInteraction):
        # Check if the username is in the database
        c = db.cursor()
        username = c.execute('SELECT pxls_username FROM usernames WHERE discord_id = ?', (str(ctx.author.id),)).fetchone()
        if username is None:
            await ctx.response.send_message("You need to link your username first (/user link)")
            return
        username = username[0]
        # Remove the username from the egos table
        c.execute('DELETE FROM canvasegos WHERE pxls_username = ?', (username,))
        db.commit()
        c.close()
        # Respond to the user
        await ctx.response.send_message("Canvas ego tracking disabled")
    
    @commands.slash_command()
    async def user(self, ctx: discord.ApplicationCommandInteraction):
        pass

    @user.sub_command(name="link", description="Link your Discord account to your Pxls username")
    async def link(self, ctx: discord.ApplicationCommandInteraction, username: str):
        # Check if the username is already in the database
        c = db.cursor()
        if c.execute('SELECT * FROM usernames WHERE pxls_username = ?', (username,)).fetchone() is not None:
            await ctx.response.send_message("Username already linked (use /user unlink to unlink)")
            return
        # Add the username to the database
        c.execute('INSERT INTO usernames VALUES (?, ?)', (str(ctx.author.id), username))
        db.commit()
        c.close()
        # Respond to the user
        await ctx.response.send_message("Username linked successfully")
    
    @user.sub_command(name="unlink", description="Unlink your Discord account from your Pxls username")
    async def unlink(self, ctx: discord.ApplicationCommandInteraction):
        # Remove the username from the database
        c = db.cursor()
        c.execute('DELETE FROM usernames WHERE discord_id = ?', (str(ctx.author.id),))
        db.commit()
        c.close()
        # Respond to the user
        await ctx.response.send_message("Username unlinked successfully")
    
    @user.sub_command(name="get", description="Get your linked username")
    async def get(self, ctx: discord.ApplicationCommandInteraction):
        # Get the username from the database
        c = db.cursor()
        username = c.execute('SELECT pxls_username FROM usernames WHERE discord_id = ?', (str(ctx.author.id),)).fetchone()
        c.close()
        if username is None:
            await ctx.response.send_message("You haven't linked a username yet")
            return
        # Respond to the user
        await ctx.response.send_message(f"Your linked username is {username[0]}")
    

def setup(bot: commands.Bot):
    bot.add_cog(Ego(bot))

def teardown(bot: commands.Bot):
    db.close()
    bot.remove_cog('Ego')
