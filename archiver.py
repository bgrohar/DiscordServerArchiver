import emoji
import os
import re
import discord
import random
import asyncio
import time
import threading
from queue import Queue
from random import randint
from os import listdir
from os.path import isfile, join
from datetime import datetime
from dotenv import load_dotenv
from discord import Game
from discord.utils import get
from discord.ext import commands, tasks



# Initialization
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
GUILD = os.getenv('DISCORD_GUILD')

intents = discord.Intents().all()
client = discord.Client(intents=intents)
bot = commands.Bot(command_prefix='!',intents=intents)

time_start = ""

log_file_path = "path to log.ini goes here"
images_path = "path to attachments folder goes here"
msg_log_file_path = os.path.dirname(__file__)+"\\logs\\messages.log"

attachment_formats = [
    "jpg",
    "jpeg",
    "png",
    "gif",
    "mp3",
    "mp4",
    "avi",
    "webm"
]

#@bot.command(name='ar', help=": Archives server history", description='It really does.')
async def writeMessages(ctx):
    # Handle pinned messages - OK
    # Resolve users by id - OK
    # Resolve avatars by user - OK
    # Resolve custom emojis - OK
    # Resolve reaction count - OK
    # Resolve user mentions
    # Give random id-s to attachments
    
    global log_file_path

    # Lock bot here
    
    
    channel = ctx.channel
    msg = await ctx.send(content='Working...')
    
    starting_time = time.time()
    
    # How many messages to save, including the command message that invoked this
    m_count = 65536
    actual_count = 0

    messages = await channel.history(limit=m_count).flatten()
    id = 0  # Set starting id for attachment renaming 
    
    if len(messages) < m_count:
        m_count = len(messages)

    
    # Count messages with attachments
    at_count = 0
    for m in messages:
        if len(m.attachments) > 0:
            at_count += 1
    print("at_count: ",at_count)
    
    
    # API rate limit countermeasure for performance metric (limit = 5 anything / 5 s / server )
    last_update = time.time()
    count_since_update = 0
    at_weight = 10
    y = (m_count - at_count) + at_count*at_weight
    at_current_count = 0

    # Create file if not present
    if not isfile(log_file_path):
        f=open(log_file_path, "w", encoding="utf-8")
        f.flush()
        f.close()
    if isfile(log_file_path):
        f=open(log_file_path, "a+", encoding="utf-8")
        m_current = 0
        for i in reversed(messages):    # Iterate in reverse (older to newer)
            if len(i.mentions) > 0:
                for me in i.mentions:
                    # Resolve users from id
                    if "<@!" in str(i.content):
                        user_id = str(i.content).split("<@!",1)[1]
                        user_id = user_id.split(">",1)[0]
                        i.content = str(i.content).replace("!"+user_id,str(await bot.fetch_user(user_id)).split("#",1)[0])  
            if len(i.attachments) > 0:  # Check if contains attachments
                for at in i.attachments:
                    # Increment attachment count
                    at_current_count += 1
                    frm = at.filename.split('.',1)[1]       
                    if frm and frm in attachment_formats: # Check if valid format
                        print(await at.save(str(os.path.dirname(__file__)+"\\logs\\images\\"+str(id)+"."+frm))) # Prints number of bytes written
                        pin = ""
                        if len(i.reactions) > 0:
                            rez=""
                            for m in i.reactions:
                                #rez+=str(m)+","
                                rez+=str(m)+"§"+str(m.count)+","
                            f_content=str(id)+"."+frm
                            if i.pinned:
                                pin = "PIN"
                            print(f_content)
                            f.write("[{}]|[{}]|[{}]|<{}>|(({}))\n".format(pin,i.author.name,str(i.created_at).split('.')[0], f_content, rez))
                        else:
                            f_content=str(id)+"."+frm
                            f.write("[{}]|[{}]|[{}]|<{}>\n".format(pin,i.author.name,str(i.created_at).split('.')[0], f_content))
                        actual_count += 1
                        id += 1
                    else:
                        f.write("uh oh!\n")
            else: # Process regular text
                f_content = r"{}".format(i.content)
                pin = ""
                if i.pinned:
                    pin = "PIN"
                if len(i.reactions) > 0:
                    rez=""
                    for m in i.reactions:
                        #rez+=str(m)+","
                        rez+=str(m)+"§"+str(m.count)+","
                    f.write("[{}]|[{}]|[{}]|{}|(({}))\n".format(pin, i.author.name, str(i.created_at).split('.')[0], f_content, rez))
                else:
                    f.write("[{}]|[{}]|[{}]|{}\n".format(pin,i.author.name,str(i.created_at).split('.')[0], f_content))
                actual_count += 1
                f.flush()
                m_current += 1
                count_since_update += 1
                #if (count_since_update > 5) and ((time.time() - last_update) > 5):
                if (time.time() - last_update) > 5:
                    x = (actual_count - at_current_count) + at_current_count*at_weight
                    display_done = int(round((x/y)*100,2)/2) # "y" is used here
                    print("Display_done: ",display_done)
                    display_string = "["+"█"*display_done+"..."*(50-display_done)+">]"
                    await msg.edit(content="{} ({}/{}) **{}% done...**".format(display_string,str(actual_count),str(m_count),str(round((x/y)*100,2))))
                    last_update = time.time()
                    count_since_update = 0
                
        f.close()
    await msg.edit(content="Done!")
    await ctx.send(content="Archived {} messages and {} attachments in {} s.".format(actual_count,at_count,str(time.time()-starting_time).split('.')[0]))
 
    # Unlock bot here
    
    print("---------Done archiving---------")

