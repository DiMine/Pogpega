import discord
from discord.ext import commands
import sqlite3
# from PIL import Image
import os

db = sqlite3.connect('cogs/databases/db.db')
cur = db.cursor()
cur.execute('CREATE TABLE IF NOT EXISTS roles (server_id, role_id)')
cur.execute('CREATE TABLE IF NOT EXISTS grief (server_id, channel_id, x, y)')
cur.close()

class Grief(commands.Cog):
    def __init__(self, bot: discord.Bot):
        self.bot = bot
        # self.templates = {}
    
    # def on_ready(self):
    #     c = db.cursor()
    #     for row in c.execute('SELECT * FROM grief'):
    #         try:
    #             channel = self.bot.get_channel(row[1])
    #             if channel is None:
    #                 print(f'Channel not found for {row[1]}')
    #                 continue
    #             self.templates[row[0]] = (Image.open(f'cogs/templates/{row[0]}.png'), channel, row[2], row[3]) # the problem
    #         except FileNotFoundError:
    #             print(f'File not found for {row[0]}')
    #     c.close()
    
    # @discord.slash_command(name='setrole', description='(Server Admin Only) Set the role of people that can edit the template announcement')
    # async def setrole(self, ctx: discord.ApplicationContext, role: discord.Role):
    #     # Check if the user has permission to use this command
    #     if ctx.author.guild_permissions.administrator:
    #         c = db.cursor()
    #         c.execute('DELETE FROM roles WHERE server_id = ?', (ctx.guild.id,))
    #         c.execute('INSERT INTO roles VALUES (?, ?)', (ctx.guild.id, role.id))
    #         db.commit()
    #         c.close()
    #         await ctx.respond('Role set')
    #     else:
    #         await ctx.respond('<a:nuhuh:1262041901440303157> You do not have permission to use this command', ephemeral=True)

    # @discord.slash_command(name='unsetrole', description='(Server Admin Only) Unset the role of people that can edit the template announcement')
    # async def unsetrole(self, ctx: discord.ApplicationContext):
    #     # Check if the user has permission to use this command
    #     if ctx.author.guild_permissions.administrator:
    #         c = db.cursor()
    #         c.execute('DELETE FROM roles WHERE server_id = ?', (ctx.guild.id,))
    #         db.commit()
    #         c.close()
    #         await ctx.respond('Role unset')
    #     else:
    #         await ctx.respond('<a:nuhuh:1262041901440303157> You do not have permission to use this command', ephemeral=True)

    grief = discord.SlashCommandGroup(name='grief', description='Commands for managing the grief alert channel')

    @grief.command(name='setchannel', description='Set the grief alert channel')
    async def setchannel(self, ctx: discord.ApplicationContext, channel: discord.TextChannel):
        # Check if the user has permission to use this command
        c = db.cursor()
        role = c.execute('SELECT role_id FROM roles WHERE server_id = ?', (ctx.guild.id,)).fetchone()
        c.close()
        if role is not None:
            role = discord.utils.get(ctx.guild.roles, id=role[0])
            if role not in ctx.author.roles:
                await ctx.respond('You do not have permission to use this command', ephemeral=True)
                return
        else:
            await ctx.respond('Role not set', ephemeral=True)
            return
        # Set the channel
        c = db.cursor()
        c.execute('DELETE FROM grief WHERE server_id = ?', (ctx.guild.id,))
        c.execute('INSERT INTO grief VALUES (?, ?, ?, ?)', (ctx.guild.id, channel.id, -1, -1))
        db.commit()
        c.close()
        await ctx.respond('Channel set')
    
    @grief.command(name='unsetchannel', description='Unset the grief alert channel')
    async def unsetchannel(self, ctx: discord.ApplicationContext):
        # Check if the user has permission to use this command
        c = db.cursor()
        role = c.execute('SELECT role_id FROM roles WHERE server_id = ?', (ctx.guild.id,)).fetchone()
        c.close()
        if role is not None:
            role = discord.utils.get(ctx.guild.roles, id=role[0])
            if role not in ctx.author.roles:
                await ctx.respond('You do not have permission to use this command', ephemeral=True)
                return
        else:
            await ctx.respond('Role not set', ephemeral=True)
            return
        # Unset the channel
        c = db.cursor()
        c.execute('DELETE FROM grief WHERE server_id = ?', (ctx.guild.id,))
        db.commit()
        c.close()
        try:
            os.remove(f'cogs/templates/{ctx.guild.id}.png')
        except FileNotFoundError:
            pass
        await ctx.respond('Channel unset')

    @grief.command(name='settemplate', description='Add/update a template to the grief alert')
    @discord.option(name='x', type=int, description='The x coordinate of the template', required=True)
    @discord.option(name='y', type=int, description='The y coordinate of the template', required=True)
    @discord.option(name='image', type=discord.Attachment, description='The image of the template', required=True)
    async def settemplate(self, ctx: discord.ApplicationContext, x: int, y: int, image: discord.Attachment):
        # Check if the attachment is a png image
        if image.content_type != 'image/png':
            await ctx.respond('The attachment must be a png image', ephemeral=True)
        # Check if the user has permission to use this command
        c = db.cursor()
        role = c.execute('SELECT role_id FROM roles WHERE server_id = ?', (ctx.guild.id,)).fetchone()
        c.close()
        if role is not None:
            role = discord.utils.get(ctx.guild.roles, id=role[0])
            if role not in ctx.author.roles:
                await ctx.respond('You do not have permission to use this command', ephemeral=True)
                return
        else:
            await ctx.respond('Role not set', ephemeral=True)
            return
        # Get the channel id from the database
        c = db.cursor()
        channel_id = c.execute('SELECT channel_id FROM grief WHERE server_id = ?', (ctx.guild.id,)).fetchone()
        c.close()
        if channel_id is None:
            await ctx.respond('Channel not set', ephemeral=True)
            return
        channel_id = channel_id[0]
        # Save the image
        await image.save(f'cogs/templates/{ctx.guild.id}.png')
        # img = Image.open(f'cogs/templates/{ctx.guild.id}.png')
        # Update the template
        # self.templates[ctx.guild.id] = (img, channel_id, x, y)
        c = db.cursor()
        c.execute('DELETE FROM grief WHERE server_id = ?', (ctx.guild.id,))
        c.execute('INSERT INTO grief VALUES (?, ?, ?, ?)', (ctx.guild.id, channel_id, x, y))
        db.commit()
        c.close()
        await ctx.respond('Template set')

    @grief.command(name='deletetemplate', description='Delete a template from the grief alert')
    async def deletetemplate(self, ctx: discord.ApplicationContext):
        # Check if the user has permission to use this command
        c = db.cursor()
        role = c.execute('SELECT role_id FROM roles WHERE server_id = ?', (ctx.guild.id,)).fetchone()
        c.close()
        if role is not None:
            role = discord.utils.get(ctx.guild.roles, id=role[0])
            if role not in ctx.author.roles:
                await ctx.respond('You do not have permission to use this command', ephemeral=True)
                return
        else:
            await ctx.respond('Role not set', ephemeral=True)
            return
        # Delete the template
        try:
            os.remove(f'cogs/templates/{ctx.guild.id}.png')
        except FileNotFoundError:
            await ctx.respond('Template not found', ephemeral=True)
            return
        await ctx.respond('Template deleted')

    

# class Template():
#     def __init__(self,image, x, y):
#         self.image = image
#         self.x = x
#         self.y = y
        

    
def setup(bot: discord.Bot):
    bot.add_cog(Grief(bot))
