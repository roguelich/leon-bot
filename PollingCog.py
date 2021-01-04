from discord.ext import commands
import datetime
import os.path
import sqlite3
import asyncio
# from utils import GMT1
from discord import Message, TextChannel, Attachment, Embed, utils, errors
from operator import itemgetter


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
            self.c.execute('CREATE TABLE polls (id INTEGER PRIMARY KEY, author_id INTEGER, opening TIMESTAMP, \
                            closing TIMESTAMP, message_id INTEGER, channel_id INTEGER, content TEXT, title TEXT, '
                           'image TEXT, active INTEGER)')
            self.c.execute('CREATE TABLE options (id INTEGER PRIMARY KEY, poll_id INTEGER, option TEXT, count INTEGER)')
            self.c.execute('CREATE TABLE votes(id INTEGER PRIMARY KEY, poll_id INTEGER, option_id INTEGER, '
                           'voter_id INTEGER)')
            self.con.commit()

    @con_ctx
    def register_poll(self, author_id, opening, closing, channel_id, content, title, image, options):
        values = (None, author_id, opening, closing, None, channel_id, content, title, image, 0)
        self.c.execute('INSERT INTO polls VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', values)
        poll_id = self.c.lastrowid
        for option in options:
            self.c.execute('INSERT INTO options VALUES (?, ?, ?, ?)', (None, poll_id, option, 0))
        return poll_id

    @con_ctx
    def fetch_value(self, key, table, row_id):
        query = 'SELECT {} FROM {} WHERE id=?'.format(key, table)
        self.c.execute(query, (row_id,))
        fetch = self.c.fetchone()[0]
        if fetch is None:
            return
        else:
            return fetch

    @con_ctx
    def change_value(self, key, table, value, row_id):
        query = "UPDATE {} SET {}=? WHERE id=?".format(table, key)
        self.c.execute(query, (value, row_id))

    @con_ctx
    def fetch_poll_data(self, poll_id):
        self.c.execute('SELECT id, author_id, opening, closing, channel_id, content, title, image FROM polls WHERE id=?',
                       (poll_id,))
        polls_fetch = self.c.fetchone()
        self.c.execute('SELECT option FROM options WHERE poll_id=?', (poll_id,))
        options_fetch = self.c.fetchall()
        options = [option_tuple[0] for option_tuple in options_fetch]
        poll_data = {}
        poll_data_keys = ["id", "author_id", "opening", "closing", "channel_id", "content", "title", "image"]
        i = 0
        for value in polls_fetch:
            poll_data[poll_data_keys[i]] = value
            i += 1
        poll_data["options"] = options
        return poll_data

    @con_ctx
    def voted(self, voter_id, poll_id):
        self.c.execute('SELECT id FROM votes WHERE voter_id=? AND poll_id=?', (voter_id, poll_id))
        return bool(self.c.fetchone())

    @con_ctx
    def add_vote(self, poll_id, option, voter_id):
        self.c.execute('SELECT count FROM options WHERE poll_id=? AND option=?', (poll_id, option))
        count = self.c.fetchone()[0]
        count += 1
        self.c.execute('UPDATE options SET count=? WHERE poll_id=? AND option=?', (count, poll_id, option))
        option_id = self.c.lastrowid
        self.c.execute('INSERT INTO votes VALUES (?, ?, ?, ?)', (None, poll_id, option_id, voter_id))

    @con_ctx
    def closed(self, poll_id):
        self.c.execute('SELECT active FROM polls WHERE id=?', (poll_id,))
        return not(self.c.fetchone()[0])

    @con_ctx
    def fetch_results(self, poll_id):
        self.c.execute('SELECT option, count FROM options WHERE poll_id=?', (poll_id,))
        fetch = self.c.fetchall()
        return sorted(fetch, key=itemgetter(1), reverse=True)

    @con_ctx
    def fetch_total_count(self, poll_id):
        self.c.execute('SELECT count FROM options WHERE poll_id=?', (poll_id,))
        fetch = self.c.fetchall()
        total_count = 0
        for count in fetch:
            total_count += count[0]
        return total_count

    @con_ctx
    def fetch_options(self, poll_id):
        self.c.execute('SELECT option FROM options WHERE poll_id=?', (poll_id,))
        fetch = self.c.fetchall()
        options = [option[0] for option in fetch]
        return options


class PollingCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = DbAPI()
        self.leon_color = self.bot.leon_color
        # now_utc = datetime.datetime.now(tz=datetime.timezone.utc)
        # self.now = now_utc.astimezone(GMT1())

    def build_embed(self, guild, poll_data):
        author = utils.find(lambda m: m.id == poll_data["author_id"], guild.members)
        description = "Poll ID: #{}".format(poll_data["id"])
        embed = Embed(title=poll_data["title"], description=description, color=self.leon_color)
        embed.set_author(name=author.name, icon_url=author.avatar_url)
        embed.set_image(url=poll_data["image"])
        embed.set_footer(text="0 votes counted | Closes at {} Paris Time".format(poll_data["closing"].strftime("%H:%M")))
        return embed

    async def run_poll(self, message, closing, poll_id, options, counter):
        embed = message.embeds[0]
        footer = embed.footer.text
        separator = " | "
        footer_sliced = footer.split(separator)

        def check(payload):
            return payload.message_id == message.id

        while True:
            now = datetime.datetime.now()
            delta = closing - now
            try:
                response = await self.bot.wait_for("raw_reaction_add", check=check, timeout=delta.total_seconds())
            except asyncio.TimeoutError:
                await message.edit(embed=embed.set_footer(text=footer_sliced[0] + separator + "Closed"))
                self.db.change_value("active", "polls", 0, poll_id)
                break
            else:
                option = response.emoji.name
                voter_id = response.user_id
                voted = self.db.voted(voter_id, poll_id)
                voter = response.member
                if option not in options:
                    print("ignoring option")
                    pass
                elif voted:
                    try:
                        await voter.send("You already voted in Poll #{}!".format(poll_id))
                    except errors.Forbidden:
                        pass
                else:
                    self.db.add_vote(poll_id, option, voter_id)
                    counter += 1
                    footer_sliced[0] = "{} votes counted".format(counter)
                    await message.edit(embed=embed.set_footer(text=footer_sliced[0] + separator + footer_sliced[1]))
                    try:
                        await voter.send("Your vote in Poll #{} has been counted.".format(poll_id))
                    except errors.Forbidden:
                        pass
                await message.remove_reaction(response.emoji, voter)

    async def open_poll(self, guild, poll_id):
        """
        Constructs a poll message and embed, sends it and sets up a listener
        :param guild:
        :param poll_id:
        :return:
        """
        poll_data = self.db.fetch_poll_data(poll_id)

        embed = self.build_embed(guild, poll_data)
        channel_id = poll_data["channel_id"]
        channel = utils.find(lambda ch: ch.id == channel_id, guild.channels)

        await channel.send(poll_data["content"])
        message = await channel.send(embed=embed)
        for option in (poll_data["options"]):
            await message.add_reaction(option)

        while True:
            updated_message = await message.channel.fetch_message(message.id)
            if len(updated_message.reactions) == len(poll_data["options"]):
                break
            else:
                await asyncio.sleep(0.1)

        self.db.change_value("message_id", "polls", message.id, poll_id)
        self.db.change_value("active", "polls", 1, poll_id)

        counter = 0

        await self.run_poll(message, poll_data["closing"], poll_id, poll_data["options"], counter)

    async def wait_for_opening(self, guild, poll_id):
        """
        Waits for the poll and passes poll_id to open_poll()
        :param guild:
        :param poll_id:
        :return:
        """
        opening = self.db.fetch_value('opening', 'polls', poll_id)
        now = datetime.datetime.now()
        delta = opening - now
        await asyncio.sleep(delta.total_seconds())
        await self.open_poll(guild, poll_id)

    @commands.group(invoke_without_command=True)
    async def poll(self, ctx, *args):
        pass

    @poll.command()
    async def schedule(self, ctx, template: Message, channel: TextChannel, opening_str, closing_str, title):
        try:
            opening_time = datetime.datetime.strptime(opening_str, "%Y-%m-%d %H:%M")
            closing_time = datetime.datetime.strptime(closing_str, "%Y-%m-%d %H:%M")
        except ValueError:
            await ctx.send('Invalid request format, try again')
            return

        try:
            assert opening_time > datetime.datetime.now()
            assert closing_time > opening_time
        except AssertionError:
            await ctx.send('Invalid dates, try again.')
            return

        content = template.content
        options = [reaction.emoji for reaction in template.reactions]

        if len(options) < 2:
            await ctx.send('You must supply at least 2 options.')
            return

        attachment = template.attachments[0]
        image = attachment.url

        poll_id = self.db.register_poll(ctx.author.id, opening_time, closing_time, channel.id, content, title, image,
                                        options)

        await self.wait_for_opening(ctx.guild, poll_id)

    @poll.command()
    async def results(self, ctx, poll_id):
        closed = self.db.closed(poll_id)
        if not closed:
            await ctx.send("The poll hasn't closed yet!")
            return
        results = self.db.fetch_results(poll_id)
        content = ""
        for option in results:
            content += "{}: {}".format(option[0], option[1])
            if results.index(option) < (len(results) - 1):
                content += "\n"
        await ctx.send(content)

    @poll.command()
    async def restart(self, ctx, poll_id):
        poll_id = int(poll_id)
        message_id = self.db.fetch_value("message_id", "polls", poll_id)
        channel_id = self.db.fetch_value("channel_id", "polls", poll_id)
        channel = ctx.guild.get_channel(channel_id)
        message = await channel.fetch_message(message_id)
        reactions = message.reactions
        for reaction in reactions:
            emoji = reaction.emoji
            async for user in reaction.users():
                if not user.id == self.bot.user.id:
                    await message.remove_reaction(emoji, user)
        closing = self.db.fetch_value("closing", "polls", poll_id)
        counter = self.db.fetch_total_count(poll_id)
        options = self.db.fetch_options(poll_id)
        await self.run_poll(message, closing, poll_id, options, counter)


def setup(bot):
    bot.add_cog(PollingCog(bot))
