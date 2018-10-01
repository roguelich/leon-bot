from discord.ext import commands
import asyncio
import json
import yaml
import os
import discord
from utils import format_help


def get_config(path):
    with open(path) as f:
        return yaml.load(f)


def get_help_pages(path):
    with open(path) as f:
        return f.read()


def get_boards(path):
    with open(path) as f:
        return json.load(f)


def save_config(config, path):
    with open(path, 'w') as f:
        yaml.dump(config, f, default_flow_style=False)


class Leon(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.config = get_config('config.yaml')
        self.boards = get_boards('boards.json')
        self.leon_color = int(0xa7f432)
        self.error_color = int(0xFF2400)
        self.help_pages, self.no_pages = format_help(get_help_pages('coms.txt'), color=self.leon_color)

        async def set_guild():
            await self.wait_until_ready()
            self.guild = self.get_guild(id=self.config['guild_id'])

        self.loop.create_task(set_guild())

    async def on_ready(self):
        print('Logged in as')
        print(self.user.name)
        print(self.user.id)
        print('------')

    def save_config(self):
        save_config(self.config, 'config.yaml')


prefix = os.getenv('PREFIX')
bot = Leon(command_prefix=[prefix])


@bot.check
async def is_disabled(ctx):
    guild_id = bot.config['guild_id']
    guild = bot.get_guild(guild_id)
    member = guild.get_member(ctx.author.id)
    if member.guild_permissions.administrator is True:
        return True
    command = ctx.invoked_with
    disabled_commands = bot.config['disabled_commands']
    if command not in disabled_commands.keys():
        return True
    elif disabled_commands[command] == '*':
        await ctx.send('Error! This command has been globally disabled.')
        return False
    if ctx.author.id in disabled_commands[command]:
        await ctx.send('Error! You aren\'t allowed to use that command.')
        return False
    return True


bot.remove_command('help')
bot.load_extension('LeonCog')
bot.load_extension('PollingCog')
bot.load_extension('StatCog')
token = os.getenv('TOKEN')
bot.run(token)
