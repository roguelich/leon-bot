import discord
from discord.ext import commands
import colorsys
import random
import re
            
spectrums = """```
red-yellow
yellow-green
green-cyan
cyan-blue
blue-magenta
magenta-red
#rrggbb-#rrggbb
h,l,s-h,l,s
```"""

def random_color():
    x = lambda: random.randint(0, 255)
    return discord.Colour.from_rgb(x(), x(), x())

def hls_to_Colour(h, l, s):
    r,g,b = colorsys.hls_to_rgb(h,l,s)
    convert = lambda x: int(x*255)
    r,g,b = convert(r), convert(g), convert(b)
    return discord.Colour.from_rgb(r,g,b)

def random_spec(spec):
    hue = lambda start, end: random.uniform(start, end)
    x = random.random
    if spec == "red-yellow":
        h = hue(0, 1/6)
    elif spec == "yellow-green":
        h = hue(1/6, 1/3)
    elif spec == "green-cyan":
        h = hue(1/3, 1/2)
    elif spec == "cyan-blue":
        h = hue(1/2, 2/3)
    elif spec == "blue-magenta":
        h = hue(2/3, 5/6)
    elif spec == "magenta-red":
        h = hue(5/6, 1)
    elif re.search("^#[a-fA-F0-9]{6}-#[a-fA-F0-9]{6}$", spec):
        convert = lambda x: (int(x[0:2], 16), int(x[2:4], 16), int(x[4:6], 16))
        r1,g1,b1 = convert(spec[1:7])
        r2,g2,b2 = convert(spec[9:15])
        x = lambda a, b: random.randint(min(a, b), max(a, b))
        r,g,b = x(r1, r2), x(g1, g2), x(b1, b2)
        return discord.Colour.from_rgb(r,g,b)
    elif re.search("^{0}\s*,\s*{0}\s*,\s*{0}-{0}\s*,\s*{0}\s*,\s*{0}$".format("((1(\.0?)?)|(0(\.[0-9]*)?))"), spec):
        color1, color2 = spec.split("-")
        h1,l1,s1 = map(float, re.split("\s*,\s*", color1))
        h2,l2,s2 = map(float, re.split("\s*,\s*", color2))
        x = lambda a, b: random.uniform(min(a, b), max(a, b))
        h,l,s = x(h1,h2), x(l1,l2), x(l1,l2)
        return hls_to_Colour(h,l,s)
    else:
        return
    return hls_to_Colour(h, x(), x())

def check_if_not_following(ctx):
    author = ctx.author
    leon_role = discord.utils.find(lambda role: role.name.startswith("leon "), author.roles)
    if leon_role is None or author.name in leon_role.name:
        return True
    return False

def check_if_following(ctx):
    author = ctx.author
    leon_role = discord.utils.find(lambda role: role.name.startswith("leon "), author.roles)
    if leon_role:
        if author.name not in leon_role.name:
            return True
    return False

