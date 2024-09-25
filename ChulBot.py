# Discord Music Bot  
# Made by KuroBean

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
current_song_title = None  # 현재 재생 중인 곡 제목 저장

FFMPEG_OPTIONS = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', 'options': '-vn'}

@client.event
async def on_ready():
    await client.change_presence(status=discord.Status.online)  # 온라인
    await client.change_presence(activity=discord.CustomActivity(name="도움말 == !help"))
    print("봇 이름:", client.user.name, "봇 아이디:", client.user.id, "봇 버전:", discord.__version__)

@client.command()  # !help 명령어 기능 (v1.0.3 추가)
async def help(ctx):
    help_message = (
        "**사용 가능한 명령어:**\n"
        "!join - 봇을 보이스 채널에 초대하기\n"
        "!play [URL] - 음악 재생\n"
        "!pause - 음악 일시정지\n"
        "!resume - 음악 일시정지 해제\n"
        "!skip - 다음 곡으로 건너뛰기\n"
        "!list - 예약된 곡 목록 보기\n"
        "!stop - 음악 중지 및 리스트 삭제\n"
        "!leave - 봇 내보내기"
    )
    await ctx.send(help_message)

@client.event  # 봇 명령어 표시 기능
async def on_message(message):
    if message.author == client.user:
        return
    await client.process_commands(message)

async def auto_disconnect_timer(ctx, timeout=300):  # 300초(5분) 후에 퇴장
    await asyncio.sleep(timeout)  # 타이머 설정
    if ctx.voice_client and not ctx.voice_client.is_playing():
        await ctx.voice_client.disconnect()
        await ctx.send("일정 시간 동안 활동이 없어 보이스 채널에서 퇴장할게요.")

@client.command()
async def join(ctx):  # v1.0.2 추가(자동퇴장기능)
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
    global current_song_title  # 전역 변수 사용
    voice_channel = ctx.voice_client
    if queue and not voice_channel.is_playing():  # 곡이 남아있고 현재 곡이 재생 중이지 않을 때만
        next_title, next_url = queue.pop(0)  # 큐에서 다음 곡을 가져와 재생
        current_song_title = next_title  # 현재 재생 중인 곡 제목 업데이트
        voice_channel.play(discord.FFmpegPCMAudio(executable="C:\\ffmpeg\\bin\\ffmpeg.exe", source=next_url, **FFMPEG_OPTIONS), after=lambda e: play_next(ctx))
        
        # 다음 곡이 끝난 후 play_next 호출
        asyncio.run_coroutine_threadsafe(ctx.send(f"\n**현재 재생 중:**\n{next_title}"), client.loop)
    else:
        if not queue:
            current_song_title = None  # 곡이 없을 때 현재 곡 제목 초기화
            asyncio.run_coroutine_threadsafe(ctx.send("리스트에 저장된 곡이 없습니다."), client.loop)

@client.command()
async def play(ctx, url):
    global current_song_title  # 전역 변수 사용
    try:
        YDL_OPTIONS = {'format': 'bestaudio', 'noplaylist': 'True'}
        
        voice_channel = ctx.voice_client
        
        with youtube_dl.YoutubeDL(YDL_OPTIONS) as ydl:
            info = ydl.extract_info(url, download=False)
            title = info.get('title', '제목을 찾을 수 없습니다')
            url2 = info['url']

            # 현재 곡이 재생 중이지 않으면 첫 번째 곡 재생
            if not voice_channel.is_playing():
                current_song_title = title  # 현재 곡 제목 업데이트
                voice_channel.play(discord.FFmpegPCMAudio(executable="C:\\ffmpeg\\bin\\ffmpeg.exe", source=url2, **FFMPEG_OPTIONS), after=lambda e: play_next(ctx))
                await ctx.send(f"**현재 곡:**\n{title}")
            else:
                # 현재 재생 중인 곡이 있을 때만 큐에 추가
                queue.append((title, url2))  # 큐에 제목과 URL 추가
                await ctx.send(f"곡이 리스트에 저장되었습니다.\n{title}\n")  # 공백 제거

            # 대기 중인 곡 리스트 출력
            if queue:
                message = "\n**현재 대기 중인 곡 리스트:**\n"  # 공백 추가
                for i, (q_title, _) in enumerate(queue):
                    message += f"{i + 1}. {q_title}\n"
                await ctx.send(message)

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
    voice_channel = ctx.voice_client

    message = ""
    
    if current_song_title:  # 현재 재생 중인 곡이 있을 때
        message += f"**현재 재생 중:** {current_song_title}\n\n"  # 현재 곡 제목 추가

    if not queue:
        message += "대기 중인 곡 리스트가 없습니다."
    else:
        message += "**대기 중인 곡 리스트:**\n"  # 대기 중인 곡 리스트 구분
        for i, (title, _) in enumerate(queue):
            message += f"{i + 1}. {title}\n"
    
    await ctx.send(message)

@client.command()
async def skip(ctx):
    voice_channel = ctx.voice_client
    if not voice_channel or not voice_channel.is_connected():
        await ctx.send("저는 보이스 채널에 없어요!")
        return
    if not queue:
        await ctx.send("마지막 곡입니다! 곡을 추가해주세요.")
        return

    if voice_channel.is_playing():
        voice_channel.stop()  # 현재 곡을 중지하고

    # 다음 곡 재생 시도
    if queue:
        await ctx.send(f"**곡을 건너뛰었어요!**\n\n")
        play_next(ctx)
    else:
        await ctx.send("리스트에 저장된 곡이 없습니다.")

@client.event  # v1.0.2 추가(자동퇴장기능 - 모든 유저 퇴장 시 봇 퇴장)
async def on_voice_state_update(member, before, after):
    voice_client = member.guild.voice_client

    # 사용자가 음성 채널을 나갔을 때
    if before.channel is not None and len(before.channel.members) == 1 and voice_client and voice_client.channel == before.channel:
        # 채널에 봇만 남았을 때 퇴장
        await voice_client.disconnect()
        # 봇이 속한 텍스트 채널로 메시지 보내기
        text_channel = member.guild.text_channels[0]  # 첫 번째 텍스트 채널로 메시지 보냄 (필요시 변경 가능)

client.run(os.getenv('DISCORD_BOT_TOKEN'))
