import disnake as discord
from disnake.ext import commands, tasks
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
import time

# TODO make the templates reset when the canvas resets (or just a command to reset them)
# TODO Make a template progress cog, use that for the templates here
# TODO Put a try except when sending messages
# TODO Let sticker be replaced

pxls_auth = os.environ['PXLS_AUTH']
BOT_ADMINS = [int(admin) for admin in os.environ['BOT_ADMINS'].split(',')]

EMBED_COLOR = discord.Color.from_rgb(0, 215, 255)

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
        self.refresh_palette()
        self.alerts = {}
        self.send_alerts.start()

    async def websock(self):
        print('Connecting to pxls.space websocket')
        async with websockets.connect('wss://pxls.space/ws', extra_headers={"x-pxls-cfauth": pxls_auth}) as socket:
            async for message in socket:
                message = json.loads(message)
                if message['type'] == 'pixel':
                    for pixel in message['pixels']:
                        # Add the pixel to the board
                        color = self.colors[pixel['color']]
                        self.board.putpixel((pixel['x'], pixel['y']), color)
                        # Check for griefs
                        await self.check_griefs(pixel, color)
                            

    def cog_unload(self) -> None:
        print('Closing websocket')
        self.task.cancel()

    def refresh_palette(self):
        self.info = json.loads(open('info/info.json').read())
        self.palette = [f"#{color['value']}" for color in self.info["palette"]]
        self.PALETTE = [hex_to_rgb(i) for i in self.palette]

        colors_list = []
        for color in self.palette:
            rgb = ImageColor.getcolor(color, "RGBA")
            colors_list.append(rgb)
        colors_dict = dict(enumerate(colors_list))
        colors_dict[255] = (0, 0, 0, 0)
        self.colors = colors_dict
        self.colors_to_index = {v: k for k, v in colors_dict.items()}

    async def send_grief_alert(self, pixel: dict, alert: int):
        print('Sending grief alert')
        x = pixel['x']
        y = pixel['y']
        color = self.colors[pixel['color']]
        print(f'\nGrief detected at {x}, {y}')
        template = self.templates[alert]
        channel = await self.bot.fetch_channel(template[1])
        print('got the channel')
        # Crop the board
        img = self.board.copy()
        print('copied the board')
        img = crop_grief_image(img, x, y)
        print('cropped the board')
        img = img.resize((img.width * 10, img.height * 10), Image.Resampling.BOX)
        print('resized the board')
        b = BytesIO()
        img.save(b, 'PNG')
        b.seek(0)
        print('cropped the grief image')
        # Get the palette indexes for the colors
        expected = template[0].getpixel((x - template[2], y - template[3]))
        col_expected = self.rgb_to_palette(expected)
        try:
            num_expected = self.colors_to_index[expected]
        except KeyError:
            num_expected = 255
        col_actual = self.rgb_to_palette(color)
        print('got the palette indexes')
        # Make the embed
        embed = discord.Embed()
        embed.title = f'Grief Detected at [({x}, {y})](https://pxls.space/#x={x}&y={y}&scale=50) <a:neuroDinkDonk:1266816771168403456>'
        embed.description = f'Pixel should be {col_expected} ({num_expected}) but is {col_actual} ({pixel['color']})'
        embed.set_thumbnail(url='https://media.discordapp.net/stickers/1150735306857910293.png')
        embed.color = EMBED_COLOR
        embed.set_image(file=discord.File(b, 'grief.png'))
        print('made the embed')
        # Send the embed
        try:
            await channel.send(embed=embed)
        except discord.Forbidden:
            print('Failed to send grief alert: no perms')
        except Exception:
            print('Failed to send grief alert: unknown error')
            print(Exception)

    async def send_grief_alerts(self, pixels: list[dict], server: int):
        alerts = []
        template = self.templates[server]
        channel = await self.bot.fetch_channel(template[1])
        for pixel in pixels:
            x = pixel['x']
            y = pixel['y']
            color = self.colors[pixel['color']]
            expected = template[0].getpixel((x - template[2], y - template[3]))
            col_expected = self.rgb_to_palette(expected)
            try:
                num_expected = self.colors_to_index[expected]
            except KeyError:
                num_expected = 255
            col_actual = self.rgb_to_palette(color)
            alerts.append((x, y, col_expected, num_expected, col_actual, pixel['color']))
        embed = discord.Embed()
        embed.title = f'Griefs Detected at {len(pixels)} locations'
        embed.color = EMBED_COLOR
        for alert in alerts:
            embed.add_field(name=f'[{alert[0]}, {alert[1]}](https://pxls.space/#x={alert[0]}&y={alert[1]}&scale=50)', value=f'Pixel should be {alert[2]} ({alert[3]}) but is {alert[4]} ({alert[5]})', inline=False)
        try:
            await channel.send(embed=embed)
        except discord.Forbidden:
            print('Failed to send grief alert: no perms')

    @tasks.loop(seconds=300)
    async def send_alerts(self):
        for server, pixels in self.alerts.items():
            print('before: ', pixels)
            # Check if the grief is still there
            for pixel in pixels:
                x = pixel['x']
                y = pixel['y']
                color_expected = self.templates[server][0].getpixel((x - self.templates[server][2], y - self.templates[server][3]))
                if self.board.getpixel((x, y)) == color_expected:
                    pixels.remove(pixel)
            print('after: ', pixels)
            # Send the alerts
            if len(pixels) > 0:
                await self.send_grief_alerts(pixels, server)
            

    @send_alerts.before_loop
    async def before_send_alerts(self):
        await self.bot.wait_until_ready()
        # Calculate the time until the next 5 minute mark
        current = time.time()
        wanted = current - (current % 300) + 300
        print('Waiting for ', wanted - current, 's to send alerts')
        await asyncio.sleep(wanted - current)


    async def fetch_board(self) -> Image:
        headers = {
            "x-pxls-cfauth": pxls_auth
        }
        async with aiohttp.ClientSession() as session:
            async with session.get("https://pxls.space/boarddata", headers=headers) as response:
                data = await response.content.read()
                arr = np.asarray(list(data), dtype=np.uint8).reshape(
                self.info["height"], self.info["width"]
                )
                arr = palettize_array(arr, self.palette)
                return Image.fromarray(arr, mode='RGBA')
                
    async def cog_load(self) -> None:
        self.board = await self.fetch_board()
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
            self.templates[row[0]] = (img, row[1], row[2], row[3], row[5])
        c.close()

    @commands.slash_command(name='refresh_board', description='(Bot Admin Only) Refresh the board')
    async def refresh_board(self, ctx: discord.ApplicationCommandInteraction):
        # Check if the user has permission to use this command
        if ctx.author.id not in BOT_ADMINS:
            await ctx.response.send_message('<a:nuhuh:1262041901440303157> You do not have permission to use this command', ephemeral=True)
            return
        self.board = await self.fetch_board()
        await ctx.response.send_message('Board refreshed')

    @commands.slash_command(name='get_board', description='Get the current board')
    async def get_board(self, ctx: discord.ApplicationCommandInteraction):
        img = self.board.copy()
        b = BytesIO()
        img.save(b, 'PNG')
        b.seek(0)
        await ctx.response.send_message(file=discord.File(b, 'board.png'))

    @commands.slash_command()
    async def grief(self, ctx: discord.ApplicationCommandInteraction):
        pass

    @grief.sub_command(name='setchannel', description='Set the grief alert channel')
    async def setchannel(self, ctx: discord.ApplicationCommandInteraction, channel: discord.TextChannel):
        # Check if the user has permission to use this command
        if not await self.check_role(ctx):
            return
        # Set the channel
        c = db_grief.cursor()
        c.execute('DELETE FROM grief WHERE server_id = ?', (ctx.guild.id,))
        c.execute('INSERT INTO grief VALUES (?, ?, ?, ?, ?, ?)', (ctx.guild.id, channel.id, -1, -1, False, 'normal'))
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
        self.templates[ctx.guild.id] = (image, channel_id, x, y, 'normal')
        c = db_grief.cursor()
        c.execute('DELETE FROM grief WHERE server_id = ?', (ctx.guild.id,))
        c.execute('INSERT INTO grief VALUES (?, ?, ?, ?, ?, ?)', (ctx.guild.id, channel_id, x, y, True, 'normal'))
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
        self.templates[ctx.guild.id] = (image, template[0][1], template[0][2], template[0][3], template[0][5])
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

    @grief.sub_command(name='alert', description='Set the alert level')
    async def alert(self, 
            ctx: discord.ApplicationCommandInteraction, 
            alert: str = commands.Param(name='alert', description='The alert level', choices=['normal', 'high', 'realtime'])):
        if not await self.check_role(ctx):
            return
        # Set the alert level
        template = self.templates[ctx.guild.id]
        self.templates[ctx.guild.id] = (template[0], template[1], template[2], template[3], alert)
        c = db_grief.cursor()
        c.execute('UPDATE grief SET alert = ? WHERE server_id = ?', (alert, ctx.guild.id))
        db_grief.commit()
        c.close()
        await ctx.response.send_message('Alert level set to ' + alert)

    @grief.sub_command(name='alertlevels', description='Get the alert levels')
    async def alertlevels(self, ctx: discord.ApplicationCommandInteraction):
        embed = discord.Embed()
        embed.title = 'Alert Levels'
        embed.add_field(name='Normal', value='Grief alerts are sent in batches at 5 minute intervals', inline=False)
        embed.add_field(name='High', value='Grief alerts are sent for each pixel after a few seconds', inline=False)
        embed.add_field(name='Realtime', value='Grief alerts are sent as soon as a pixel is detected, including pixels that are undone', inline=False)
        embed.color = EMBED_COLOR
        await ctx.response.send_message(embed=embed)

    async def check_griefs(self, pixel: dict, color: tuple):
        x = pixel['x']
        y = pixel['y']
        for server, template in self.templates.items():
            if self.check_grief(template, x, y, color):
                if template[4] == 'realtime':
                    await self.send_grief_alert(pixel, server)
                elif template[4] == 'high':
                    task = asyncio.create_task(self.check_undo(template, x, y, server))
                elif template[4] == 'normal':
                    self.add_to_dict(server, pixel)


    def check_grief(self, template: tuple, x: int, y: int, color: tuple) -> bool:
        img = template[0]
        x = x - template[2]
        y = y - template[3]
        if x < 0 or y < 0:
            return False
        try:
            pixel = img.getpixel((x, y))
            if pixel[3] != 0 and pixel != color:
                return True
            return False
        except IndexError:
            return False
        
    async def check_undo(self, template: tuple, x: int, y: int, server: int):
        await asyncio.sleep(5)
        new_color = self.board.getpixel((x, y))
        if self.check_grief(template, x, y, new_color):
            try:
                color = self.colors_to_index[new_color]
            except KeyError:
                print('Error in check_undo')
                return
            await self.send_grief_alert({'x': x, 'y': y, 'color': color}, server)
        else:
            print('Undo detected')
    
    def rgb_to_hex(self, rgb: tuple) -> str:
        return f'{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}'

    def rgb_to_palette(self, rgb: tuple) -> str:
        palette = self.info['palette']
        hex = self.rgb_to_hex(rgb)
        for color in palette:
            if color['value'] == hex:
                return color['name']
        return 'Unknown'
    
    def add_to_dict(self, server: int, pixel: dict):
        if server not in self.alerts:
            self.alerts[server] = []
        self.alerts[server].append(pixel)

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
    

