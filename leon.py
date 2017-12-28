# -*- coding: utf-8 -*-
"""
Created on Thu Dec 21 12:59:05 2017

@author: Lenovo
"""
import discord
import random
import asyncio
import os

client = discord.Client()

help_info = """`!leon` - activate/deactivate random colours every post
`!leon keep` - keep your current colour
`!leon set [#000000]` - set your colour to #000000
`!leon random` - set your colour to random one
`!leon camouflage [member]` - set your colour to that of the other member
`!leon get` - get your colour"""

@client.event
async def on_ready():
    print('Logged in as')
    print(client.user.name)
    print(client.user.id)
    print('------')

def randomColor():
    r = lambda: random.randint(0,255)
    color = '%02X%02X%02X' % (r(),r(),r())
    color = color.lower()
    return discord.Colour(int(color, 16))

async def getRole(author, role_start):
    roles = author.roles
    for role in roles:
        role_name = role.name
        if role_name.startswith(role_start):
            return role
    return False

async def isColor(server, color):
    for role in server.roles:
        role_name = role.name
        if role_name.startswith("p_leon"):
            if role.color == color:
                return role
    return False

async def leon(author, call=None):
    server = author.server
    is_author = await getRole(author, "leon")
    if is_author != False and call != None:
        await client.delete_role(server, is_author)
    elif is_author == False and call != None:
        role_name = author.name
        role_name = "leon " + role_name
        new_role = await client.create_role(server, name=role_name, colour=randomColor())
        await client.add_roles(author, new_role)
        check = await getRole(author, "p_leon")
        if check != None:
            try:
                await client.remove_roles(author, check)
            except:
                pass
    else:
        if is_author != False:
            await client.edit_role(server, role=is_author, colour=randomColor())

async def clean(server):
    roles = server.roles
    members = server.members
    unused = []
    counter = 0
    for role in roles:
        used = False
        for member in members:
            if role in member.roles:
                used = True
                break
        if used == False:
            unused.append(role)
    for role in unused:
        try:
            await client.delete_role(server, role)
            counter += 1
        except:
            pass
    return print("{} roles deleted.".format(counter))

async def persistent_leon(author):
    server = author.server
    role = await getRole(author, "leon")
    role_color = role.color
    color_str = str(role_color)
    role_name = "p_leon " + color_str
    check = discord.utils.get(server.roles, name=role_name)
    if check != None:
        await client.add_roles(author, check)
    else:
        new_role = await client.create_role(server, name=role_name, colour=role_color)
        await client.add_roles(author, new_role)
    await client.delete_role(server, role)

async def new_persistent_leon(author, color):
    server = author.server
    check_leon = await getRole(author, "leon")
    if check_leon != False:
        await client.delete_role(server, check_leon)
    check_p_leon = await getRole(author, "p_leon")
    if check_p_leon != None:
        try:
            await client.remove_roles(author, check_p_leon)
        except:
            pass
    check = await isColor(server, color)
    if check != False:
        await client.add_roles(author, check)
    else:
        role_name = "p_leon " + str(color)
        new_role = await client.create_role(server, name=role_name, colour=color)
        await client.add_roles(author, new_role)

async def clean_roles():
    await client.wait_until_ready()
    server = client.get_server(id="183926953365995520")
    await asyncio.sleep(5)
    while not client.is_closed:
        print("Cleaning roles...")
        await clean(server)
        await asyncio.sleep(600)

@client.event
async def on_message(message):
    author = message.author
    server = author.server
    if author == client.user:
        return
    elif message.content.startswith("!leon help"):
        await client.send_message(message.channel, help_info)
    elif message.content == "!leon":
        await leon(author, call=True)
    elif message.content == "!leon keep":
        await persistent_leon(author)
    elif message.content == "!leon clean":
        await clean(server)
    elif message.content == "!leon set #000000":
        await client.send_message(message.channel, "Black is not a colour!")
    elif message.content.startswith("!leon set"):
        color_hex = message.content
        color_hex = color_hex.split()
        color_hex = color_hex[-1]
        color_hex = color_hex[1:]
        new_color = discord.Colour(int(color_hex, 16))
        await new_persistent_leon(author, new_color)
    elif message.content.startswith("!leon random"):
        color = randomColor()
        await new_persistent_leon(author, color)
    elif message.content.startswith("!leon get"):
        await client.send_message(message.channel, content="Your colour is: {}" .format(author.color))
    elif message.content.startswith("!leon camouflage"):
        other_member = message.content
        other_member = other_member.split()
        other_member = other_member[-1]
        member = discord.utils.find(lambda m: m.name == '{}'.format(other_member), server.members)
        try:
            color = member.color
            await new_persistent_leon(author, color)
        except:
            print(member)
    else:
        await leon(author)

client.loop.create_task(clean_roles())
token = os.environ.get('TOKEN')
client.run(token)
