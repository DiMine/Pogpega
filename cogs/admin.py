import disnake as discord
from disnake.ext import commands
import dotenv
import os
import aiohttp
import json

dotenv.load_dotenv()

pxls_auth = os.environ['PXLS_AUTH']

ADMINS = [int(admin) for admin in os.environ['BOT_ADMINS'].split(',')]

class Admin(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    def cog_slash_command_check(self, ctx: discord.ApplicationCommandInteraction):
        return ctx.author.id in ADMINS

    # @commands.Cog.listener()    
    # async def on_slash_command_error(self, ctx, error):
    #     if isinstance(error, commands.errors.CheckFailure):
    #         await ctx.response.send_message('<a:nuhuh:1262041901440303157> You do not have permission to use this command', ephemeral=True)

    # @commands.slash_command(name='admin_echo', description='(Bot Admin Only) Echo a message')
    # async def echo(self, ctx: discord.ApplicationCommandInteraction, message: str):
    #     await ctx.response.send_message(message)

    # @commands.slash_command(name='admin_edit', description='(Bot Admin Only) Edit any message sent by the bot')
    # async def edit(
    #     self,
    #     ctx: discord.ApplicationCommandInteraction, 
    #     message_id: int = commands.Param(name='message_id', description='The message ID to edit'),
    #     message: str = commands.Param(name='message', description='The new message')):
    #     try:
    #         message = await ctx.channel.fetch_message(message_id)
    #         await message.edit(content=message)
    #     except discord.NotFound:
    #         await ctx.response.send_message('Message not found', ephemeral=True)

    # @commands.slash_command(name='admin_delete', description='(Bot Admin Only) Delete any message sent by the bot')
    # async def delete(
    #     self,
    #     ctx: discord.ApplicationCommandInteraction, 
    #     message_id: int = commands.Param(name='message_id', description='The message ID to delete')):
    #     try:
    #         message = await ctx.channel.fetch_message(message_id)
    #         await message.delete()
    #     except discord.NotFound:
    #         await ctx.response.send_message('Message not found', ephemeral=True)

    @commands.slash_command(name='infodownload', description='(Bot Admin Only) Download the info page from pxls.space')
    async def infodownload(self, ctx: discord.ApplicationCommandInteraction):
        headers = {
            "x-pxls-cfauth": pxls_auth
        }
        timeout = aiohttp.ClientTimeout(sock_connect=10, sock_read=10)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get("https://pxls.space/info", headers=headers) as response:
                info = await response.json()
                with open('info/info.json', 'w') as f:
                    f.write(json.dumps(info))
        await ctx.response.send_message('Info page downloaded')
    

def setup(bot: commands.Bot):
    bot.add_cog(Admin(bot))

def teardown(bot: commands.Bot):
    bot.remove_cog('Admin')