import discord
import re
import random
import colorsys
import operator
from datetime import datetime, tzinfo, timedelta


def is_reserved(hex_code, reserved):
    def to_rgb(hex_str):
        hex_str = hex_str.lstrip('#')
        return tuple(int(hex_str[i:i+2], 16) for i in (0, 2, 4))
    reserved_rgbs = [to_rgb(r) for r in reserved]
    rgb = to_rgb(hex_code)
    for r in reserved_rgbs:
        d = ((rgb[0]-r[0])**2 + (rgb[1]-r[1])**2 + (rgb[2]-r[2])**2)**0.5
        print(d)
        if d <= 60:
            return True


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
    elif re.search("^\s*#[a-fA-F0-9]{6}\s*-\s*#[a-fA-F0-9]{6}\s*$", spec):
        convert = lambda x: (int(x[0:2], 16), int(x[2:4], 16), int(x[4:6], 16))
        r1,g1,b1 = convert(spec[1:7])
        r2,g2,b2 = convert(spec[9:15])
        x = lambda a, b: random.randint(min(a, b), max(a, b))
        r,g,b = x(r1, r2), x(g1, g2), x(b1, b2)
        return discord.Colour.from_rgb(r,g,b)
    elif re.search("^\s*{0}\s*,\s*{0}\s*,\s*{0}\s*-\s*{0}\s*,\s*{0}\s*,\s*{0}\s*$".format("0*((1(\.0?)?)|(0(\.[0-9]*)?)|(\.[0-9]+))"), spec):
        color1, color2 = spec.split("-")
        h1,l1,s1 = map(float, re.split("\s*,\s*", color1))
        h2,l2,s2 = map(float, re.split("\s*,\s*", color2))
        x = lambda a, b: random.uniform(min(a, b), max(a, b))
        h,l,s = x(h1,h2), x(l1,l2), x(l1,l2)
        return hls_to_Colour(h,l,s)
    else:
        return
    return hls_to_Colour(h, x(), x())


def format_help(commands, color):
    pages = []
    commands = commands.splitlines()
    if len(commands) % 5 is 0:
        no_pages = len(commands)/5
    else:
        no_pages = (len(commands)//5)+1
    no_pages = int(no_pages)
    p_count = 1
    c_count = 0
    for command in commands:
        if c_count is 0:
            embed = discord.Embed(colour=color)
            footer = "Page {}/{} ({} commands)".format(p_count, no_pages, str(len(commands)))
            embed.set_footer(text=footer)
        com, des = command.split(":")
        des = des[1:]
        embed.add_field(name=com, value=des, inline=False)
        if c_count is 4 or command == commands[-1]:
            c_count = 0
            p_count += 1
            pages.append(embed)
        else:
            c_count += 1
    return pages, no_pages


class GMT1(tzinfo):
    def utcoffset(self, dt):
        return timedelta(hours=1) + self.dst(dt)

    def dst(self, dt):
        d = datetime(dt.year, 4, 1)
        self.dston = d - timedelta(days=d.weekday() + 1)
        d = datetime(dt.year, 11, 1)
        self.dstoff = d - timedelta(days=d.weekday() + 1)
        if self.dston <=  dt.replace(tzinfo=None) < self.dstoff:
            return timedelta(hours=1)
        else:
            return timedelta(0)

    def tzname(self,dt):
        return "GMT +1"


def super_sort(l):
    sort_alpha = sorted(l, key=operator.itemgetter(0))
    return sorted(sort_alpha, key=operator.itemgetter(1), reverse=True)


class InvalidSyntax(Exception):
    pass


def int_to_uni(i):
    if i == "10":
        return "\U0001f51f"
    else:
        return "{}\u20e3".format(i)


def uni_to_int(u):
    string = repr(u.encode('utf-8'))
    fp, sp = string.split("'", 1)
    if sp[0].isnumeric():
        return int(sp[0])
    else:
        return 10