def crop_grief_image(image: Image, x: int, y: int) -> Image:
    WIDTH = 15
    HEIGHT = 6
    try:
        img = image.crop((x - WIDTH, y - HEIGHT, x + WIDTH, y + HEIGHT))
    except ValueError:
        try:
            img = image.crop((0, y - HEIGHT, x + WIDTH, y + HEIGHT))
        except ValueError:
            try:
                img = image.crop((x - WIDTH, 0, x + WIDTH, y + HEIGHT))
            except ValueError:
                try:
                    img = image.crop((0, 0, x + WIDTH, y + HEIGHT))
                except ValueError:
                    try:
                        img = image.crop((x - WIDTH, y - HEIGHT, 2 * image.width - x - WIDTH, y + HEIGHT))
                    except ValueError:
                        try:
                            img = image.crop((x - WIDTH, y - HEIGHT, x + WIDTH, 2 * image.height - y - HEIGHT))
                        except ValueError:
                            try:
                                img = image.crop((x - WIDTH, y - HEIGHT, 2 * image.width - x - WIDTH, 2 * image.height - y - HEIGHT))
                            except ValueError:
                                img = Image.new('RGB', (1, 1), (85, 171, 237))
    img = img.resize((img.width * 10, img.height * 10), Image.Resampling.BOX)
    return img

    
def setup(bot: commands.Bot):
    bot.add_cog(Grief(bot))

def teardown(bot: commands.Bot):
    db.close()
    db_grief.close()
    bot.remove_cog('Grief')