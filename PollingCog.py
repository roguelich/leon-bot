from discord.ext import commands
from datetime import datetime, timedelta
from asyncio import sleep
import os.path
import sqlite3
from ast import literal_eval
from discord import Embed, utils, Message, RawReactionActionEvent
from utils import GMT1, super_sort, InvalidSyntax, int_to_uni, uni_to_int
import asyncio
import operator


def con_ctx(f):
    """Wrapper to ensure con.commit()."""
    def wrapper(*args, **kwargs):
        with args[0].con:
            return f(*args, **kwargs)
    return wrapper

class DbAPI:
    def __init__(self):
        file_exists = os.path.isfile('polling.db')
        self.con = sqlite3.connect('polling.db', detect_types=sqlite3.PARSE_COLNAMES | sqlite3.PARSE_DECLTYPES)
        self.c = self.con.cursor()
        if not file_exists:
            self.c.execute('CREATE TABLE polls (id INTEGER PRIMARY KEY, author_id INTEGER, question TEXT,\
                            opening TIMESTAMP, closing_time TIMESTAMP, choice TEXT, priority INTEGER)')
            self.c.execute('CREATE TABLE options (id INTEGER PRIMARY KEY, poll_id INTEGER, option TEXT)')
            self.c.execute('CREATE TABLE votes(id INTEGER PRIMARY KEY, option_id INTEGER, user_id INTEGER)')
            self.con.commit()

    @con_ctx
    def add_poll(self, author_id, question, options, opening, closing_time, choice, priority=0):
        vals = (None, author_id, question, opening, closing_time, choice, priority)
        self.c.execute('INSERT INTO polls VALUES (?, ?, ?, ?, ?, ?, ?)', vals)
        poll_id = self.c.lastrowid
        for option in options:
            self.c.execute('INSERT INTO options VALUES (?, ?, ?)', (None, poll_id, option))
        return poll_id

    @con_ctx
    def close_poll(self, poll_id, closing_time):
        self.c.execute('UPDATE polls SET closing_time = ? WHERE id = ?', (closing_time, poll_id))

    @con_ctx
    def add_vote(self, option_id, user_id):
        self.c.execute('INSERT INTO votes VALUES (?, ?, ?)', (None, option_id, user_id))
        pass

    def fetch_poll(self, poll_id, results=False):
        """Returns a list that: [[0]poll_id: int, [1]author_id: int, [2]question: str, [3]opening: datetime.datetime,
        [4]closing_time: datetime.datetime, [5]choice: text, [6]priority: int,
        [7]options: (option name: str, vote_count: int): list"""

        self.c.execute('SELECT * FROM polls WHERE id = ?', (poll_id,))
        fetch = self.c.fetchone()
        if fetch is None:
            return
        poll_list = list(fetch)
        options = self.c.execute('SELECT * FROM options WHERE poll_id = ?', (poll_id,)).fetchall()
        options_pairs = []

        for option in options:
            if results:
                self.c.execute('SELECT * FROM votes WHERE option_id = ?', (option[0],))
                votes = self.c.fetchall()
                if votes:
                    vote_count = len(votes)
                else:
                    vote_count = 0
                options_pairs.append((option[2], vote_count))
            else:
                options_pairs.append((option[2], option[0]))

        poll_list.append(options_pairs)

        return poll_list

    def fetch_value(self, poll_id, value):
        self.c.execute('SELECT ? FROM polls WHERE id = ?', (value, poll_id))
        fetch = self.c.fetchone()
        if fetch is None:
            return
        else:
            return fetch

    def get_count(self, poll_id):
        self.c.execute('SELECT id FROM options WHERE poll_id = ?', (poll_id,))
        options = self.c.fetchall()
        count = 0
        for option_id in options:
            self.c.execute('SELECT COUNT(id) FROM votes WHERE option_id = ?', option_id)
            for fetch in self.c.fetchall():
                count += fetch[0]
        return count

    def fetch_actives(self):
        self.c.execute('SELECT id, author_id, question, priority FROM polls WHERE closing_time IS NULL')
        polls = self.c.fetchall()
        polls_list = []
        for poll in polls:
            poll_dict = {'id': poll[0],
                         'author_id': poll[1],
                         'question': poll[2],
                         'priority': poll[3],
                         'vote_count': self.get_count(poll[0])}
            polls_list.append(poll_dict)
        return polls_list

    def voted_for_option(self, user_id, option_id):
        self.c.execute('SELECT id FROM votes WHERE user_id = ? AND option_id = ?', (user_id, option_id))
        return bool(self.c.fetchone())

    def voted_in(self, user_id, poll_id):
        self.c.execute('SELECT id FROM options WHERE poll_id = ?', (poll_id,))
        option_ids = self.c.fetchall()
        for option_id in option_ids:
            self.c.execute('SELECT id FROM votes WHERE user_id = ? AND option_id = ?', (user_id, option_id[0]))
            fetch = self.c.fetchone()
            if fetch:
                return True
        return False


def make_description(closing_time, choice):
    # strftime("%d-%m-%Y %H:%M:%S")
    desc = ''
    if not closing_time:
        desc += 'Active'
    else:
        desc += 'Closed'
    desc += ' | {}'.format(choice)
    return desc


def share_bar(x, y):
    if y == 0:
        return ''
    return '#' * int(15 * x/y)


