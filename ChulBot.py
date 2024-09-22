import discord
from discord.ext import commands
import yt_dlp as youtube_dl
from dotenv import load_dotenv
import os

load_dotenv('DISCORD_BOT_TOKEN.env')
print("DISCORD_BOT_TOKEN:", os.getenv('DISCORD_BOT_TOKEN'))

intents = discord.Intents.default()
intents.message_content = True
client = commands.Bot(command_prefix='!', intents=intents)

# 노래 대기열과 현재 재생 중인 노래 제목
queue = []
current_playing = None

@client.event
async def on_ready():
    print(f'Logged in as {client.user}')

@client.command()
async def join(ctx):
    if not ctx.author.voice:
        await ctx.send("당신은 현재 보이스챗에 없어요!")
        return
    channel = ctx.author.voice.channel
    await channel.connect()

@client.command()
async def leave(ctx):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
    else:
        await ctx.send("저는 현재 보이스챗에 없어요!")

@client.command()
async def play(ctx, url):
    global queue, current_playing
    try:
        YDL_OPTIONS = {'format': 'bestaudio', 'noplaylist': 'True'}
        FFMPEG_OPTIONS = {
            'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
            'options': '-vn -loglevel debug'
        }

        with youtube_dl.YoutubeDL(YDL_OPTIONS) as ydl:
            info = ydl.extract_info(url, download=False)
            title = info['title']
            url2 = info['url']
            queue.append((title, url2))  # 제목과 URL을 대기열에 추가
            await ctx.send(f"재생목록에 추가: {title}")

            # 현재 재생 중이지 않으면 재생 시작
            if not ctx.voice_client.is_playing():
                current_playing = title  # 현재 재생 중인 노래 제목 저장
                await play_next(ctx)

    except Exception as e:
        await ctx.send(f"An error occurred: {str(e)}")

async def play_next(ctx):
    global queue, current_playing
    if queue:
        title, url2 = queue.pop(0)
        ctx.voice_client.play(
            discord.FFmpegPCMAudio(
                executable="C:\\discordBot\\ffmpeg-master-latest-win64-gpl-shared\\bin\\ffmpeg.exe",
                source=url2,
                options="-filter:a 'volume=0.5'"  # 볼륨 50%로 설정
            ),
            after=lambda e: client.loop.create_task(play_next(ctx))
        )
        current_playing = title  # 현재 재생 중인 노래 제목 업데이트
        await ctx.send(f"현재 재생 중: {title}")
    else:
        current_playing = None  # 대기열이 비어있으면 현재 재생 중인 노래 없음
        await ctx.send("재생목록이 비어있어요!")

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

@client.command()
async def list(ctx):
    global queue, current_playing
    if current_playing:
        current_title = current_playing
    else:
        current_title = "None"

    if queue:
        titles = "\n".join([f"{i+1}. {title}" for i, (title, _) in enumerate(queue)])
        await ctx.send(f"현재 재생 중: {current_title}\n\n현재 재생목록:\n{titles}")
    else:
        await ctx.send(f"현재 재생 중: {current_title}\n\n재생목록이 비어있어요!")

@client.command()
async def skip(ctx):
    voice_channel = ctx.voice_client
    if voice_channel.is_playing():
        voice_channel.stop()
        await ctx.send("현재 노래를 스킵합니다.")
    else:
        await ctx.send("저는 현재 어떤 노래도 틀고 있지 않아요!")

client.run(os.getenv('DISCORD_BOT_TOKEN'))
