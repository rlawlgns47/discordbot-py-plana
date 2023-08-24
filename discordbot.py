from cmath import log
from distutils.sysconfig import PREFIX
import discord
from discord import Embed
from dotenv import load_dotenv
import os
load_dotenv()
import requests
from discord.ext import commands
from datetime import datetime, timedelta
import threading
import random
import time
from bs4 import BeautifulSoup
import asyncio
import pytz
 
PREFIX = os.environ['PREFIX']
TOKEN = os.environ['TOKEN']
OPENAI_API_KEY = os.environ['GPT']
app = commands.Bot(command_prefix='/',intents=discord.Intents.all())
message_counts = {}
time_frames = {}
red_cards = {}

admin_id = 888839822184153089
semiadmin_id = 1087589293750497300

# Time interval to keep data in memory (in seconds)
DATA_EXPIRATION_TIME = 3600

# 글자수 최대
threshold = 300

# 장문도배 경고문
WARNING_MESSAGES = ["長文の連投ですか？やめてください！",
                   "長文の連投が確認されました！",
                   "長文は連投として判断します！やめてください！"
                   ]

def get_osaka_weather():
    url = "https://weather.yahoo.co.jp/weather/jp/27/6200.html"
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')
    high_temp = soup.select_one('li.high em').text
    low_temp = soup.select_one('li.low em').text
    t1 = soup.select_one('tr.precip td:nth-child(2)').text
    t2 = soup.select_one('tr.precip td:nth-child(3)').text
    t3 = soup.select_one('tr.precip td:nth-child(4)').text
    t4 = soup.select_one('tr.precip td:nth-child(5)').text
    weather_icon = soup.select_one('p.pict img')
    weather_text = weather_icon['alt']
    img_tag = soup.select_one('p.pict img')
    image_url = img_tag['src']
    return high_temp, low_temp, t1, t2, t3, t4, weather_text, image_url
 

@app.event
async def on_ready():
    print('Done')
    await app.change_presence(status=discord.Status.online, activity=None)
    
    channel = app.get_channel(1032650685180813312)
    message_id = 1094422274607689759
    message = None
    async for msg in channel.history(limit=None):
        if msg.id == message_id:
            message = msg
            break
    if message is None:
        message = await channel.send("🇴 :OVERWATCH\n🇻 :VALORANT\n🇦 :APEX\n🇱 :League of Legends\n🇪 :Escape From Tarkov\n🅾️ :Other games")
        await message.add_reaction("🇴")
        await message.add_reaction("🇻")
        await message.add_reaction("🇦")
        await message.add_reaction("🇱")
        await message.add_reaction("🇪")
        await message.add_reaction("🅾️")

    while True:
        now = datetime.now(pytz.timezone("Asia/Tokyo"))
        if now.hour == 7 and now.minute == 0:
            high_temp, low_temp, t1, t2, t3, t4, weather_text, image_url  = get_osaka_weather()
            embed = discord.Embed(title="大阪基準で今日の天気をお知らせします", description=weather_text, color=0xFF00AA)
            embed.add_field(name="最高気温", value=f"{high_temp}℃", inline=True)
            embed.add_field(name="最低気温", value=f"{low_temp}℃", inline=True)
            embed.add_field(name="0~6時降水確率", value=t1, inline=True)
            embed.add_field(name="6~12時降水確率", value=t2, inline=True)
            embed.add_field(name="12-18時降水確率", value=t3, inline=True)
            embed.add_field(name="18-24時降水確率", value=t4, inline=True)
            embed.set_footer(text="おはようございます")
            embed.set_image(url=image_url)
            await app.get_channel(1087556634005479544).send(embed=embed)
        await asyncio.sleep(60) #1마다 체크

def is_spamming(author_id):
    now = datetime.now()
    time_frame = time_frames.get(author_id, now)
    message_count = message_counts.get(author_id, 0)
    
    # Set time frame for user to 2 seconds
    time_frames[author_id] = now + timedelta(seconds=2)
    
    # Reset message count and delete expired data if time frame has passed
    if now > time_frame:
        message_counts[author_id] = 0
        for key in list(time_frames.keys()):
            if now > time_frames[key] + timedelta(seconds=DATA_EXPIRATION_TIME):
                del time_frames[key]
                del message_counts[key]
                
        return False
    
    # Increase message count and check if spamming
    message_counts[author_id] = message_count + 1
    return message_count >= 3 # Change 5 to desired message count threshold

def decrease_red_cards():
    while True:
        for user_id in red_cards.copy():
            red_cards[user_id] -= 1
            if red_cards[user_id] == 0:
                del red_cards[user_id]
        time.sleep(60)

# 감소 쓰레드 시작
decrease_thread = threading.Thread(target=decrease_red_cards, daemon=True)
decrease_thread.start()

def add_red_card(user_id):
    red_cards[user_id] = red_cards.get(user_id, 0) + 1