# Archive function with partial history fetching and reverse reconstruction
#@bot.command(name='tar', help=": Like 'ar', but reports more often") 
async def TwriteMessages(ctx):
    
    global log_file_path

    starting_time = time.time()
    last_update = time.time()
    
    rst = await ctx.send("Fetching...")
    
    # Lock bot here
    
    channel = ctx.channel
    
    # How many messages to save, including the command message that invoked this
    m_count = 65536
    ms_limit = m_count

    actual_count = 0

    divisor = 1 # Determine this value below
    fract = ms_limit
    remainder = 0
    
    if ms_limit > 200:
        divisor = ms_limit // 100
        fract = 100 
        remainder = (ms_limit - fract) % fract  
    
    print("divisor:",str(divisor))
    print("fract:",str(fract))
    print("remainder:",str(remainder))
    
    date_treshold = ""
    print("ms_limit:",ms_limit)
    combined_cache = []
    final_cache = []
    
    # Get ending first > OK <
    cache_end = list(reversed(await channel.history(limit=fract).flatten()))
    date_treshold = cache_end[0].created_at

    # Get others in reversed order > OK <
    for i in range(0,divisor-1):
        combined_cache.append(list(reversed(await channel.history(limit=fract, before=date_treshold).flatten())))
        date_treshold = combined_cache[len(combined_cache)-1][0].created_at
        if((time.time() - last_update) > 2):
            await rst.edit(content="Loading.....{}%".format(str(round((i+1/divisor)*1.2658,2)))) # only goes 0-79% otherwise
            last_update = time.time()
        print("Working...",str(round((i+1/divisor)*1.2658,2)))

    # Get beggining last (remainder)
    cache_start = []
    if remainder > 0:
        cache_start = list(reversed(await channel.history(limit=remainder, before=date_treshold).flatten()))
    
    final_cache = final_cache + cache_start # Add beggining
    print("Added {} elements to final from cache_start".format(str(len(cache_start))))
    
    
    idx = len(combined_cache)-1
    for l in list(reversed(combined_cache)):
        final_cache = final_cache + l # Add everything in between

    final_cache = final_cache + cache_end # Add ending
    print("Added {} elements to final from cache_end".format(str(len(cache_end))))

    xt = divisor + 1
    if remainder > 0:
        xt+=1
        
    dur = str(time.time()-starting_time).split('.')[0]
    rs = "- {} - Completed in {} s.".format(str(divisor),dur)
    print("tm fired :: "+rs)
    await rst.edit(content=rs, delete_after=15)
    messages = combined_cache
    
    
    id = 0  # Set starting id for attachment renaming 
    msg = await ctx.send(content='Working...')
    
    
    if len(messages) < m_count:
        m_count = len(messages)

    
    # Count messages with attachments
    at_count = 0
    for m in messages:
        if len(m.attachments) > 0:
            at_count += 1
    print("at_count: ",at_count)
    
    
    # API rate limit countermeasure for performance metric (limit = 5 anything / 5 s / server )
    last_update = time.time()
    count_since_update = 0
    at_weight = 10
    y = (m_count - at_count) + at_count*at_weight
    at_current_count = 0

    # Create file if not present
    if not isfile(log_file_path):
        f=open(log_file_path, "w", encoding="utf-8")
        f.flush()
        f.close()
    if isfile(log_file_path):
        f=open(log_file_path, "a+", encoding="utf-8")
        m_current = 0
        for i in reversed(messages):    # Iterate in reverse (older to newer)
            if len(i.mentions) > 0:
                for me in i.mentions:
                    # Resolve users from id
                    if "<@!" in str(i.content):
                        user_id = str(i.content).split("<@!",1)[1]
                        user_id = user_id.split(">",1)[0]
                        i.content = str(i.content).replace("!"+user_id,str(await bot.fetch_user(user_id)).split("#",1)[0])  
            if len(i.attachments) > 0:  # Check if contains attachments
                for at in i.attachments:
                    # Increment attachment count
                    at_current_count += 1
                    frm = at.filename.split('.',1)[1]       
                    if frm and frm in attachment_formats: # Check if valid format
                        print(await at.save(str(images_path+str(id)+"."+frm))) # Prints number of bytes written
                        pin = ""
                        if len(i.reactions) > 0:
                            rez=""
                            for m in i.reactions:
                                rez+=str(m)+"§"+str(m.count)+","
                            f_content=str(id)+"."+frm
                            if i.pinned:
                                pin = "PIN"
                            print(f_content)
                            f.write("[{}]|[{}]|[{}]|<{}>|(({}))\n".format(pin,i.author.name,str(i.created_at).split('.')[0], f_content, rez))
                        else:
                            f_content=str(id)+"."+frm
                            f.write("[{}]|[{}]|[{}]|<{}>\n".format(pin,i.author.name,str(i.created_at).split('.')[0], f_content))
                        actual_count += 1
                        id += 1
                    else:
                        f.write("Uh oh - Invalid attachment type !\n")
            else: # Process regular text
                f_content = r"{}".format(i.content)
                pin = ""
                if i.pinned:
                    pin = "PIN"
                if len(i.reactions) > 0:
                    rez=""
                    for m in i.reactions:
                        #rez+=str(m)+","
                        rez+=str(m)+"§"+str(m.count)+","
                    f.write("[{}]|[{}]|[{}]|{}|(({}))\n".format(pin, i.author.name, str(i.created_at).split('.')[0], f_content, rez))
                else:
                    f.write("[{}]|[{}]|[{}]|{}\n".format(pin,i.author.name,str(i.created_at).split('.')[0], f_content))
                actual_count += 1
                f.flush()
                m_current += 1
                count_since_update += 1
                #if (count_since_update > 5) and ((time.time() - last_update) > 5):
                if (time.time() - last_update) > 5:
                    x = (actual_count - at_current_count) + at_current_count*at_weight
                    display_done = int(round((x/y)*100,2)/2)
                    print("Display_done: ",display_done)
                    display_string = "["+"█"*display_done+"..."*(50-display_done)+">]"
                    await msg.edit(content="{} ({}/{}) **{}% done...**".format(display_string,str(actual_count),str(m_count),str(round((x/y)*100,2))))
                    last_update = time.time()
                    count_since_update = 0
                
        f.close()
    await msg.edit(content="Done!")
    await ctx.send(content="Archived {} messages and {} attachments in {} s.".format(actual_count,at_count,str(time.time()-starting_time).split('.')[0]))

    # Unlock bot here
    
    print("---------Done archiving---------")


@bot.event
async def on_ready():
    print(discord.__version__)
    global time_start
    time_start = time.time()
    
    await bot.wait_until_ready()
    for g in bot.guilds:
        print("g: ",g)
    guild = discord.utils.get(bot.guilds, name=GUILD)
    print(
        f'{bot.user} is in guild:\n'
        f'{guild.name}(id: {guild.id})'
    )
    print('\n')
    members = '\n - '.join([member.name for member in guild.members])
    print(f'Members:\n - {members}')
    print('\n')


@bot.event
async def on_error(event, *args, **kwargs):
    with open('err.log', 'a') as f:
        if event == 'on_message':
            f.write(f'Unhandled message: {args[0]}\n')
        else:
            raise


@bot.event
async def on_message(message):
    await bot.process_commands(message)  #Commands aren't even processed without this
    
    if message.author == bot.user:
        return

bot.run(TOKEN)