class PollingCog:
    def __init__(self, bot):
        self.bot = bot
        self.db = DbAPI()
        self.leon_color = self.bot.leon_color

    def build_list_embed(self, ctx, fetch):
        embed = Embed(title='Active Polls', color=self.leon_color)
        poll_list = sorted(fetch, key=operator.itemgetter('priority'), reverse=True)
        for poll in poll_list:
            author = ctx.guild.get_member(int(poll['author_id']))
            embed.add_field(name='{}'.format(poll['question']), inline=False, value=
                            'ID: {} | Vote Count: {} | By: {}'.format(poll['id'], poll['vote_count'], author.nick))
        return embed

    def build_poll_embed(self, ctx, poll, results=False):
        member = utils.find(lambda m: m.id == poll[1], ctx.guild.members)
        desc = make_description(poll[4], poll[5])
        embed = Embed(title='{}'.format(poll[2]), description=desc, color=self.leon_color)
        embed.set_author(name=member.nick, icon_url=member.avatar_url)
        options = poll[7]

        if results:
            options_s = super_sort(options)
            votes_total = 0
            for option in options_s:
                votes_total += option[1]

            embed.set_footer(text='{} Votes'.format(votes_total))

            for option in options_s:
                bar = '[{}]'.format(share_bar(option[1], votes_total))
                embed.add_field(name=option[0] + ': ' + str(option[1]), value=bar, inline=False)

            return embed

        else:
            ordered_ids = []
            order_count = 1
            for option in options:
                embed.add_field(name='{}. '.format(order_count), value=option[0], inline=False)
                ordered_ids.append(option[1])
                order_count += 1

            return embed, ordered_ids

    @commands.group(invoke_without_command=True)
    async def poll(self, ctx, *args):

        if args[0].isnumeric() and len(args) > 1:
            if args[1] == "results":
                await ctx.invoke(self.poll.get_command('results'), args[0])

        elif args[0].isnumeric():
            await ctx.invoke(self.poll.get_command('vote'), args[0])

    @poll.command()
    async def create(self, ctx, question, options, *args):
        options_split = options.split()
        if len(options_split) <= 2 or len(options_split) > 10:
            await ctx.send('You have to supply 2-10 options inside quotation marks and separated by spaces.')
            return

        if len(args) > 2:
            raise InvalidSyntax

        args_l = [arg.lower() for arg in args]

        if 'priority' in args_l:
            priority = 1
        else:
            priority = 0

        if 'multi' in args_l:
            choice = 'Multiple Choice'
        else:
            choice = 'Single Choice'

        if priority > 0 and not ctx.author.guild_permissions.administrator:
            await ctx.send('You aren\'t allowed to create a priority poll.')
            return

        options_eval = literal_eval(str(options_split))
        author_id = ctx.author.id
        opening = datetime.now(GMT1())
        closing_time = None

        poll_id = self.db.add_poll(author_id, question, options_eval, opening, closing_time, choice,
                                   priority)

        await ctx.send('Poll #{} has been created. Type in "$poll vote <id>" to vote in it and "$poll results" '
                       'to see the results.'.format(poll_id))

    @poll.command()
    async def results(self, ctx, poll_id):
        poll = self.db.fetch_poll(int(poll_id), results=True)
        if poll is None:
            await ctx.send('Poll not found.')
            return
        embed = self.build_poll_embed(ctx, poll, results=True)
        await ctx.send(embed=embed)

    @poll.command()
    async def list(self, ctx):
        active_polls = self.db.fetch_actives()
        if len(active_polls) == 0:
            await ctx.send('There are no active polls now.')
            return
        embed = self.build_list_embed(ctx, active_polls)
        await ctx.send(embed=embed)

    @poll.command()
    async def vote(self, ctx, poll_id):
        poll = self.db.fetch_poll(int(poll_id))
        if poll is None:
            await ctx.send('Poll not found.')
            return
        embed, ordered_ids = self.build_poll_embed(ctx, poll)
        message = await ctx.send(embed=embed)

        for i in range(len(ordered_ids)):
            unicode = int_to_uni(i+1)
            await message.add_reaction(unicode)

        def check(payload):
            return payload.user_id == ctx.author.id

        end_time = datetime.now() + timedelta(seconds=60)

        while True:
            now = datetime.now()
            remaining = end_time - now

            try:
                response = await self.bot.wait_for('raw_reaction_add', check=check, timeout=remaining.total_seconds())

            except asyncio.TimeoutError:
                break

            else:
                unicode = response.emoji.name
                i = uni_to_int(unicode)
                option_id = ordered_ids[i-1]

                choice = poll[5]
                if choice == "Multiple Choice":
                    if self.db.voted_for_option(ctx.author.id, option_id):
                        await ctx.send('You already voted for that option.')
                        return
                else:
                    if self.db.voted_in(ctx.author.id, poll[0]):
                        await ctx.send('You already voted in that poll.')
                        return

                self.db.add_vote(option_id, ctx.author.id)

                await ctx.send('Your vote has been counted.')

    @poll.command()
    async def close(self, ctx, poll_id):
        poll_author_id = self.db.fetch_value(poll_id, 'author_id')
        if poll_author_id is None:
            await ctx.send('Poll not found')
            return
        if ctx.author.id != poll_author_id and not ctx.author.guild_permissions.administrator:
            await ctx.send('Only the poll\'s author or an administrator can close it.')
            return
        now = datetime.now(GMT1())
        self.db.close_poll(poll_id, now)


def setup(bot):
    bot.add_cog(PollingCog(bot))