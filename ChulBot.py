# Discord Music Bot  
# Made by KuroBean

import discord 
from discord.ext import commands
import yt_dlp as youtube_dl
from dotenv import load_dotenv
import os
import asyncio
import functools
import aiohttp  # 비동기 HTTP 요청 처리

load_dotenv('DISCORD_BOT_TOKEN.env')
print("DISCORD_BOT_TOKEN:", os.getenv('DISCORD_BOT_TOKEN'))

intents = discord.Intents.default()
intents.message_content = True
client = commands.Bot(command_prefix='!', intents=intents, help_command=None)

# 큐를 위한 리스트 초기화
queue = []  # [ (제목, URL), ... ]
current_song_title = None  # 현재 재생 중인 곡 제목 저장
search_results = {}  # 검색 결과를 저장하는 전역 변수

FFMPEG_OPTIONS = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', 'options': '-vn'}

@client.event
async def on_ready():
    await client.change_presence(status=discord.Status.online)  # 온라인
    await client.change_presence(activity=discord.CustomActivity(name="도움말 == !명령어"))
    print("봇 이름:", client.user.name, "봇 아이디:", client.user.id, "봇 버전:", discord.__version__)

@client.command()  # !명령어 - 명령어 기능 (v1.0.3 추가)
async def 명령어(ctx):
    help_message = (
        "**사용 가능한 명령어:**\n"
        "!입장 - 봇을 보이스 채널에 초대하기\n"
        "!재생 [URL] - 음악 재생\n"
        "!검색 [곡 이름] - 유튜브 음악 검색\n"
        "!선택 [번호 선택] - 검색한 음악 재생\n"
        "!멈춰 - 음악 일시정지\n"
        "!계속 - 음악 일시정지 해제\n"
        "!스킵 - 다음 곡으로 건너뛰기\n"
        "!리스트 - 예약된 곡 목록 보기\n"
        "!삭제 - 음악 중지 및 리스트 삭제\n"
        "!나가 - 봇 내보내기"
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
async def 입장(ctx):  # v1.0.2 추가(자동퇴장기능)
    if not ctx.author.voice:
        await ctx.send("당신은 현재 보이스 채널에 없어요!")
        return
    channel = ctx.author.voice.channel
    await channel.connect()
    # 자동 퇴장을 위한 타이머 시작
    asyncio.create_task(auto_disconnect_timer(ctx))

@client.command()
async def 나가(ctx):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
    else:
        await ctx.send("저는 보이스 채널에 없어요!")

async def play_next(ctx):
    global current_song_title  # 전역 변수 사용
    voice_channel = ctx.voice_client
    if queue and not voice_channel.is_playing():  # 곡이 남아있고 현재 곡이 재생 중이지 않을 때만
        next_title, next_url = queue.pop(0)  # 큐에서 다음 곡을 가져와 재생
        current_song_title = next_title  # 현재 재생 중인 곡 제목 업데이트
        voice_channel.play(discord.FFmpegPCMAudio(executable="ffmpeg", source=next_url, **FFMPEG_OPTIONS), after=lambda e: asyncio.run_coroutine_threadsafe(play_next(ctx), client.loop))
        await ctx.send(f"\n**현재 재생 중:**\n{next_title}")
    else:
        if not queue:
            current_song_title = None  # 곡이 없을 때 현재 곡 제목 초기화
            await ctx.send("리스트에 저장된 곡이 없습니다.")

@client.command()
async def 재생(ctx, url):
    global current_song_title
    try:
        # YDL_OPTIONS에 'extract_flat' 옵션 추가하여 재생목록의 메타데이터만 가져오도록 설정
        YDL_OPTIONS = {'format': 'bestaudio', 'noplaylist': 'False', 'extract_flat': 'in_playlist'}
        voice_channel = ctx.voice_client

        # extract_info 함수 정의
        def extract_info(url):
            with youtube_dl.YoutubeDL(YDL_OPTIONS) as ydl:
                return ydl.extract_info(url, download=False)

        # 재생목록 메타데이터를 먼저 비동기적으로 가져옴
        first_info = await asyncio.to_thread(extract_info, url)

        if 'entries' in first_info:
            # 재생목록일 경우 첫 번째 항목만 가져옴
            first_entry = first_info['entries'][0]
            first_url = first_entry['url']
            first_title = first_entry.get('title', '제목을 찾을 수 없습니다')
            current_song_title = first_title

            # 실제 오디오 URL을 가져오기 위한 YDL_OPTIONS 재설정
            YDL_OPTIONS['extract_flat'] = False

            # 첫 번째 곡을 비동기적으로 가져와서 재생
            song_info = await asyncio.to_thread(extract_info, first_url)
            audio_url = song_info['url']

            voice_channel.play(discord.FFmpegPCMAudio(executable="ffmpeg", source=audio_url, **FFMPEG_OPTIONS), after=lambda e: asyncio.run_coroutine_threadsafe(play_next(ctx), client.loop))
            await ctx.send(f"**현재 곡:** {first_title}")

            # 백그라운드에서 나머지 곡들을 큐에 추가
            async def add_remaining_entries(entries):
                for entry in entries[1:]:
                    url2 = entry['url']
                    song_info = await asyncio.to_thread(extract_info, url2)
                    title = song_info.get('title', '제목을 찾을 수 없습니다')
                    audio_url = song_info['url']
                    queue.append((title, audio_url))
                    # 다른 작업에 이벤트 루프 양보
                    await asyncio.sleep(0)

                # 모든 곡 추가 완료 후 알림
                await ctx.send("모든 곡이 큐에 추가되었습니다.")
                # 대기 중인 곡 리스트 출력
                if queue:
                    message = "\n**대기 중인 곡 리스트:**\n"
                    for i, (q_title, _) in enumerate(queue):
                        message += f"{i + 1}. {q_title}\n"
                    await ctx.send(message)

            # 비동기적으로 나머지 곡들을 큐에 추가
            asyncio.create_task(add_remaining_entries(first_info['entries']))
        else:
            # 단일 동영상일 경우 기존 방식으로 처리
            song_info = first_info
            title = song_info.get('title', '제목을 찾을 수 없습니다')
            audio_url = song_info['url']
            if not voice_channel.is_playing():
                current_song_title = title
                voice_channel.play(discord.FFmpegPCMAudio(executable="ffmpeg", source=audio_url, **FFMPEG_OPTIONS), after=lambda e: asyncio.run_coroutine_threadsafe(play_next(ctx), client.loop))
                await ctx.send(f"**현재 곡:** {title}")
            else:
                queue.append((title, audio_url))
                await ctx.send(f"곡이 리스트에 저장되었습니다: {title}")

    except Exception as e:
        await ctx.send(f"오류가 발생했습니다: {str(e)}")


@client.command()
async def 멈춰(ctx):
    voice_channel = ctx.voice_client
    if voice_channel.is_playing():
        voice_channel.pause()

@client.command()
async def 계속(ctx):
    voice_channel = ctx.voice_client
    if voice_channel.is_paused():
        voice_channel.resume()

@client.command()
async def 삭제(ctx):
    voice_channel = ctx.voice_client
    if voice_channel.is_playing():
        voice_channel.stop()
        queue.clear()  # 큐의 모든 노래 삭제
        await ctx.send("곡을 멈추고 리스트를 전체 삭제합니다.")
    else:
        await ctx.send("현재 음악 재생 중이 아닙니다.")

@client.command()
async def 리스트(ctx):
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
async def 스킵(ctx):
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

@client.command() #검색 및 선택 기능 (v1.1.1)
async def 검색(ctx, *, query=None):
    """유튜브에서 노래를 검색하고 선택할 수 있는 기능"""
    global search_results
    YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY')  # API 키 가져오기

    if not YOUTUBE_API_KEY:
        await ctx.send("YouTube API Key가 설정되지 않았습니다. 관리자에게 문의하세요.")
        return

    if not query:
        await ctx.send("사용법: `!검색 [키워드]`를 입력하세요.")
        return

    search_url = "https://www.googleapis.com/youtube/v3/search"

    params = {
        "part": "snippet",
        "q": query,
        "type": "video",
        "videoCategoryId": "10",  # 음악 카테고리
        "maxResults": 5,  # 최대 5개 결과 반환
        "key": YOUTUBE_API_KEY,
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(search_url, params=params) as response:
            if response.status != 200:
                await ctx.send("검색 중 오류가 발생했습니다.")
                return

            data = await response.json()
            results = data.get("items", [])

            if not results:
                await ctx.send("검색 결과가 없습니다.")
                return

            message = "**🔍 검색 결과:**\n"
            search_results[ctx.author.id] = []  # 현재 사용자의 검색 결과 초기화

            for i, item in enumerate(results, start=1):
                title = item["snippet"]["title"]
                video_id = item["id"]["videoId"]
                video_url = f"https://www.youtube.com/watch?v={video_id}"
                message += f"{i}. {title}\n"  # 제목만 추가
                search_results[ctx.author.id].append((title, video_url))

            await ctx.send(message)
            await ctx.send("재생하려면 `!선택 [번호]`를 입력하세요.")

@client.command()
async def 선택(ctx, number: int):
    """검색된 목록에서 노래를 선택하여 재생"""
    global search_results
    if ctx.author.id not in search_results or not search_results[ctx.author.id]:
        await ctx.send("먼저 `!검색` 명령어를 사용하여 노래를 검색하세요.")
        return

    try:
        selected_song = search_results[ctx.author.id][number - 1]  # 선택된 노래
        title, url = selected_song

        # 봇이 음성 채널에 없으면 자동으로 연결
        if not ctx.voice_client:
            await 입장(ctx)

        # 선택된 노래 재생
        await 재생(ctx, url)
        del search_results[ctx.author.id]  # 검색 결과 초기화

    except IndexError:
        await ctx.send("유효하지 않은 번호입니다. 다시 시도하세요.")
    except Exception as e:
        await ctx.send(f"오류가 발생했습니다: {str(e)}")

client.run(os.getenv('DISCORD_BOT_TOKEN'))
