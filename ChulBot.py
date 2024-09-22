import discord
from discord.ext import commands
import yt_dlp as youtube_dl  # yt-dlp로 변경
from dotenv import load_dotenv  # dotenv 패키지 임포트
import os

# env 파일 불러오기
load_dotenv('DISCORD_BOT_TOKEN.env')
print("DISCORD_BOT_TOKEN:", os.getenv('DISCORD_BOT_TOKEN'))


intents = discord.Intents.default()
intents.message_content = True
client = commands.Bot(command_prefix='!', intents=intents)

@client.event
async def on_ready():
    print(f'Logged in as {client.user}')

@client.command()
async def join(ctx):
    if not ctx.author.voice:
        await ctx.send("You are not in a voice channel!")
        return
    channel = ctx.author.voice.channel
    await channel.connect()

@client.command()
async def leave(ctx):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
    else:
        await ctx.send("I'm not in a voice channel!")

@client.command()
async def play(ctx, url):
    try:
        YDL_OPTIONS = {'format': 'bestaudio', 'noplaylist': 'True'}
        FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn -loglevel debug'
}

        voice_channel = ctx.voice_client
        
        with youtube_dl.YoutubeDL(YDL_OPTIONS) as ydl:
            info = ydl.extract_info(url, download=False)
            url2 = info['url']  # 변경
            voice_channel.play(discord.FFmpegPCMAudio(executable="C:\\discordBot\\ffmpeg-master-latest-win64-gpl-shared\\bin\\ffmpeg.exe", source=url2, **FFMPEG_OPTIONS))
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

client.run(os.getenv('DISCORD_BOT_TOKEN'))  # .env 파일에서 토큰 가져오기
