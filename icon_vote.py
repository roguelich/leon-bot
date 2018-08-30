from discord import Embed
import datetime
from utils import random_color
import asyncio
import aiohttp


class VotingError(Exception):
    pass


class IconVote(object):

    def __init__(self, votes_required, color):
        self.author = None
        self.link = None
        self.votes_required = votes_required
        self.votes = votes_required
        self.voted = []
        self.timeout = 300
        self.color = color

    async def _checkImg(self, ctx, link):
        if link is None:
            try:
                link = ctx.message.attachments[0].url
            except:
                await ctx.send('No image provided.')
                return False
        link_no = link.lower()
        if link_no.endswith('.jpg') or link_no.endswith('.jpeg') or link_no.endswith('.png'):
            return link
        await ctx.send('Invalid image format(JPG/PNG only).')
        return False

    def _votingOn(self):
        if self.author:
            return True
        return False

    def _makeEmbed(self, author):
        embed = Embed(color=self.color, title='{} votes required to pass the icon.'.format(self.votes))
        embed.set_author(name=author.nick, icon_url=author.avatar_url)
        embed.set_image(url=self.link)
        return embed

    def _reset(self):
        self.author = None
        self.link = None
        self.votes = self.votes_required
        self.voted = []

    async def _dlIcon(self, link):
        async with aiohttp.ClientSession() as session:
            async with session.get(link) as resp:
                return await resp.read()

    async def view_submission(self, ctx):
        author = self.author
        embed = self._makeEmbed(author)
        await ctx.send(content=None, embed=embed)

    async def passSubmission(self, ctx):
        if not self._votingOn():
            return
        await ctx.send('{}\'s submission has been approved. Changing the icon...'.format(self.author.display_name))
        await ctx.guild.edit(icon=await self._dlIcon(self.link))
        self._reset()

    async def check_votes(self, ctx, delta):
        end_time = datetime.datetime.now() + delta
        sec = datetime.timedelta(seconds=1)
        while True:
            if (datetime.datetime.now() + sec) >= end_time:
                await ctx.send('Failed to pass the submission on time.')
                self._reset()
                break
            elif self.votes == 0:
                await self.passSubmission(ctx)
                break
            elif self.author is None:
                break
            await asyncio.sleep(1)

    async def submit(self, ctx, link):
        link = await self._checkImg(ctx, link)
        if not link:
            return
        if self._votingOn():
            await ctx.send('Somebody has already made a submission.')
            return
        self.link = link
        self.author = ctx.author
        await ctx.send('Your icon has been submitted.')
        await self.check_votes(ctx, datetime.timedelta(seconds=self.timeout))

    async def addVote(self, ctx):
        if not self._votingOn():
            await ctx.send('There\'s no active voting going on.')
            return
        elif ctx.author == self.author:
            await ctx.send('You can\'t vote for your own submission.')
            return
        elif ctx.author in self.voted:
            await ctx.send('You can only vote once!')
            return
        self.votes -= 1
        if self.votes != 0:
            self.voted.append(ctx.author)
            await ctx.send('Your vote has been counted, {} more votes required.'.format(self.votes))

    async def reject(self, ctx):
        if not self._votingOn():
            return
        self._reset()
        await ctx.send('The submission has been rejected.')