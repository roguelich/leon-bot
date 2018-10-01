from discord.ext import commands
import discord
import datetime
from utils import GMT1
import re
import json
import os


def count(d, name):
    if name in d:
        d[name] += 1
    else:
        d[name] = 1


class StatCog:
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def stat(self, ctx, *args):

        now_utc = datetime.datetime.now(tz=datetime.timezone.utc)
        now = now_utc.astimezone(GMT1())

        preset = {'limit': None}

        if 'pm' in args:
            bfr_dt = datetime.datetime(now.year, now.month, day=1, hour=0, minute=0, second=0)
            pm = bfr_dt - datetime.timedelta(seconds=1)
            aft_dt = pm.replace(day=1, hour=0, minute=0, second=0)
            preset['before'] = bfr_dt

            fname = '{}_{}.json'.format(pm.month, pm.year)

        else:
            aft_dt = datetime.datetime(now.year, now.month, 1)

            fname = '{}_{}.json'.format(now.month, now.year)

        preset['after'] = aft_dt

        total, pp_member, pp_channel, pp_day = 0, {}, {}, {}
        guild_emojis = {emoji.name: 0 for emoji in ctx.guild.emojis}
        pattern = r':(.*?):'
        p = re.compile(pattern)

        print('Start counting...')

        for channel in ctx.guild.text_channels:
            counter = 0
            async for message in channel.history(**preset):
                try:
                    try:
                        member = message.author.nick
                        assert member is not None
                    except (AttributeError, AssertionError):
                        member = message.author.name

                    mid = message.author.id

                    if mid not in pp_member:
                        pp_member[mid] = [member, 1]
                    else:
                        pp_member[mid][1] += 1

                    matches = p.findall(message.content)
                    for match in matches:
                        if match in guild_emojis:
                            guild_emojis[match] += 1

                    dt = message.created_at
                    dt_aware = dt.replace(tzinfo=datetime.timezone.utc)
                    dt_gmt1 = dt_aware.astimezone(GMT1())
                    day = dt_gmt1.date().isoformat()

                    count(pp_day, day)

                except discord.HTTPException:
                    pass

                finally:
                    total += 1
                    counter += 1

            pp_channel[channel.name] = counter

        stats = {'total': total,
                 'pp_member': pp_member,
                 'pp_channel': pp_channel,
                 'pp_day': pp_day,
                 'emojis': guild_emojis}

        with open(fname, 'w+', encoding='utf-8') as f:
            json.dump(stats, f, ensure_ascii=False)

        print('Done.')

        '''with open(fname, 'rb') as f:
            await ctx.send(file=discord.File(f))

        os.remove(fname)'''


def setup(bot):
    bot.add_cog(StatCog(bot))