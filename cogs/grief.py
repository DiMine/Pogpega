import disnake as discord
from disnake.ext import commands
import sqlite3
from PIL import Image, ImageColor
import os
import websockets
import asyncio
import json
from clueless import hex_to_rgb, palettize_array
import aiohttp
import numpy as np
from io import BytesIO

# TODO make the templates reset when the canvas resets
# TODO have a "normal" mode and "high alert" mode for end of canvas griefs
# TODO Download the board at the start, have a command to refresh it, and use the websocket to update it
# TODO Have a timeout for griefs so that misplaces that get undone don't trigger them

pxls_auth = os.environ['PXLS_AUTH']

info = json.loads(open('info/info.json').read())

EMBED_COLOR = discord.Color.from_rgb(0, 215, 255)

palette = [f"#{color['value']}" for color in info["palette"]]
PALETTE = [hex_to_rgb(i) for i in palette]

db = sqlite3.connect('cogs/databases/db.db')
cur = db.cursor()
cur.execute('CREATE TABLE IF NOT EXISTS roles (server_id, role_id)')
db.commit()
cur.close()
db_grief = sqlite3.connect('cogs/databases/grief.db')
cur = db_grief.cursor()
cur.execute('CREATE TABLE IF NOT EXISTS grief (server_id, channel_id, x, y, enabled, alert)')
db_grief.commit()
cur.close()


