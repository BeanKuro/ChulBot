#Discord Music Bot
#Made by KuroBean

import discord 
from discord.ext import commands
import yt_dlp as youtube_dl
from dotenv import load_dotenv
import os
import asyncio

load_dotenv('DISCORD_BOT_TOKEN.env')
print("DISCORD_BOT_TOKEN:", os.getenv('DISCORD_BOT_TOKEN'))

intents = discord.Intents.default()
intents.message_content = True
client = commands.Bot(command_prefix='!', intents=intents, help_command=None)

# 큐를 위한 리스트 초기화
queue = []  # [ (제목, URL), ... ]

FFMPEG_OPTIONS = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', 'options': '-vn'}

@client.event
async def on_ready():
    print(f'Logged in as {client.user}')

@client.event # 봇 상태 표시 기능 (v1.0.3 추가)
async def on_ready():
  
  await client.change_presence(status=discord.Status.online) #온라인
  #await client.change_presence(status=discord.Status.idle) #자리비움
  #await client.change_presence(status=discord.Status.dnd) #다른용무
  #await client.change_presence(status=discord.Status.offline) #오프라인

  await client.change_presence(activity=discord.Game(name="승탱이 때리기 "))
  #await client.change_presence(activity=discord.Streaming(name="스트림 방송중", url='링크'))
  #await client.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name="노래 듣는중"))
  #await client.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="영상 시청중"))
  
  print("봇 이름:",client.user.name,"봇 아이디:",client.user.id,"봇 버전:",discord.__version__)


@client.command()  # !help 명령어 기능 (v1.0.3 추가)
async def help(ctx):
    help_message = (
        "**사용 가능한 명령어:**\n"
        "!play [URL] - 음악 재생\n"
        "!pause - 음악 일시정지\n"
        "!resume - 음악 일시정지 해제\n"
        "!skip - 다음 곡으로 건너뛰기\n"
        "!list - 예약된 곡 목록 보기\n"
        "!stop - 음악 중지 및 리스트 삭제\n"
        "!leave - 봇 내보내기\n"
        "!join - 봇을 보이스 채널에 초대하기"
    )
    await ctx.send(help_message)

@client.event  # 봇 명령어 표시 기능
async def on_message(message):
    if message.author == client.user:
        return

    # on_message에서도 다른 명령어 처리를 위해 process_commands 호출
    await client.process_commands(message)


#v1.0.2 추가(자동퇴장기능)
async def auto_disconnect_timer(ctx, timeout=300):  # 300초(5분) 후에 퇴장
    await asyncio.sleep(timeout)  # 타이머 설정
    if ctx.voice_client and not ctx.voice_client.is_playing():
        await ctx.voice_client.disconnect()
        await ctx.send("일정 시간 동안 활동이 없어 보이스 채널에서 퇴장할게요.")
        

@client.command()
async def join(ctx): #v1.0.2 추가(자동퇴장기능)
    if not ctx.author.voice:
        await ctx.send("당신은 현재 보이스 채널에 없어요!")
        return
    channel = ctx.author.voice.channel
    await channel.connect()
    # 자동 퇴장을 위한 타이머 시작
    asyncio.create_task(auto_disconnect_timer(ctx))


@client.command()
async def leave(ctx):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
    else:
        await ctx.send("저는 보이스 채널에 없어요!")

def play_next(ctx):
    voice_channel = ctx.voice_client
    if queue:  # 큐에 곡이 있을 경우
        next_title, next_url = queue.pop(0)  # 큐에서 첫 번째 곡 가져오고 제거
        voice_channel.play(discord.FFmpegPCMAudio(executable="ffmpeg", source=next_url, **FFMPEG_OPTIONS), after=lambda e: play_next(ctx))
        # 다음 곡이 끝나면 play_next 호출
        asyncio.run_coroutine_threadsafe(ctx.send(f"**현재 재생 중:**\n{next_title}"), client.loop)
    else:
        asyncio.run_coroutine_threadsafe(ctx.send("리스트에 저장된 곡이 없습니다."), client.loop)

