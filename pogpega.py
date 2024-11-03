import disnake as discord
from disnake.ext import commands
import dotenv
import os
import logging

logging.basicConfig(level=logging.INFO)

dotenv.load_dotenv()

ADMINS = [int(admin) for admin in os.environ['BOT_ADMINS'].split(',')]

bot = commands.InteractionBot()#test_guilds=[int(server) for server in os.environ['DISCORD_TEST_SERVERS'].split(',')])

@bot.event
async def on_ready():
    print('Logged on as', bot.user)

cogs_list = [
    'admin',
    'ego',
    'announce',
    'grief',
    'fun'
    # 'points'
]
for cog in cogs_list:
    bot.load_extension(f'cogs.{cog}')

def check_admin(ctx: discord.ApplicationCommandInteraction):
    return ctx.author.id in ADMINS

# @bot.event
# async def on_slash_command_error(ctx, error):
#     if isinstance(error, commands.errors.CheckFailure):
#         await ctx.response.send_message('<a:nuhuh:1262041901440303157> You do not have permission to use this command', ephemeral=True)

# @bot.event
# async def on_error(ctx, error):
#     print("---- Error ----")
#     logging.error(error)


@bot.slash_command(name='refresh_cogs', description='(Bot Admin Only) Refresh all the cogs')
@commands.check(check_admin)
async def refresh_cogs(ctx: discord.ApplicationCommandInteraction):
    for cog in cogs_list:
        bot.reload_extension(f'cogs.{cog}')
        await ctx.response.send_message('Cogs refreshed')

@bot.slash_command(name='refresh_cog', description='(Bot Admin Only) Refresh a cog')
@commands.check(check_admin)
async def refresh_cog(
    ctx: discord.ApplicationCommandInteraction, 
    cog: str = commands.Param(name='cog', description='The cog to refresh', choices=cogs_list)):
    bot.reload_extension(f'cogs.{cog}')
    await ctx.response.send_message(f'{cog} refreshed')

bot.run(os.environ['DISCORD_TOKEN'])