class LeonCog:
    def __init__(self, bot):
        self.bot = bot
        self.data = {}
        
    async def on_ready(self):
        print('Logged in as')
        print(self.bot.user.name)
        print(self.bot.user.id)
        print('------')
        self.data = await self.bot.load_data()
        
    @commands.command(name='help')
    async def _help(self, ctx):
        embed = discord.Embed(title="LeonBot", colour=random_color(), description="A list of LeonBot Commands")
        embed.set_thumbnail(url=ctx.guild.icon_url)
        embed.add_field(name="help", value="Shows this message.")
        embed.add_field(name="rand [spectrum]", value="Get either a completely random color or that within declared hue spectrum")
        embed.add_field(name="rainbow [spectrum]", value="Enable random color every post. You can also declare a specific hue spectrum!")
        embed.add_field(name="rainbow off", value="Turn off the rainbow")
        embed.add_field(name="spec", value="Show available hue spectrums", inline=False)
        embed.add_field(name="get [member]", value="Get your or another member's colour")
        embed.add_field(name="camouflage (member)", value="Get someone else's color!", inline=False)
        embed.add_field(name="follow (member)", value="Follow somoeone's color. While you're following someone, you cannot invoke any commands except follow and unfollow.")
        embed.add_field(name="unfollow", value="Stop following another member")
        await ctx.send(content=None, embed=embed)
        
    @commands.command()
    async def spec(self, ctx):
        await ctx.send(spectrums)
        
    @commands.command()
    async def get(self, ctx, other_member=None):
        guild = ctx.guild
        if other_member is None:
            author = ctx.author
            role = discord.utils.get(author.roles, name="leon " + author.name)
            color = role.color
            await ctx.send("Your color is: `{}`." .format(str(color)))
        else:
            member_found = discord.utils.get(guild.members, name=other_member)
            if member_found is None:
                await ctx.send("{} not found!" .format(other_member))
                return
            members_role = discord.utils.get(member_found.roles, name="leon " + other_member)
            if members_role:
                await ctx.send("{}'s color is `{}`." .format(other_member, str(members_role.color)))
            if members_role is None:
                await ctx.send("{} doesn't have a valid role!" .format(other_member))

    @commands.command()
    @commands.check(check_if_not_following)
    async def rand(self, ctx, spec=None):
        guild = ctx.guild
        author = ctx.author
        role_name = "leon " + ctx.author.name
        has_role = discord.utils.get(author.roles, name=role_name)
        if spec is None and not has_role:
            role = await guild.create_role(name=role_name, color=random_color())
            await author.add_roles(role)
        elif spec and not has_role:
            role = await guild.create_role(name=role_name, color=random_spec(spec))
            await author.add_roles(role)
        elif spec is None and has_role:
            await has_role.edit(color=random_color())
        elif spec and has_role:
            await has_role.edit(color=random_spec(spec))
            
    @commands.group(invoke_without_command=True)
    @commands.check(check_if_not_following)
    async def rainbow(self, ctx, spec=None):
        if ctx.invoked_subcommand is None:
            guild = ctx.guild
            guild.id = str(guild.id)
            author = ctx.author
            if spec is None:
                self.data[guild.id][author.name] = {"rainbow":True, "spec":None}
            else: 
                self.data[guild.id][author.name] = {"rainbow":True, "spec":spec}
            
    @rainbow.command()
    async def off(self, ctx, description="Turn the rainbow off, retaining your last color."):
        guild = ctx.guild
        guild.id = str(guild.id)
        author = ctx.author
        self.data[guild.id][author.name] = {"rainbow":False, "spec":None}
        
    @commands.command(name='set')
    @commands.check(check_if_not_following)
    async def setcolor(self, ctx, color, description="Set your own color."):
        color = color[1:]
        color = int(color, 16)
        color = discord.Colour(color)
        guild = ctx.guild
        author = ctx.author
        role_name = "leon " + author.name
        has_role = discord.utils.get(author.roles, name=role_name)
        if has_role:
            await has_role.edit(color=color)
        else:
            role = await guild.create_role(name=role_name, color=color)
            await author.add_roles(role)
        
    @commands.command()
    @commands.check(check_if_not_following)
    async def camouflage(self, ctx, other_member):
        guild = ctx.guild
        member_found = discord.utils.get(guild.members, name=other_member)
        if member_found is None:
            await ctx.send("{} not found!" .format(other_member))
        members_role = discord.utils.get(member_found.roles, name="leon " + other_member)
        if members_role:
            color = members_role.colour
            await ctx.invoke(self.setcolor, str(color))
        elif members_role is None:
            await ctx.send("{} doesn't have a valid role!" .format(other_member))
            
    @commands.command()
    async def follow(self, ctx, other_member):
        author = ctx.author
        guild = ctx.guild
        member_found = discord.utils.get(guild.members, name=other_member)
        if member_found is None:
            await ctx.send("{} not found!" .format(other_member))
            return
        members_role = discord.utils.get(member_found.roles, name = "leon " + other_member)
        print(members_role)
        if members_role:
            print(author)
            await author.add_roles(members_role)
            role_name = "leon " + author.name
            has_role = discord.utils.get(author.roles, name=role_name)
            if has_role:
                await has_role.delete()
            is_following = discord.utils.find(lambda role: role.name.startswith("leon "), author.roles)
            if is_following:
                await ctx.author.remove_roles(is_following)
        elif members_role is None:
            await ctx.send("{} doesn't have a valid role!" .format(other_member))
            
    @commands.command()
    @commands.check(check_if_following)
    async def unfollow(self, ctx):
        author = ctx.author
        role = discord.utils.find(lambda role: role.name.startswith("leon "), author.roles)
        await author.remove_roles(role)
            
    async def on_message(self, message):
        ctx = await self.bot.get_context(message)
        if ctx.valid:
            #await self.bot.process_commands(message)
            return
        author = message.author
        guild = author.guild
        guild.id = str(guild.id)
        if author.name not in self.data[guild.id]:
            return
        rainbow = self.data[guild.id][author.name]["rainbow"]
        not_following = check_if_not_following(ctx)
        if rainbow and not_following:
            spec = self.data[guild.id][author.name]["spec"]
            if spec:
                await ctx.invoke(self.rand, spec=spec)
            else: 
                await ctx.invoke(self.rand)
        
    @commands.command()
    async def _save(self, ctx):
        self.bot.save_data()
                
    async def on_command_error(self, ctx, error):
        print(type(error))
        inv = ctx.invoked_with
        if inv == "rand" or inv == "rainbow" or inv == "rainbow off" or \
        inv == "setcolor" or inv == "camouflage":
            if isinstance(error, type(commands.errors.CheckFailure)):
                await ctx.send("Error! You're following someone!")
        elif inv == "unfollow":
            if isinstance(error, type(commands.errors.CheckFailure)):
                await ctx.send("Error! You aren't following anyone yet!")
        else:
            print(error)
            
def setup(bot):
    bot.add_cog(LeonCog(bot))
