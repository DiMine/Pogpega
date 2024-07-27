import disnake as discord
from disnake.ext import commands
import sqlite3

db = sqlite3.connect('cogs/databases/db.db')
cur = db.cursor()
cur.execute('CREATE TABLE IF NOT EXISTS announce (server_id, message_id)')
cur.execute('CREATE TABLE IF NOT EXISTS roles (server_id, role_id)')
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
                await ctx.response.send_message('You do not have permission to use this command', ephemeral=True)
                return False
        else:
            await ctx.response.send_message('Role not set', ephemeral=True)
            return False
        return True
    
    @commands.slash_command(name='setrole', description='(Server Admin Only) Set the role of people that can edit the template announcement')
    async def setrole(self, ctx: discord.ApplicationCommandInteraction, role: discord.Role):
        # Check if the user has permission to use this command
        if ctx.author.guild_permissions.administrator:
            c = db.cursor()
            c.execute('DELETE FROM roles WHERE server_id = ?', (ctx.guild.id,))
            c.execute('INSERT INTO roles VALUES (?, ?)', (ctx.guild.id, role.id))
            db.commit()
            c.close()
            await ctx.response.send_message('Role set')
        else:
            await ctx.response.send_message('<a:nuhuh:1262041901440303157> You do not have permission to use this command', ephemeral=True)

    @commands.slash_command(name='unsetrole', description='(Server Admin Only) Unset the role of people that can edit the template announcement')
    async def unsetrole(self, ctx: discord.ApplicationCommandInteraction):
        # Check if the user has permission to use this command
        if ctx.author.guild_permissions.administrator:
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
        modal = AnnouncementModal(title='Create an announcement')
        await ctx.send_modal(modal)
        await modal.wait()
        sent_message = await ctx.send(
            content = modal.children[0].value
        )
        # Add the announcement to the database
        c = db.cursor()
        c.execute('INSERT INTO announce VALUES (?, ?)', (ctx.guild.id, sent_message.id))
        db.commit()
        c.close()
        ctx.response.send_message('Announcement created', ephemeral=True)

    async def get_announcements(ctx: discord.ApplicationCommandInteraction) -> list[str]:
        c = db.cursor()
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
        c = db.cursor()
        announcements = c.execute('SELECT message_id FROM announce WHERE server_id = ?', (ctx.guild.id,)).fetchall()
        c.close()
        if announcement not in [str(announcement[0]) for announcement in announcements]:
            await ctx.response.send_message('Announcement not found in database', ephemeral=True)
            return
        # Send the modal
        modal = AnnouncementModal(title='Edit an announcement')
        await ctx.send_modal(modal)
        await modal.wait()
        # Edit the announcement
        try:
            sent_message = await ctx.fetch_message(announcement)
        except discord.NotFound:
            await ctx.response.send_message('Message not found', ephemeral=True)
            return
        await sent_message.edit(content=modal.children[0].value)
        # Send confirmation
        await ctx.response.send_message('Announcement edited', ephemeral=True)

    
    @announce.sub_command(name='delete', description='Removes an announcement from the database')
    async def delete(self, 
            ctx: discord.ApplicationCommandInteraction, 
            announcement: str = commands.Param(name='announcement', description='The announcement ID to delete', autocomplete=get_announcements)):
        # Check if the user has permission to use this command
        if not await self.check_role(ctx):
            return
        # Check if the announcement exists in the database
        c = db.cursor()
        announcements = c.execute('SELECT message_id FROM announce WHERE server_id = ?', (ctx.guild.id,)).fetchall()
        c.close()
        if announcement not in [str(announcement[0]) for announcement in announcements]:
            await ctx.response.send_message('Announcement not found', ephemeral=True)
            return
        # Delete the announcement
        c = db.cursor()
        c.execute('DELETE FROM announce WHERE server_id = ? AND message_id = ?', (ctx.guild.id, int(announcement)))
        db.commit()
        c.close()
        # Send confirmation
        await ctx.response.send_message('Announcement deleted', ephemeral=True)
        
class AnnouncementModal(discord.ui.Modal):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.add_item(discord.ui.InputText(label="Announcement", placeholder="I've come to make an announcement", style=discord.InputTextStyle.long))

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_message('Saved announcement', ephemeral=True)
        

def setup(bot: commands.Bot):
    bot.add_cog(Announce(bot))