@app.event
async def on_message(message):

    spam_messages = [
    f"{message.author.mention}さん、連投は禁止です!",
    f"{message.author.mention}さん、連投はやめてください！",
    f"{message.author.mention}さん、連投はダメです！",
    f"{message.author.mention}さん、チャットが早すぎます",
    f"{message.author.mention}さん、連投なんて！管理者に全部言いつけます！"
]
    message_length = len(message.content)

    if message.author == app.user:
        return
    
    target_channel_id = 1087556634005479544 # 번역 대상 채널의 ID를 입력해주세요.

    if message.content.startswith(app.command_prefix):
        # Process commands in a separate thread
        await app.loop.run_in_executor(None, app.process_commands, message)
        return
    
    # 메세지 길이가 최대 글자수 돌파하는지 체크
    if message_length > threshold:
        # 경고발사
        WARNING_MESSAGE = random.choice(WARNING_MESSAGES)
        await message.channel.send(WARNING_MESSAGE)

        add_red_card(message.author.id)

        if red_cards.get(message.author.id, 0) >= 2:
            guild = message.guild
            role_id = 1087892271703261316 # Replace with the role ID you want to give to the user
            role = guild.get_role(role_id)
            adrole = discord.utils.get(message.guild.roles, id=admin_id)
            sadrole = discord.utils.get(message.guild.roles, id=semiadmin_id)
            member = guild.get_member(message.author.id)
            await member.add_roles(role)
            await message.channel.send(f"{message.author.mention}, {role.name} 役割を与えました！ {adrole.mention},{sadrole.mention} 管理者がくるまでお待ちください！")
            
    if message.author == app.user:
        return
    text = message.content
    if text.startswith('プラナ '):
        user_input = text[4:]

        # 이전 대화 내용을 포함하여 대화 진행
        conversation_history.append({"role": "user", "content": user_input})

        bot_response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "MD studioディスコードチャンネルサポートAIプラナです"},
                {"role": "user", "content": user_input}
            ] + conversation_history,  # 이전 대화 내용 추가
            temperature=0.5
        )

        # 대화 내용 업데이트
        conversation_history.append({"role": "assistant", "content": bot_response['choices'][0]['message']['content']})
        
        #print(bot_response)
        bot_text = '\n'.join([choice['message']['content'] for choice in bot_response['choices']])
        await message.channel.send(f"{bot_text}")

        return
    
    # Check if user is spamming
    elif is_spamming(message.author.id):
        spam_message = random.choice(spam_messages)
        await message.channel.send(spam_message)
        message_counts[message.author.id] = 0 # Reset message count for user

        add_red_card(message.author.id)

        if red_cards.get(message.author.id, 0) >= 2:
            guild = message.guild
            role_id = 1087892271703261316 # Replace with the role ID you want to give to the user
            role = guild.get_role(role_id)
            adrole = discord.utils.get(message.guild.roles, id=admin_id)
            sadrole = discord.utils.get(message.guild.roles, id=semiadmin_id)
            member = guild.get_member(message.author.id)
            await member.add_roles(role)
            await message.channel.send(f"{message.author.mention}, {role.name} 役割を与えました！ {adrole.mention},{sadrole.mention} 管理者がくるまでお待ちください！")
            

    return

@app.event
async def on_member_join(member):
    channel = app.get_channel(1087554522378948609)
    await channel.send(f'{member.mention}さん 日本人ですか？初めまして！ruleチャンネルを読んでroleチャンネルで日本を選んでください！') # channel에 보내기

ROLES = {
    "🇴": 1087692814462242816,  
    "🇻": 1087691245868032010,
    "🇦": 1087692165242683392,  
    "🇱": 1087693182441099275,
    "🇪": 1087693438423666809,  # 이모지와 해당 역할 ID를 수정해주세요.
    "🅾️": 1087693693122773054,
}

# 이벤트 핸들러
@app.event
async def on_raw_reaction_add(payload):
    if payload.message_id == 1094422274607689759:  # 역할 부여를 받을 메시지 ID를 수정해주세요.
        guild = app.get_guild(payload.guild_id)
        member = guild.get_member(payload.user_id)
        if member.bot:
            return

        emoji = payload.emoji.name
        if emoji in ROLES:
            role_id = ROLES[emoji]
            role = guild.get_role(role_id)
            await member.add_roles(role)

@app.event
async def on_raw_reaction_remove(payload):
    if payload.message_id == 1094422274607689759:  # 역할 부여를 받을 메시지 ID를 수정해주세요.
        guild = app.get_guild(payload.guild_id)
        member = guild.get_member(payload.user_id)
        if member.bot:
            return

        emoji = payload.emoji.name
        if emoji in ROLES:
            role_id = ROLES[emoji]
            role = guild.get_role(role_id)
            await member.remove_roles(role)

        
try:
    app.run(TOKEN)
except discord.errors.LoginFailure as e:
    print("Improper token has been passed.")
