import disnake as discord
from disnake.ext import commands
import sqlite3
import re
import time

db = sqlite3.connect('cogs/databases/db.db')
cur = db.cursor()
cur.execute('CREATE TABLE IF NOT EXISTS roles (server_id, role_id)')
db.commit()
cur.close()
db_announce = sqlite3.connect('cogs/databases/announce.db')
cur = db_announce.cursor()
cur.execute('CREATE TABLE IF NOT EXISTS announce (server_id, channel_id, message_id)')
db_announce.commit()
cur.close()

class Announce(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def check_role(self, ctx: discord.ApplicationCommandInteraction):
        # Check if the user has permission to use this command
        c = db.cursor()
        role = c.execute('SELECT role_id FROM roles WHERE server_id = ?', (ctx.guild.id,)).fetchone()
        c.close()
        if role is not None:
            role = discord.utils.get(ctx.guild.roles, id=role[0])
            if role not in ctx.author.roles:
                await ctx.response.send_message('<a:nuhuh:1262041901440303157> You do not have permission to use this command', ephemeral=True)
                return False
        else:
            await ctx.response.send_message('Role not set', ephemeral=True)
            return False
        return True
    
    @commands.slash_command(name='setrole', description='(Server Admin Only) Set the role of people that can edit the template announcement')
    async def setrole(self, ctx: discord.ApplicationCommandInteraction, role: discord.Role):
        # Check if the user has permission to use this command
        if ctx.author.guild_permissions.manage_guild:
            c = db.cursor()
            c.execute('DELETE FROM roles WHERE server_id = ?', (ctx.guild.id,))
            c.execute('INSERT INTO roles VALUES (?, ?)', (ctx.guild.id, role.id))
            # c.execute('INSERT INTO roles VALUES (?, ?) ON CONFLICT(server_id) DO UPDATE SET role_id = ?', (ctx.guild.id, role.id, role.id))
            db.commit()
            c.close()
            await ctx.response.send_message('Role set')
        else:
            await ctx.response.send_message('<a:nuhuh:1262041901440303157> You do not have permission to use this command', ephemeral=True)

    @commands.slash_command(name='unsetrole', description='(Server Admin Only) Unset the role of people that can edit the template announcement')
    async def unsetrole(self, ctx: discord.ApplicationCommandInteraction):
        # Check if the user has permission to use this command
        if ctx.author.guild_permissions.manage_guild:
            c = db.cursor()
            c.execute('DELETE FROM roles WHERE server_id = ?', (ctx.guild.id,))
            db.commit()
            c.close()
            await ctx.response.send_message('Role unset')
        else:
            await ctx.response.send_message('<a:nuhuh:1262041901440303157> You do not have permission to use this command', ephemeral=True)
    
    @commands.slash_command()
    async def announce(self, ctx: discord.ApplicationCommandInteraction):
        pass

    @announce.sub_command(name='create', description='Create an announcement')
    async def create(self, ctx: discord.ApplicationCommandInteraction):
        # Check if the user has permission to use this command
        if not await self.check_role(ctx):
            return
        # Send the modal
        modal = AnnouncementModal(title='Create an announcement', type='create')
        await ctx.response.send_modal(modal)

    async def get_announcements(ctx: discord.ApplicationCommandInteraction, user_input: str) -> list[str]:
        c = db_announce.cursor()
        announcements = c.execute('SELECT message_id FROM announce WHERE server_id = ?', (ctx.guild_id,)).fetchall()
        c.close()
        announcements = [str(announcement[0]) for announcement in announcements]
        return announcements
    
    @announce.sub_command(name='edit', description='Edit an announcement')
    async def edit(self, 
            ctx: discord.ApplicationCommandInteraction, 
            announcement: str = commands.Param(name='announcement', description='The announcement ID to edit', autocomplete=get_announcements)):
        # Check if the user has permission to use this command
        if not await self.check_role(ctx):
            return
        # Check if the announcement exists in the database
        c = db_announce.cursor()
        announcements = c.execute('SELECT message_id FROM announce WHERE server_id = ?', (ctx.guild.id,)).fetchall()
        c.close()
        if announcement not in [str(announcement[0]) for announcement in announcements]:
            await ctx.response.send_message('Announcement not found in database', ephemeral=True)
            return
        # Select the channel from the database
        c = db_announce.cursor()
        the_announcement = c.execute('SELECT * FROM announce WHERE server_id = ? AND message_id = ?', (ctx.guild.id, int(announcement))).fetchall()
        c.close()
        try:
            channel = await commands.Bot.fetch_channel(self.bot, the_announcement[0][1])
            message = await channel.fetch_message(the_announcement[0][2])
        except discord.NotFound:
            await ctx.response.send_message('Message not found', ephemeral=True)
            return
        # Send the modal
        modal = AnnouncementModal(title='Edit an announcement', type='edit', announcement=announcement, channel=the_announcement[0][1])
        await ctx.response.send_modal(modal)
    
    @announce.sub_command(name='update_time', description='Update the timestamps of an announcement, if there are any')
    async def update_time(self,
            ctx: discord.ApplicationCommandInteraction,
            announcement: str = commands.Param(name='announcement', description='The announcement ID to update', autocomplete=get_announcements)):
        # Check if the user has permission to use this command
        if not await self.check_role(ctx):
            return
        # Check if the announcement exists in the database
        c = db_announce.cursor()
        announcements = c.execute('SELECT message_id FROM announce WHERE server_id = ?', (ctx.guild.id,)).fetchall()
        c.close()
        if announcement not in [str(announcement[0]) for announcement in announcements]:
            await ctx.response.send_message('Announcement not found', ephemeral=True)
            return
        # Select the channel from the database
        c = db_announce.cursor()
        the_announcement = c.execute('SELECT * FROM announce WHERE server_id = ? AND message_id = ?', (ctx.guild.id, int(announcement))).fetchall()
        c.close()
        # Update the timestamps
        try:
            channel = await commands.Bot.fetch_channel(self.bot, the_announcement[0][1])
            sent_message = await channel.fetch_message(the_announcement[0][2])
        except discord.NotFound:
            await ctx.response.send_message('Message not found', ephemeral=True)
            return
        content = sent_message.content
        content = re.sub(r"<t:\d{10}(?::[FDTRfdrt])?>", f'<t:{time.time()}:R>', content)
        await sent_message.edit(content=content)
    
    @announce.sub_command(name='delete', description='Removes an announcement from the database')
    async def delete(self, 
            ctx: discord.ApplicationCommandInteraction, 
            announcement: str = commands.Param(name='announcement', description='The announcement ID to delete', autocomplete=get_announcements)):
        # Check if the user has permission to use this command
        if not await self.check_role(ctx):
            return
        # Check if the announcement exists in the database
        c = db_announce.cursor()
        announcements = c.execute('SELECT message_id FROM announce WHERE server_id = ?', (ctx.guild.id,)).fetchall()
        c.close()
        if announcement not in [str(announcement[0]) for announcement in announcements]:
            await ctx.response.send_message('Announcement not found', ephemeral=True)
            return
        # Delete the announcement
        c = db_announce.cursor()
        c.execute('DELETE FROM announce WHERE server_id = ? AND message_id = ?', (ctx.guild.id, int(announcement)))
        db_announce.commit()
        c.close()
        # Send confirmation
        await ctx.response.send_message('Announcement removed from the database', ephemeral=True)
        
class AnnouncementModal(discord.ui.Modal):
    def __init__(self, type: str, announcement: str = None, channel: str = None, *args, **kwargs):
        self.type = type
        if announcement is not None:
            self.announcement = announcement
        if channel is not None:
            self.channel = channel
        components = [
            discord.ui.TextInput(
                label="Announcement", 
                placeholder="I've come to make an announcement",
                custom_id="announcement",
                style=discord.TextInputStyle.long
                )
        ]
        super().__init__(*args, **kwargs, components=components)

    async def callback(self, interaction: discord.ModalInteraction):
        if self.type == 'create':
            sent_message = await interaction.channel.send(interaction.text_values['announcement'])
            c = db_announce.cursor()
            c.execute('INSERT INTO announce VALUES (?, ?, ?)', (interaction.guild_id, sent_message.channel.id, sent_message.id))
            db_announce.commit()
            c.close()
            await interaction.response.send_message('Announcement created', ephemeral=True)
            return
        elif self.type == 'edit':
            try:
                channel = await interaction.bot.fetch_channel(int(self.channel))
                sent_message = await channel.fetch_message(int(self.announcement))
            except discord.NotFound:
                await interaction.response.send_message('Message not found', ephemeral=True)
                return
            await sent_message.edit(content=interaction.text_values['announcement'])
            await interaction.response.send_message('Announcement edited', ephemeral=True)
            return
        

def setup(bot: commands.Bot):
    bot.add_cog(Announce(bot))

def teardown(bot: commands.Bot):
    db.close()
    bot.remove_cog('Announce')
