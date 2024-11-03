import disnake as discord
from disnake.ext import commands
from PIL import Image
import os
from io import BytesIO
import time

class Fun(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.you_know_what_that_means = []
        # loop through the frames in the directory
        for i in range(0, 21):
            # open the image
            img = Image.open(f'other/frames/frame_{i}.png')
            # append the image to the list
            self.you_know_what_that_means.append(img)
        print('You know what that means loaded')

    
    @commands.slash_command(name='youknowwhatthatmeans', description='Add an image to the "You know what that means" gif')
    async def youknowwhatthatmeans(self, 
                  ctx: discord.ApplicationCommandInteraction, 
                  image: discord.Attachment = commands.Param(name='image', description='The image to add'),
                  sticker: bool = commands.Param(name='sticker', description='Resize the gif so it can be made into a discord sticker (default: false)', default=False)):
        await ctx.response.defer()
        # if image.content_type != 'image/png':
        #     await ctx.followup.send('The attachment must be a png image')
        #     return
        # save the image
        now = time.time()
        await image.save(f'other/frames/{ctx.guild_id}-{ctx.author.id}-{now}.png')
        img = Image.open(f'other/frames/{ctx.guild_id}-{ctx.author.id}-{now}.png').convert('RGBA')
        youknowwhatthatmeans = self.you_know_what_that_means.copy()
        # Paste the image onto the youknowwhatthatmeans frames
        tmp = img.copy().resize((9, 9))
        youknowwhatthatmeans[6].paste(tmp, (242, 234, 251, 243), tmp)
        tmp = img.copy().resize((13, 13))
        youknowwhatthatmeans[7].paste(tmp, (253, 228, 266, 241), tmp)
        youknowwhatthatmeans[8].paste(tmp, (257, 226, 270, 239), tmp)
        youknowwhatthatmeans[9].paste(tmp, (272, 222, 285, 235), tmp)
        tmp = img.copy().resize((22, 21))
        youknowwhatthatmeans[10].paste(tmp, (280, 215, 302, 236), tmp)
        tmp = img.copy().resize((22, 20))
        youknowwhatthatmeans[11].paste(tmp, (291, 208, 313, 228), tmp)
        youknowwhatthatmeans[12].paste(tmp, (296, 204, 318, 224), tmp)
        tmp = img.copy().resize((27, 25))
        youknowwhatthatmeans[13].paste(tmp, (300, 189, 327, 214), tmp)
        tmp = img.copy().resize((31, 29))
        youknowwhatthatmeans[14].paste(tmp, (307, 185, 338, 214), tmp)
        tmp = img.copy().resize((32, 29))
        youknowwhatthatmeans[15].paste(tmp, (313, 181, 345, 210), tmp)
        tmp = img.copy().resize((36, 33))
        youknowwhatthatmeans[16].paste(tmp, (308, 183, 344, 216), tmp)
        tmp = img.copy().resize((47, 44))
        youknowwhatthatmeans[17].paste(tmp, (309, 169, 356, 213), tmp)
        tmp = img.copy().resize((89, 83))
        youknowwhatthatmeans[18].paste(tmp, (283, 141, 372, 224), tmp)
        tmp = img.copy().resize((110, 115))
        youknowwhatthatmeans[19].paste(tmp, (279, 125, 389, 240), tmp)
        tmp = img.copy().resize((379, 274))
        youknowwhatthatmeans[20].paste(tmp, (0, 102, 379, 376), tmp)

        # Delete the original image from the frames directory
        os.remove(f'other/frames/{ctx.guild_id}-{ctx.author.id}-{now}.png')

        if sticker:
            # resize to 320x320
            for i in range(len(youknowwhatthatmeans)):
                youknowwhatthatmeans[i] = youknowwhatthatmeans[i].resize((320, 320))

        with BytesIO() as fp:
            youknowwhatthatmeans[0].save(fp, format='GIF', save_all=True, append_images=youknowwhatthatmeans[1:], duration=0.1, loop=0, optimize=True)
            fp.seek(0)
            # edit the message with an embed
            await ctx.followup.send(files=[discord.File(fp=fp, filename='youknowwhatthatmeans.gif')])
    

def setup(bot: commands.Bot):
    bot.add_cog(Fun(bot))

def teardown(bot: commands.Bot):
    bot.remove_cog('Fun')