class Grief(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.load_images()

        colors_list = []
        for color in palette:
            rgb = ImageColor.getcolor(color, "RGBA")
            colors_list.append(rgb)
        colors_dict = dict(enumerate(colors_list))
        colors_dict[255] = (0, 0, 0, 0)
        self.colors = colors_dict


    async def websock(self):
        print('Connecting to pxls.space websocket')
        async with websockets.connect('wss://pxls.space/ws', extra_headers={"x-pxls-cfauth": pxls_auth}) as socket:
            async for message in socket:
                message = json.loads(message)
                if message['type'] == 'pixel':
                    for pixel in message['pixels']:
                        color = self.colors[pixel['color']]
                        alerts = await self.check_griefs(pixel['x'], pixel['y'], color)
                        for alert in alerts:
                            template = self.templates[alert]
                            channel = await self.bot.fetch_channel(template[1])
                            print(f'Grief detected at {pixel["x"]}, {pixel["y"]}')
                            embed = discord.Embed()
                            embed.title = 'Grief Detected <a:neuroDinkDonk:1266816771168403456>'
                            embed.description = f'Grief detected at {pixel["x"]}, {pixel["y"]}'
                            embed.add_field(name='Pxls Link', value=f'https://pxls.space/#x={pixel['x']}&y={pixel['y']}&scale=50')
                            embed.set_thumbnail(url='https://media.discordapp.net/stickers/1150735306857910293.png')
                            img = await self.fetch_board()
                            img = template[0].crop((pixel['x'] - template[2] - 20, pixel['y'] - template[3] - 10, pixel['x'] - template[2] + 20, pixel['y'] - template[3] + 10))
                            img = img.resize((img.width * 7, img.height * 7), Image.Resampling.BOX)
                            b = BytesIO()
                            img.save(b, 'PNG')
                            b.seek(0)
                            embed.set_image(file=discord.File(b, 'grief.png'))
                            embed.color = EMBED_COLOR
                            await channel.send(embed=embed)

    def cog_unload(self) -> None:
        print('Closing websocket')
        self.task.cancel()

    async def fetch_board(self) -> Image:
        headers = {
            "x-pxls-cfauth": pxls_auth
        }
        async with aiohttp.ClientSession() as session:
            async with session.get("https://pxls.space/boarddata", headers=headers) as response:
                data = await response.content.read()
                arr = np.asarray(list(data), dtype=np.uint8).reshape(
                info["height"], info["width"]
                )
                arr = palettize_array(arr, palette)
                return Image.fromarray(arr, mode='RGBA')
                
            
    async def cog_load(self) -> None:
        self.task = asyncio.create_task(self.websock())
        

    def load_images(self): # TODO Palettize the images into index arrays
        self.templates = {}
        c = db_grief.cursor()
        c.execute('SELECT * FROM grief WHERE enabled = ?', (True,))
        for row in c.fetchall():
            img = Image.open(f'cogs/templates/{row[0]}.png')
            # img = reduce(img, PALETTE)
            # image = palettize_array(img, palette)
            # image = Image.fromarray(image)
            # image.save(f'cogs/templates/{row[0]}_but_worse.png')
            self.templates[row[0]] = (img, row[1], row[2], row[3])
        c.close()


    @commands.slash_command()
    async def grief(self, ctx: discord.ApplicationCommandInteraction):
        pass


    @grief.sub_command(name='setchannel', description='Set the grief alert channel')
    async def setchannel(self, ctx: discord.ApplicationCommandInteraction, channel: discord.TextChannel):
        # Check if the user has permission to use this command
        c = db.cursor()
        role = c.execute('SELECT role_id FROM roles WHERE server_id = ?', (ctx.guild.id,)).fetchone()
        c.close()
        if not await self.check_role(ctx):
            return
        # Set the channel
        c = db_grief.cursor()
        c.execute('DELETE FROM grief WHERE server_id = ?', (ctx.guild.id,))
        c.execute('INSERT INTO grief VALUES (?, ?, ?, ?, ?, ?)', (ctx.guild.id, channel.id, -1, -1, False, False))
        db_grief.commit()
        c.close()
        await ctx.response.send_message('Channel set')
    

    @grief.sub_command(name='unsetchannel', description='Unset the grief alert channel')
    async def unsetchannel(self, ctx: discord.ApplicationCommandInteraction):
        if not await self.check_role(ctx):
            return
        # Unset the channel
        c = db_grief.cursor()
        c.execute('DELETE FROM grief WHERE server_id = ?', (ctx.guild.id,))
        db_grief.commit()
        c.close()
        try:
            os.remove(f'cogs/templates/{ctx.guild.id}.png')
        except FileNotFoundError:
            pass
        await ctx.response.send_message('Channel unset')


    @grief.sub_command(name='settemplate', description='Add/update a template to the grief alert')
    async def settemplate(self, 
            ctx: discord.ApplicationCommandInteraction, 
            x: int = commands.Param(name='x', description='The x coordinate of the template'),
            y: int = commands.Param(name='y', description='The y coordinate of the template'),
            image: discord.Attachment = commands.Param(name='image', description='The image of the template')):
        # Check if the attachment is a png image
        if image.content_type != 'image/png':
            await ctx.response.send_message('The attachment must be a png image', ephemeral=True)
            return
        if not await self.check_role(ctx):
            return
        # Get the channel id from the database
        c = db_grief.cursor()
        channel_id = c.execute('SELECT channel_id FROM grief WHERE server_id = ?', (ctx.guild.id,)).fetchone()
        c.close()
        if channel_id is None:
            await ctx.response.send_message('Channel not set', ephemeral=True)
            return
        channel_id = channel_id[0]
        # Save the image
        await image.save(f'cogs/templates/{ctx.guild.id}.png')
        image = Image.open(f'cogs/templates/{ctx.guild.id}.png')
        # image = reduce(image, PALETTE)
        # img = Image.open(f'cogs/templates/{ctx.guild.id}.png')
        # Update the template
        self.templates[ctx.guild.id] = (image, channel_id, x, y)
        c = db_grief.cursor()
        c.execute('DELETE FROM grief WHERE server_id = ?', (ctx.guild.id,))
        c.execute('INSERT INTO grief VALUES (?, ?, ?, ?, ?, ?)', (ctx.guild.id, channel_id, x, y, True, False))
        db_grief.commit()
        c.close()
        await ctx.response.send_message('Template set')


    @grief.sub_command(name='deletetemplate', description='Delete a template from the grief alert')
    async def deletetemplate(self, ctx: discord.ApplicationCommandInteraction):
        if not await self.check_role(ctx):
            return
        self.templates.pop(ctx.guild.id, None)
        # Delete the template
        try:
            os.remove(f'cogs/templates/{ctx.guild.id}.png')
        except FileNotFoundError:
            await ctx.response.send_message('Template not found', ephemeral=True)
            return
        await ctx.response.send_message('Template deleted')
    

    @grief.sub_command(name='enable', description='Enable the grief alert')
    async def enable(self, ctx: discord.ApplicationCommandInteraction):
        if not await self.check_role(ctx):
            return
        # Enable the grief alert
        c = db_grief.cursor()
        c.execute('UPDATE grief SET enabled = ? WHERE server_id = ?', (True, ctx.guild.id))
        db_grief.commit()
        template = c.execute('SELECT * FROM grief WHERE server_id = ?', (ctx.guild.id,))
        c.close()
        image = Image.open(f'cogs/templates/{ctx.guild.id}.png')
        self.templates[ctx.guild.id] = (image, template[0][1], template[0][2], template[0][3])
        await ctx.response.send_message('Grief alert enabled')


    @grief.sub_command(name='disable', description='Disable the grief alert')
    async def disable(self, ctx: discord.ApplicationCommandInteraction):
        if not await self.check_role(ctx):
            return
        # Disable the grief alert
        c = db_grief.cursor()
        c.execute('UPDATE grief SET enabled = ? WHERE server_id = ?', (False, ctx.guild.id))
        db_grief.commit()
        c.close()
        self.templates.pop(ctx.guild.id, None)
        await ctx.response.send_message('Grief alert disabled')


    @grief.sub_command(name='highalert', description='Enable or disable high alert mode (sends a message on every pixel)')
    async def highalert(self, 
            ctx: discord.ApplicationCommandInteraction, 
            alert: bool = commands.Param(name='alert', description='Whether or not the template is on high alert')):
        if not await self.check_role(ctx):
            return
        # Set the alert level
        c = db_grief.cursor()
        c.execute('UPDATE grief SET alert = ? WHERE server_id = ?', (alert, ctx.guild.id))
        db_grief.commit()
        c.close()
        await ctx.response.send_message('Alert level set (currently low alert disables grief alerts)')


    async def check_griefs(self, x: int, y: int, color: tuple):
        alerts = []
        for key, value in self.templates.items():
            if self.check_grief(value, x, y, color):
                alerts.append(key)
        return alerts
    

    def check_grief(self, template: tuple, x: int, y: int, color: tuple):
        img = template[0]
        x = x - template[2] + 1
        y = y - template[3] + 1
        if x < 0 or y < 0:
            return False
        try:
            pixel = img.getpixel((x, y))
            if pixel[3] != 0 and pixel != color:
                return True
            return False
        except IndexError:
            return False
        

    async def check_role(self, ctx: discord.ApplicationCommandInteraction):
        # Check if the user has permission to use this command
        c = db.cursor()
        role = c.execute('SELECT role_id FROM roles WHERE server_id = ?', (ctx.guild.id,)).fetchone()
        c.close()
        if role is not None:
            role = discord.utils.get(ctx.guild.roles, id=role[0])
            if role not in ctx.author.roles:
                await ctx.response.send_message('You do not have permission to use this command', ephemeral=True)
                return False
        else:
            await ctx.response.send_message('Role not set', ephemeral=True)
            return False
        return True
        
    
def setup(bot: commands.Bot):
    bot.add_cog(Grief(bot))


def teardown(bot: commands.Bot):
    bot.remove_cog('Grief')