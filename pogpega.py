import discord
import dotenv
import os

dotenv.load_dotenv()

ADMINS = [int(admin) for admin in os.environ['BOT_ADMINS'].split(',')]

bot = discord.Bot(debug_guilds=[int(os.environ['DISCORD_TEST_SERVER'])])

@bot.event
async def on_ready():
    print('Logged on as', bot.user)

cogs_list = [
    'ego',
    'announce',
    'grief'
]
for cog in cogs_list:
    bot.load_extension(f'cogs.{cog}')

@bot.slash_command(name='refresh_cogs', description='(Bot Admin Only) Refresh all the cogs')
async def refresh_cogs(ctx: discord.ApplicationContext):
    if ctx.author.id in ADMINS:
        for cog in cogs_list:
            bot.reload_extension(f'cogs.{cog}')
        await ctx.respond('Cogs refreshed')
    else:
        await ctx.respond('<a:nuhuh:1262041901440303157> You do not have permission to use this command', ephemeral=True)

@bot.slash_command(name='refresh_cog', description='(Bot Admin Only) Refresh a cog')
@discord.option(name='cog', type=str, description='The cog to refresh', required=True, choices=cogs_list)
async def refresh_cog(ctx: discord.ApplicationContext, cog: str):
    if ctx.author.id in ADMINS:
        if cog in cogs_list:
            bot.reload_extension(f'cogs.{cog}')
            await ctx.respond(f'{cog} refreshed')
        else:
            await ctx.respond(f'<a:nuhuh:1262041901440303157> That is not a valid cog')
    else:
        await ctx.respond('<a:nuhuh:1262041901440303157> You do not have permission to use this command', ephemeral=True)

@bot.slash_command(name='echo', description='(Bot Admin Only) Echo a message')
async def echo(ctx: discord.ApplicationContext, message: str):
    if ctx.author.id in ADMINS:
        await ctx.respond(message)
    else:
        await ctx.respond('<a:nuhuh:1262041901440303157> You do not have permission to use this command', ephemeral=True)

bot.run(os.environ['DISCORD_TOKEN'])
