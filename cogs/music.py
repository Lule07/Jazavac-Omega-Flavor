import os
import re
import discord
import asyncio
import logging
import spotipy

from yt_dlp import YoutubeDL
from discord.ext import commands
from discord.utils import get
from spotipy.oauth2 import SpotifyClientCredentials


def get_video_id(url: str) -> str:
    return url.lstrip("https://www.youtube.com/watch?v=")


class SongEmbed(discord.Embed):
    def __init__(self, info: dict) -> None:
        super().__init__()

        self.title = info["title"]
        self.color = discord.Color.from_rgb(240, 240, 240)

        self.set_author(name="Currently playing:", icon_url=info["platform_icon"])
        self.set_footer(text="Jazavac™ Omega Music ©, All rights reserved")
        # self.set_thumbnail(
        #    url=f"https://img.youtube.com/vi/{get_video_id(info["video_url"])}/maxresdefault.jpg"
        # )
        self.set_image(
            url=f"https://img.youtube.com/vi/{get_video_id(info["video_url"])}/maxresdefault.jpg"
        )


class Music(commands.Cog):
    def __init__(self, bot: discord.Bot) -> None:
        self.bot: discord.Bot = bot

        self.sp = spotipy.Spotify(
            client_credentials_manager=SpotifyClientCredentials(
                client_id=os.getenv("SPOTIFY_ID"),
                client_secret=os.getenv("SPOTIFY_SECRET"),
            ),
        )

        self.ytdl_opts = {
            "quiet": True,
            "format": "bestaudio/best",
            "restrictfilenames": True,
            "noplaylist": True,
            "nocheckcertificate": True,
            "extract_flat": True,
            "default_search": "auto",
        }

        self.voice_client: discord.VoiceClient | None = None
        self.latest_ctx: discord.ApplicationContext | None = None

        self.queue = asyncio.Queue(maxsize=150)
        self.playing_lock = asyncio.Lock()

    # *DONE - Checks if a url is a valid Spotify url
    def is_spotify_url(self, url: str) -> bool:
        pattern = re.compile(
            r"https?:\/\/(open\.spotify\.com\/(track|album|playlist|artist|episode|show)\/[a-zA-Z0-9]+|spotify:(track|album|playlist|artist|episode|show):[a-zA-Z0-9]+)"  # Spotify urls
        )

        return bool(pattern.match(url))

    # *DONE - Checks if a url is a valid Youtube url
    def is_yt_url(self, url: str) -> bool:
        pattern = re.compile(
            r"^(https?://)?(www\.)?(youtube\.com|youtu\.be)/"  # Domain
            r"(watch\?v=|embed/|v/|.+\?v=)?"  # Video ID prefix
            r"([a-zA-Z0-9_-]{11})$"  # Video ID
        )

        return bool(pattern.match(url))

    # *DONE - Returns the stream url from a url or a search query on Spotify
    def get_info_from_spotify(self, query: str) -> dict | None:
        with YoutubeDL(self.ytdl_opts) as ytdl:
            if self.is_spotify_url(query):
                try:
                    id = query.split("/")[-1].split("?")[0]
                    result = self.sp.track(id)

                    if not result:
                        logging.warning(f"No song for query: {query}")
                        return None

                    data = ytdl.extract_info(
                        f"ytsearch:{result["name"]} {[artist["name"] for artist in result["artists"]]}",
                        download=False,
                    )

                    if data and "entries" in data and data["entries"]:
                        logging.info(f"Successfully extracted info for query: {query}")
                        return {
                            "stream_url": ytdl.extract_info(
                                data["entries"][0]["url"], download=False
                            )["url"],
                            "video_url": data["entries"][0]["url"],
                            "title": data["entries"][0]["title"],
                            "platform_icon": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/19/Spotify_logo_without_text.svg/480px-Spotify_logo_without_text.svg.png",
                            "duration": data["entries"][0]["duration"],
                        }

                    logging.warning(f"No song for query: {query}")
                    return None

                except Exception as e:
                    logging.error(e)
                    return None

            try:
                result: dict = self.sp.search(q=query, type="track", limit=1)
                result = (result.get("tracks", {}).get("items") or [None])[0]

                if not result:
                    logging.warning(f"No song for query: {query}")
                    return None

                data = ytdl.extract_info(
                    f"ytsearch:{result["name"]} {[artist["name"] for artist in result["artists"]]}",
                    download=False,
                )

                if data and "entries" in data and data["entries"]:
                    logging.info(f"Successfully extracted info for query: {query}")
                    return {
                        "stream_url": ytdl.extract_info(
                            data["entries"][0]["url"], download=False
                        )["url"],
                        "video_url": data["entries"][0]["url"],
                        "title": data["entries"][0]["title"],
                        "platform_icon": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/19/Spotify_logo_without_text.svg/480px-Spotify_logo_without_text.svg.png",
                        "duration": data["entries"][0]["duration"],
                    }

                logging.warning(f"No song for query: {query}")
                return None

            except Exception as e:
                logging.error(e)
                return None

    # *DONE - Returns the stream url from a url or a search query on Youtube
    def get_info_from_yt(self, query: str) -> dict | None:
        with YoutubeDL(self.ytdl_opts) as ytdl:
            if self.is_yt_url(query):
                try:
                    data = ytdl.extract_info(query, download=False)

                    if data and "url" in data:
                        logging.info(f"Successfully extracted info for query: {query}")
                        return {
                            "stream_url": data["url"],
                            "video_url": query,
                            "title": data["entries"][0]["title"],
                            "platform_icon": "https://cdn4.iconfinder.com/data/icons/social-messaging-ui-color-shapes-2-free/128/social-youtube-circle-512.png",
                            "duration": data["entries"][0]["duration"],
                        }

                    logging.warning(f"No song for query: {query}")
                    return None

                except Exception as e:
                    logging.error(e)
                    return None

            try:
                data = ytdl.extract_info(f"ytsearch:{query}", download=False)

                if data and "entries" in data and data["entries"]:
                    logging.info(f"Successfully extracted info for query: {query}")
                    return {
                        "stream_url": ytdl.extract_info(
                            data["entries"][0]["url"], download=False
                        )["url"],
                        "video_url": data["entries"][0]["url"],
                        "title": data["entries"][0]["title"],
                        "platform_icon": "https://cdn4.iconfinder.com/data/icons/social-messaging-ui-color-shapes-2-free/128/social-youtube-circle-512.png",
                        "duration": data["entries"][0]["duration"],
                    }

                logging.warning(f"No song for query: {query}")
                return None

            except Exception as e:
                logging.error(e)
                return None

    # *DONE - Returns the voice client of a voice chat in the specified guild context
    async def get_voice_client(
        self, ctx: discord.ApplicationContext
    ) -> discord.VoiceClient | None:
        if not ctx.guild or not ctx.author.voice:
            logging.warning(
                f"{ctx.author.display_name} has tried to connect the bot but they are not in a voice chat."
            )
            return None

        voice_state: discord.VoiceState | None = ctx.author.voice
        voice_channel: discord.VoiceChannel = voice_state.channel

        # Tries to get the current voice client in a guild if it exists
        self.voice_client: discord.VoiceClient = get(
            self.bot.voice_clients, guild=ctx.guild
        )

        try:
            if self.voice_client and self.voice_client.is_connected():
                await self.voice_client.move_to(voice_channel)

            else:
                self.voice_client: discord.VoiceClient = await voice_channel.connect()

        except discord.ClientException as e:
            logging.error(f"Error while connecting to voice channel: {e}")
            return None

        return self.voice_client

    async def play_song(self):
        while True:
            if self.playing_lock.locked():
                await asyncio.sleep(1)

            await self.playing_lock.acquire()

            info = await self.queue.get()

            if not self.voice_client or not self.voice_client.is_connected():
                logging.error("There is no voice client to play the music")
                return

            self.song_msg: discord.Message = await self.latest_ctx.send(
                embed=SongEmbed(info)
            )

            self.voice_client.play(
                source=discord.FFmpegOpusAudio(
                    info["stream_url"],
                    before_options="-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
                    options="-vn -af 'equalizer=f=60:width_type=h:width=100:g=3'",
                ),
                after=lambda _: self.bot.loop.call_soon_threadsafe(
                    self.bot.loop.create_task, self.end_song()
                ),
            )

    async def end_song(self):
        if not self.voice_client or not self.voice_client.is_connected():
            logging.warning("There is no voice client to stop the music")

        if self.playing_lock.locked():
            logging.info("Song ended")

            try:
                self.voice_client.stop()
                await self.song_msg.delete(delay=1)
            except Exception as e:
                logging.warning(e)

            self.playing_lock.release()

            if not self.queue.empty():
                await self.play_song()

    async def clear_queue(self):
        while not self.queue.empty():
            await self.queue.get()
            self.queue.task_done()

    # *DONE - Puts the provided song into queue and starts playing it
    @commands.slash_command(
        name="play", description="Plays the selected song from Youtube or Spotify."
    )
    async def play(
        self,
        ctx: discord.ApplicationContext,
        song: str,
        platform: str = discord.Option(
            str, "Choose platform", choices=["Spotify", "Youtube"]
        ),
    ):
        await ctx.defer()

        self.latest_ctx = ctx

        info = (
            await asyncio.to_thread(self.get_info_from_spotify, song)
            if platform == "Spotify"
            else await asyncio.to_thread(self.get_info_from_yt, song)
        )

        if not info:
            await ctx.respond("Couldn't find the song.")
            return

        if not self.voice_client or not self.voice_client.is_connected():
            self.voice_client = await self.get_voice_client(ctx)

            if not self.voice_client:
                await ctx.respond("You must be in a voice channel to use this command.")
                return

        # Add the song to the queue
        await self.queue.put(info)
        await ctx.respond(f"Added song to queue.", ephemeral=True)
        try:
            await ctx.delete(delay=3)
        except Exception as e:
            logging.warning(e)

        # Start playback if not already playing
        if not self.voice_client.is_playing() and not self.voice_client.is_paused():
            await self.play_song()

    @commands.slash_command(
        name="skip", description="Skips the currently playing song."
    )
    async def skip(self, ctx: discord.ApplicationContext) -> None:
        if (
            self.voice_client
            and self.voice_client.is_connected()
            and self.playing_lock.locked()
        ):
            await ctx.defer()
            await self.end_song()
            await ctx.respond("Skipped the song.")
            try:
                await ctx.delete(delay=3)
            except Exception as e:
                logging.warning(e)
        else:
            await ctx.respond("There is no music playing.")
            try:
                await ctx.delete(delay=3)
            except Exception as e:
                logging.warning(e)

    @commands.slash_command(
        name="stop", description="Stops the playing music, clears the queue."
    )
    async def stop(self, ctx: discord.ApplicationContext) -> None:
        if (
            self.voice_client
            and self.voice_client.is_connected()
            and self.playing_lock.locked()
        ):
            await ctx.defer()
            await self.voice_client.stop()
            await self.clear_queue()
            await self.song_msg.delete(delay=0)
            await ctx.respond("Stopped the music.")

            try:
                await ctx.delete(delay=3)
            except Exception as e:
                logging.warning(e)
        else:
            await ctx.respond("There is no music playing.")
            try:
                await ctx.delete(delay=3)
            except Exception as e:
                logging.warning(e)


def setup(bot: discord.Bot) -> None:
    bot.add_cog(Music(bot))