@client.command()
async def play(ctx, url):
    try:
        YDL_OPTIONS = {'format': 'bestaudio', 'noplaylist': 'True'}
        
        voice_channel = ctx.voice_client
        
        with youtube_dl.YoutubeDL(YDL_OPTIONS) as ydl:
            info = ydl.extract_info(url, download=False)
            title = info.get('title', '제목을 찾을 수 없습니다')
            url2 = info['url']
            
            # 큐에 제목과 URL 추가
            queue.append((title, url2))

            # 현재 곡이 재생 중이지 않으면 첫 번째 곡 재생
            if not voice_channel.is_playing():
                next_title, next_url = queue.pop(0)  # 첫 번째 곡 가져오고 제거
                voice_channel.play(discord.FFmpegPCMAudio(executable="ffmpeg", source=next_url, **FFMPEG_OPTIONS), after=lambda e: play_next(ctx))
                await ctx.send(f"**현재 곡:**\n{next_title}")
            else:
                await ctx.send(f"곡이 리스트에 저장되었습니다.\n {title}")
    except Exception as e:
        await ctx.send(f"An error occurred: {str(e)}")

@client.command()
async def pause(ctx):
    voice_channel = ctx.voice_client
    if voice_channel.is_playing():
        voice_channel.pause()

@client.command()
async def resume(ctx):
    voice_channel = ctx.voice_client
    if voice_channel.is_paused():
        voice_channel.resume()

@client.command()
async def stop(ctx):
    voice_channel = ctx.voice_client
    if voice_channel.is_playing():
        voice_channel.stop()
        queue.clear()  # 큐의 모든 노래 삭제
        await ctx.send("곡을 멈추고 리스트를 전체 삭제합니다.")
    else:
        await ctx.send("현재 음악 재생 중이 아닙니다.")

@client.command()
async def list(ctx):
    if not queue:
        await ctx.send("리스트에 저장된 노래가 없습니다.")
    else:
        message = "**곡 리스트:**\n"
        for i, (title, _) in enumerate(queue):
            message += f"{i+1}. {title}\n"
        await ctx.send(message)

@client.command()
async def skip(ctx):
    voice_channel = ctx.voice_client
    if not voice_channel or not voice_channel.is_connected():
        await ctx.send("저는 보이스 채널에 없어요!")
        return
    if not queue:
        await ctx.send("스킵 할 곡이 없습니다!")
        return

    voice_channel.stop()
    
    if queue:  # 큐에 다음 곡이 있을 경우
        next_title, next_url = queue.pop(0)  # 큐에서 첫 번째 노래 가져오고 제거
        voice_channel.play(discord.FFmpegPCMAudio(executable="ffmpeg", source=next_url, **FFMPEG_OPTIONS))
        await ctx.send(f"**스킵! 현재 곡:**\n{next_title}")
    else:
        await ctx.send("리스트에 저장된 노래가 없습니다.")

@client.event #v1.0.2 추가(자동퇴장기능 - 모든 유저 퇴장 시 봇 퇴장)
async def on_voice_state_update(member, before, after):
    voice_client = member.guild.voice_client

    # 사용자가 음성 채널을 나갔을 때
    if before.channel is not None and len(before.channel.members) == 1 and voice_client and voice_client.channel == before.channel:
        # 채널에 봇만 남았을 때 퇴장
        await voice_client.disconnect()

        # 봇이 속한 텍스트 채널로 메시지 보내기
        text_channel = member.guild.text_channels[0]  # 첫 번째 텍스트 채널로 메시지 보냄 (필요시 변경 가능)

        # 음성 채널에 사용자가 들어왔을 때 별도의 동작을 추가할 수도 있음



client.run(os.getenv('DISCORD_BOT_TOKEN'))
