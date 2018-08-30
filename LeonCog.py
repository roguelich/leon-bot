import discord
from discord.ext import commands
from forex_python.converter import CurrencyRates
from forex_python.bitcoin import BtcConverter
import asyncio
import aiohttp
from lxml import html
import operator
import datetime
import os
from utils import *
import datetime
from PollingCog import GMT1
import sys, traceback
from icon_vote import IconVote


def find_member(ctx, name):
    return ctx.guild.get_member_named(name)


async def look_for_m(ctx, name):
    member = ctx.guild.get_member_named(name)
    if member is None:
        await ctx.send('{} not found!'.format(name))
        return
    return member


async def auth_or_mem(ctx, name):
    if name:
        member = await look_for_m(ctx, name)
    else:
        member = ctx.author
    return member


def get_member(ctx, args):
    '''
    Returns only the member object
    '''
    nickname = ' '.join(args)
    return discord.utils.find(lambda m: m.name == nickname or m.nick == nickname, ctx.guild.members)


class LeonCog:
    def __init__(self, bot):
        self.bot = bot
        self.help_pages = bot.help_pages
        self.no_pages = bot.no_pages
        self.boards = bot.boards
        self.config = bot.config
        self.leon_color = self.bot.leon_color
        self.iv = IconVote(3, self.leon_color)
        self.waits = {}
        self.prefix = self.bot.command_prefix

    @commands.command(name='help')
    async def _help(self, ctx):
        page = 0
        last_page = self.no_pages - 1
        message = await ctx.send(content=None, embed=self.help_pages[page])
        await message.add_reaction('\u23EE')
        await message.add_reaction('\u25C0')
        await message.add_reaction('\u25B6')
        await message.add_reaction('\u23ED')
        await message.add_reaction('\U0001f522')
        await message.add_reaction('\u23F9')

        def check(payload):
            return payload.user_id == ctx.author.id
        try:
            while True:
                payload = await self.bot.wait_for('raw_reaction_add', timeout=120.0, check=check)

                if payload.emoji.name == '\u23EE':
                    page = 0

                elif payload.emoji.name == '\u25C0':
                    if page == 0:
                        page = last_page
                    else:
                        page -= 1

                elif payload.emoji.name == '\u25B6':
                    if page == last_page:
                        page = 0
                    else:
                        page += 1

                elif payload.emoji.name == '\u23ED':
                    page = last_page

                elif payload.emoji.name == '\U0001f522':
                    await ctx.send('Which page do you want me to go to?')
                    resp = await self.bot.wait_for('message', check=lambda message: message.content.isdigit() and message.author is ctx.author)
                    page = int(resp.content)
                    page -= 1

                elif payload.emoji.name == '\u23F9':
                    await message.delete()
                    return

                await message.edit(embed=self.help_pages[page])
                await message.remove_reaction(payload.emoji, ctx.author)

        except asyncio.TimeoutError:
            pass

    @commands.group(invoke_without_command=True)
    async def color(self, ctx):
        pass

    @color.command(name='set')
    async def _set(self, ctx, hex_code):
        if not hex_code.startswith('#'):
            hex_code = '#' + hex_code
        try:
            assert hex_code != '#000000'
        except AssertionError:
            await ctx.send('Black is not a colour!')
            return
        if is_reserved(hex_code, self.config['reserved_colors']):
            await ctx.send('This color is in a reserved range.')
            return
        hex_int = int(hex_code.replace('#', '0x'), 16)
        color = discord.Color(hex_int)
        requested = discord.utils.find(lambda r: hex_code in r.name, ctx.guild.roles)
        previous = discord.utils.find(lambda r: 'color' in r.name, ctx.author.roles)
        if previous:
            sharing = discord.utils.find(lambda m: previous in m.roles and m is not ctx.author, ctx.guild.members)
            if not sharing:
                await previous.edit(name='color {}'.format(hex_code), color=color)
                return
            else:
                await ctx.author.remove_roles(previous)
        else:
            if requested:
                await ctx.author.add_roles(requested)
                return
        new_role = await ctx.guild.create_role(name='color {}'.format(hex_code), color=color)
        await ctx.author.add_roles(new_role)

    @commands.command()
    async def cset(self, ctx, hex_code):
        await ctx.invoke(self.color.get_command('set'), hex_code)

    @color.command(name='remove')
    async def _remove(self, ctx):
        crole = discord.utils.find(lambda r: 'color' in r.name, ctx.author.roles)
        if not crole:
            return
        sharing = discord.utils.find(lambda m: crole in m.roles and m is not ctx.author, ctx.guild.members)
        if sharing:
            await ctx.author.remove_roles(crole)
        else:
            await crole.delete()

    @commands.command()
    async def crem(self, ctx):
        await ctx.invoke(self.color.get_command('remove'))

    @color.command()
    async def code(self, ctx, name=None):
        member = await auth_or_mem(ctx, name)
        if member:
            await ctx.send('{}'.format(str(hex(member.color.value)).replace('0x', '#')))

    @commands.command()
    async def ccode(self, ctx, name=None):
        await ctx.invoke(self.color.get_command('code'), name)

    @color.command()
    async def get(self, ctx, name):
        member = await look_for_m(ctx, name)
        if not member:
            return
        crole = discord.utils.find(lambda r: 'color' in r.name, member.roles)
        if not crole:
            await ctx.send('{} has no color role.'.format(name))
            return
        previous = discord.utils.find(lambda r: 'color' in r.name, ctx.author.roles)
        if previous:
            sharing = discord.utils.find(lambda m: previous in m.roles and m is not ctx.author, ctx.guild.members)
            if not sharing:
                await ctx.guild.delete_roles(previous)
            else:
                await ctx.author.remove_roles(previous)
        await ctx.author.add_roles(crole)

    @commands.command()
    async def cget(self, ctx, name=None):
        await ctx.invoke(self.color.get_command('get'), name)

    @commands.command()
    async def avatar(self, ctx, name=None):
        member = await auth_or_mem(ctx, name)
        if member:
            await ctx.send('{}'.format(member.avatar_url_as(format='jpg')))

    @commands.command()
    async def id(self, ctx, name=None):
        member = await auth_or_mem(ctx, name)
        if member:
            await ctx.send("{}".format(member.id))

    @commands.command()
    async def joined(self, ctx, name=None):
        member = await auth_or_mem(ctx, name)
        if member:
            await ctx.send("{0}" .format(member.joined_at.strftime("%Y-%m-%d %H:%M:%S")))
                
    @commands.group(invoke_without_command=True)
    async def ex(self, ctx, *args):
        pass
        
    @ex.command()
    async def rate(self, ctx, *args):
        if len(args) is 1:
            cur = args[0].split('/')
            cur1, cur2 = cur[1], cur[2]
        elif len(args) is 2:
            cur1, cur2 = args[0], args[1]
        else:
            raise InvalidSyntax
        cur1, cur2 = cur1.upper(), cur2.upper()
        if cur1 == 'BTC':
            b = BtcConverter()
            rate = b.get_latest_price(cur2)
        elif cur2 == 'BTC':
            b = BtcConverter()
            rate = b.get_latest_price(cur1)
        else:
            c = CurrencyRates()
            rate = c.get_rate(cur1, cur2)
        await ctx.send('{}'.format(rate))
        
    @ex.command()
    async def convert(self, ctx, *args):
        if len(args) is not 3:
            return
        cur1, cur2, amount = args[0], args[1], float(args[2])
        cur1, cur2 = cur1.upper(), cur2.upper()
        if cur1 == 'BTC':
            b = BtcConverter()
            result = b.convert_btc_to_cur(amount, cur2)
        if cur2 == 'BTC':
            b = BtcConverter()
            result = b.convert_to_btc(amount, cur1)
        else:
            c = CurrencyRates()
            result = c.convert(cur1, cur2, amount)
        await ctx.send('{}'.format(result))
        
    @commands.command()
    async def roll(self, ctx, dice=6):
        roll = random.randrange(1, dice+1)
        await ctx.send('{}'.format(roll))
        
    # 4pic
    @commands.command(name='4pic')
    async def _4pic(self, ctx, board=None):
        pics = []
        if board is None:
            board = random.choice(list(self.boards.keys()))
        async with aiohttp.ClientSession() as session:
            async with session.get('http://a.4cdn.org/{}/threads.json'.format(board)) as resp:
                resp = await resp.json()
            page = random.choice(resp)
            threads = page['threads']
            thread = random.choice(threads)
            async with session.get('http://a.4cdn.org/{}/thread/{}.json'.format(board,thread['no'])) as resp:
                resp = await resp.json()
            for post in resp['posts']:
                if 'tim' in post.keys() and post['ext'] != '.swf':
                    no_pic = []
                    no_pic.append(post['no'])
                    no_pic.append(str(post['tim']) + post['ext'])
                    pics.append(no_pic)
        no_pic = random.choice(pics)
        pic = no_pic[1]
        no = no_pic[0]
        embed = discord.Embed(colour=discord.Color(0x559f3a))
        link = 'http://boards.4chan.org/{}/thread/{}#p{}'.format(board,thread['no'], no)
        embed.set_author(name='>>>/{}/{}'.format(board, no), url=link, icon_url='http://i.imgur.com/jabqg1m.png')
        if not pic.endswith('webm'):
            embed.set_image(url='http://i.4cdn.org/{}/{}'.format(board, pic))
            await ctx.send(embed=embed)
        else:
            await ctx.send(content='http://i.4cdn.org/{}/{}'.format(board, pic))
            
    @commands.command(name='4chan')
    async def _4chan(self, ctx, board=None):
        if board is None:
            board = random.choice(list(self.boards.keys()))
        async with aiohttp.ClientSession() as session:
            async with session.get('http://a.4cdn.org/{}/threads.json'.format(board)) as resp:
                resp = await resp.json()
            page = random.choice(resp)
            threads = page['threads']
            thread = random.choice(threads)
            async with session.get('http://a.4cdn.org/{}/thread/{}.json'.format(board,thread['no'])) as resp:
                resp = await resp.json()
            post = random.choice(resp['posts'])
        if 'com' in post.keys():
            text = re.sub('<br>', '\n', post['com'])
            text = html.fromstring(text).text_content()
            embed = discord.Embed(description=text, colour=discord.Color(0x559f3a))
        else:
            embed = discord.Embed(colour=discord.Color(0x559f3a))
        link = 'http://boards.4chan.org/{}/thread/{}#p{}'.format(board,thread['no'],post['no'])
        embed.set_author(name='>>>/{}/{}'.format(board, post['no']), url=link, icon_url='http://i.imgur.com/jabqg1m.png')
        if 'ext' in post.keys() and 'ext' not in ['.webm', '.swf']:
            embed.set_image(url='http://i.4cdn.org/{}/{}'.format(board, str(post['tim'])+post['ext']))
        await ctx.send(embed=embed)
    
    @commands.command()
    @commands.has_permissions(administrator=True)    
    async def stat(self, ctx, option=None):

        def write_iter(iterable):
            for el in iterable:
                f.write('{} {}\n'.format(el[0], el[1]))
        now_utc = datetime.datetime.now(tz=datetime.timezone.utc)
        now = now_utc.astimezone(GMT1())
        if option:
            if option == '-lm':
                after_dt = datetime.datetime(now.year, now.month, 1)
                preset = {'limit': None, 'after': after_dt}
            elif option == '-pm':
                before_dt = datetime.datetime(now.year, now.month, 1) - datetime.timedelta(seconds=1)
                print(before_dt)
                after_dt = before_dt.replace(day=1, hour=0, minute=0, second=0)
                print(after_dt)
                preset = {'limit': None, 'before': before_dt, 'after': after_dt}
            else:
                return
        else:
            preset = {'limit': None}

        posts, channels, days, total = {}, {}, {}, 0
        emojis = {emoji.name: 0 for emoji in ctx.guild.emojis}
        pattern = r':(.*?):'
        p = re.compile(pattern)

        async with ctx.channel.typing():
            for channel in ctx.guild.channels:
                if not isinstance(channel, discord.channel.TextChannel):
                    continue
                print('Retrieving messages from {}...'.format(channel.name))
                counter = 0
                async for message in channel.history(**preset):
                    try:
                        counter += 1
                        total += 1
                        if message.author.name in posts:
                            posts[message.author.name] += 1
                        else:
                            posts[message.author.name] = 1
                        matches = p.findall(message.content)
                        for match in matches:
                            if match not in emojis.keys():
                                continue
                            else:
                                emojis[match] += 1
                        dt = message.created_at
                        dt_aware = dt.replace(tzinfo=datetime.timezone.utc)
                        dt_gmt1 = dt_aware.astimezone(GMT1())
                        day = dt_gmt1.date().isoformat()
                        if day not in days:
                            days[day] = 1
                        else:
                            days[day] += 1
                    except discord.HTTPException:
                        print('error')
                channels[channel.name] = counter
                print('{} messages retrieved.'.format(counter))
        await ctx.send('Retrieving done!')

        posts_sort, channels_sort, emojis_sort = super_sort(posts.items()), super_sort(channels.items()), super_sort(emojis.items())
        days_sort = sorted(days.items(), key=operator.itemgetter(0))
        filename = "{}_{}_{}.txt".format(now.day, now.month, now.year)
        with open(filename, 'w+', encoding='utf-8') as f:
            write_iter(posts_sort)
            f.write('\n')
            write_iter(channels_sort)
            f.write('\n')
            f.write('total: {}\n'.format(total))
            f.write('\n')
            write_iter(days_sort)
            f.write('\n')
            write_iter(emojis_sort)
        with open(filename, 'rb') as f:
            await ctx.send(file=discord.File(f))
        os.remove(filename)
        
    @commands.command()
    async def created_at(self, ctx):
        print(ctx.message.created_at.day)
        
    @commands.group(invoke_without_command=True)
    async def ghost(self, ctx, channel=None, content=None):
        pass

    @ghost.command()
    async def chset(self, ctx, channel_name):
        async def appearance(ch, content):
            def sub_mention(match):
                group = match.group(0)
                nick = re.sub('[\[\]@]', '', group)  # \[|\]|@
                if '#' in nick:
                    nick = nick.split('#', 1)[0]
                member = guild.get_member_named(nick)
                if member is None:
                    return nick
                return member.mention

            sub_content = re.sub('\\[(.*)\\]|(@\\S+)', sub_mention, str(content))
            if sub_content:
                await ch.send(sub_content)
            else:
                await ch.send(content)

        await ctx.invoke(self.bot.get_command('ghost off'))

        guild = self.bot.guild
        channel = discord.utils.get(guild.channels, name=channel_name)

        if not channel:
            await ctx.send('Channel "{}" not found.'.format(channel_name))
            return

        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel

        while True:
            cor = self.bot.wait_for('message', timeout=600, check=check)
            fut = asyncio.ensure_future(cor)
            self.waits[(ctx.author.id, ctx.channel.id)] = fut
            try:
                message = await fut
            except (asyncio.TimeoutError, asyncio.CancelledError):
                self.waits.pop((ctx.author.id, ctx.channel.id))
                break
            else:
                await appearance(channel, message.content)

        await ctx.send('{} session closed.'.format(channel.name))

    @ghost.command(name='off')
    async def off(self, ctx):
        if (ctx.author.id, ctx.channel.id) in self.waits:
            self.waits[(ctx.author.id, ctx.channel.id)].cancel()

    # mod tools
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def purge(self, ctx, no, nickname=None):
        no = int(no)
        if no > 100:
            raise Exception('limit exceeded')

        async def purge_iter(iterator):
            count = 0
            while count < no:
                msg = await iterator.next()
                if msg.id == ctx.message.id:
                    continue
                await msg.delete()
                count += 1
        if nickname is not None:
            def predicate(message):
                return message.author.name == nickname
            iterator = ctx.channel.history().filter(predicate)
        else: 
            iterator = ctx.channel.history()
        await purge_iter(iterator)
        
    @commands.group(invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    async def role(self, ctx):
        pass
    
    @role.command()
    @commands.has_permissions(administrator=True)
    async def add(self, ctx, nickname, role):
        member = discord.utils.find(lambda m: m.name == nickname or m.nick == nickname, ctx.guild.members)
        role = discord.utils.get(ctx.guild.roles, name=role)
        await member.add_roles(role)
        
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def radd(self, ctx, nickname, role):
        await ctx.invoke(self.role.get_command('add'), nickname, role)

    @role.command(aliases=['rem'])
    @commands.has_permissions(administrator=True)
    async def remove(self, ctx, nickname, role):
        member = discord.utils.find(lambda m: m.name == nickname or m.nick == nickname, ctx.guild.members)
        role = discord.utils.get(ctx.guild.roles, name=role)
        await member.remove_roles(role)
        
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def rrem(self, ctx, nickname, role):
        await ctx.invoke(self.role.get_command('remove'), nickname, role)

    @role.command(aliases=['del'])
    @commands.has_permissions(administrator=True)
    async def delete(self, ctx, role):
        role = discord.utils.get(ctx.guild.roles, name=role)
        await role.delete()

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def topic(self, ctx, topic: str):
        await ctx.channel.edit(topic=topic)
        
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def kick(self, ctx, nickname, reason=None):
        member = get_member(ctx, nickname)
        await member.kick(reason=reason)
        
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def ban(self, ctx, nickname, reason=None):
        member = get_member(ctx, nickname)
        await member.ban(reason=reason)
        
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def unban(self, ctx, nickname, reason=None):
        member = get_member(ctx, nickname)
        await member.unban(reason=reason)

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def disable(self, ctx, command, *nicknames):
        disabled_commands = self.config['disabled_commands']
        modified = False
        if disabled_commands is None:
            self.config['disabled_commands'] = {}
        if command not in disabled_commands:
            self.config['disabled_commands'][command] = []
        elif disabled_commands == '*':
            return
        if len(nicknames) > 0 :
            members = [ctx.guild.get_member_named(nickname) for nickname in nicknames]
            for member in members:
                self.config['disabled_commands'][command].append(member.id)
                modified = True

            await ctx.send('Command {} has been disabled for members: {}.'.format(command, ", ".join(nicknames)))
        else:
            self.config['disabled_commands'][command] = '*'
            modified = True

            await ctx.send('Command {} has been disabled globally'.format(command))
        if modified:
            self.bot.save_config()

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def check_admin(self, ctx):
        for member in ctx.guild.members:
            if member.guild_permissions.administrator is True:
                await ctx.send(member.name)


    @commands.command()
    @commands.has_permissions(administrator=True)
    async def enable(self, ctx, command, *nicknames):
        disabled_commands = self.config['disabled_commands']
        modified = False
        if command not in disabled_commands:
            await ctx.send('Command not found or isn\'t disabled for anyone.')
            return
        if len(nicknames) > 0:
            if disabled_commands[command] == '*':
                await ctx.send('Error! This command has been globally disabled')
                return
            members = [ctx.guild.get_member_named(nickname) for nickname in nicknames]
            for member in members:
                if member.id in disabled_commands[command]:
                    self.config['disabled_commands'][command].remove(member.id)
                    modified = True

                await ctx.send('Command {} has been enabled for members: {}.'.format(command, ", ".join(nicknames)))
        else:
            disabled_commands.pop(command, None)
            modified = True

            await ctx.send('Command {} has been globally enabled.'.format(command))
        if modified:
            self.bot.save_config()

    # Icon Vote
    @commands.group(invoke_without_command=True)
    async def icon(self, ctx):
        pass

    @icon.command()
    @commands.has_permissions(administrator=True)
    async def set(self, ctx, link=None):
        img = await self.iv._checkImg(ctx, link)
        if img:
            await ctx.guild.edit(icon = await self.iv._dlIcon(img))
    
    @icon.command()
    async def submit(self, ctx, link=None):
        await self.iv.submit(ctx, link)
       
    @icon.command()
    async def vote(self, ctx):
        await self.iv.addVote(ctx)
        
    @icon.command()
    async def view(self, ctx):
        await self.iv.message(ctx)
        
    @icon.command(name='pass')
    @commands.has_permissions(administrator=True)
    async def pass_sub(self, ctx):
        await self.iv.passSubmission(ctx)
    
    @icon.command()
    @commands.has_permissions(administrator=True)
    async def reject(self, ctx):
        await self.iv.reject(ctx)

    async def on_command_error(self, ctx, error):
        errors = ['Do. Not. Panic.',
                  'Houston, we\'ve HAD a problem.',
                  'Achtung! Achtung!',
                  'Just dodge the bullets!',
                  'Bad, bad lizard']

        if isinstance(error, commands.MissingPermissions):
            await ctx.send('Insufficient permissions.')

        elif isinstance(error, commands.errors.CommandNotFound):
            await ctx.send('Command not found.')

        elif isinstance(error, InvalidSyntax) or isinstance(error, discord.ext.commands.errors.MissingRequiredArgument):
            await ctx.send('Invalid syntax! Check {}help.'.format(self.prefix))

        elif isinstance(error, commands.errors.CheckFailure):
            pass

        else:
            traceback.print_exception(type(error), error, error.__traceback__, file=sys.stderr)

            embed = discord.Embed(color=self.bot.error_color)
            embed.add_field(name=random.choice(errors), value='Some unhandled exception occurred.')

            await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(LeonCog(bot))
