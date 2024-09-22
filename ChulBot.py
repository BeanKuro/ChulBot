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

# 큐를 위한 리스트 초기화
queue = []  # [ (제목, URL), ... ]

FFMPEG_OPTIONS = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', 'options': '-vn'}

@client.event
async def on_ready():
    print(f'Logged in as {client.user}')

@client.command()
async def join(ctx):
    if not ctx.author.voice:
        await ctx.send("당신은 현재 보이스 채널에 없어요!")
        return
    channel = ctx.author.voice.channel
    await channel.connect()

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
        asyncio.run_coroutine_threadsafe(ctx.send(f"현재 재생 중: {next_title}"), client.loop)
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
                await ctx.send(f"현재 곡: {next_title}")
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
        await ctx.send(f"스킵!\n 현재 곡: {next_title}")
    else:
        await ctx.send("리스트에 저장된 노래가 없습니다.")

client.run(os.getenv('DISCORD_BOT_TOKEN'))
