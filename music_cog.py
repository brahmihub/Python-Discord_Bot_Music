import discord
from discord.ext import commands
from youtubesearchpython import VideosSearch
from pytube import YouTube
import asyncio
from ast import alias
import os
import threading
class music_cog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        # all the music-related stuff
        self.is_playing = False
        self.is_paused = False
        self.playback_lock = threading.Lock()

        # 2d array containing [song, channel]
        self.music_queue = []
        self.FFMPEG_OPTIONS = {'options': '-vn'}

        self.vc = None

    # searching the item on youtube
    def search_yt(self, item):
        if item.startswith("https://"):
            yt = YouTube(item)
            return {'source': item, 'title': yt.title}
        else:
            search = VideosSearch(item, limit=1)
            result = search.result()
            if result['result']:
                return {'source': result['result'][0]['link'], 'title': result['result'][0]['title']}
            else:
                return None
    
    async def play_next(self):
        if len(self.music_queue) > 0:
            self.is_playing = True
            try:
                current_path = os.getcwd()
                current_path=current_path.replace("/","//")
                # List all files in the folder
                files = os.listdir(current_path)

                # Iterate through each file
                for file in files:
                    # Check if the file is an MP3 file
                    if file.endswith(".mp4"):
                        # Construct the full file path
                        file_path = os.path.join(current_path, file)

                        # Delete the file
                        os.remove(file_path)
                        print(f"Deleted: {file_path}")
                         
            except:
                pass
            # get the first url
            m_url = self.music_queue[0][0]['source']

            # remove the first element as you are currently playing it
            self.music_queue.pop(0)

            yt = YouTube(m_url)
            song = yt.streams.filter(only_audio=True).first()
            self.vc.play(
                discord.FFmpegPCMAudio(song.download(), **self.FFMPEG_OPTIONS),
                after=lambda e: self.bot.loop.create_task(self.play_next())
            )
            
        else:
            self.is_playing = False
            
    # infinite loop checking 
    async def play_music(self, ctx):
        try:
            if len(self.music_queue) > 0:
                self.is_playing = True
                try:
                    current_path = os.getcwd()
                    current_path=current_path.replace("/","//")
                    # List all files in the folder
                    files = os.listdir(current_path)

                    # Iterate through each file
                    for file in files:
                        # Check if the file is an MP3 file
                        if file.endswith(".mp4"):
                            # Construct the full file path
                            file_path = os.path.join(current_path, file)

                            # Delete the file
                            os.remove(file_path)
                            print(f"Deleted: {file_path}")
                         
                except:
                    pass
                
                m_url = self.music_queue[0][0]['source']
                # try to connect to the voice channel if you are not already connected
                if self.vc is None or not self.vc.is_connected():
                    self.vc = await self.music_queue[0][1].connect()

                    # in case we fail to connect
                    if self.vc is None:
                        await ctx.send("```Could not connect to the voice channel```")
                        return
                else:
                    await self.vc.move_to(self.music_queue[0][1])

                # remove the first element as you are currently playing it
                self.music_queue.pop(0)

                yt = YouTube(m_url)
                song = yt.streams.filter(only_audio=True).first()
                self.vc.play(
                    discord.FFmpegPCMAudio(song.download(), **self.FFMPEG_OPTIONS),
                    after=lambda e: asyncio.run_coroutine_threadsafe(self.play_next(), self.bot.loop)
                )
                
                
            else:
                self.is_playing = False
               
        except Exception as e:
            print(f"An error occurred: {e}")
        finally:
            await asyncio.sleep(0)  # Allow other tasks to be processed

    @commands.command(name="play", aliases=["p", "playing"], help="Plays a selected song from youtube")
    async def play(self, ctx, *args):
        query = " ".join(args)
        try:
            voice_channel = ctx.author.voice.channel
        except:
            await ctx.send("```You need to connect to a voice channel first!```")
            return
        if self.is_paused:
            self.vc.resume()
        else:
            song_info = self.search_yt(query)
            if song_info is None:
                await ctx.send("```Invalid input. Please provide a valid YouTube link or video name.```")
            else:
                if self.is_playing:
                    await ctx.send(f"**#{len(self.music_queue)+2} -'{song_info['title']}'** added to the queue")
                else:
                    await ctx.send(f"Playing **'{song_info['title']}'**")
                self.music_queue.append([song_info, voice_channel])
                if not self.is_playing:
                    
                    await self.play_music(ctx)

    @commands.command(name="pause", help="Pauses the current song being played")
    async def pause(self, ctx, *args):
        with self.playback_lock:

            self.is_playing = False
            self.is_paused = True
            self.vc.pause()

            
    @commands.command(name="resume", aliases=["r"], help="Resumes playing with the discord bot")
    async def resume(self, ctx, *args):
        with self.playback_lock:

            self.is_paused = False
            self.is_playing = True
            self.vc.resume()

    @commands.command(name="skip", aliases=["s"], help="Skips the current song being played")
    async def skip(self, ctx):
        with self.playback_lock:
            try:
                current_path = os.getcwd()
                current_path=current_path.replace("/","//")
                # List all files in the folder
                files = os.listdir(current_path)

                # Iterate through each file
                for file in files:
                    # Check if the file is an MP3 file
                    if file.endswith(".mp4"):
                        # Construct the full file path
                        file_path = os.path.join(current_path, file)

                        # Delete the file
                        os.remove(file_path)
                        print(f"Deleted: {file_path}")

            except:
                pass
            if self.vc and self.vc.is_playing():
                self.vc.stop()
                # try to play next in the queue if it exists
                await self.play_music(ctx)
                
    @commands.command(name="queue", aliases=["q"], help="Displays the current songs in queue")
    async def queue(self, ctx):
        retval = ""
        for i in range(0, len(self.music_queue)):
            retval += f"#{i+1} -" + self.music_queue[i][0]['title'] + "\n"

        if retval != "":
            await ctx.send(f"```queue:\n{retval}```")
        else:
            await ctx.send("```No music in queue```")

# Make sure to add this cog to your bot in the main file

    @commands.command(name="clear", aliases=["c", "bin"], help="Stops the music and clears the queue")
    async def clear(self, ctx):
        if self.vc != None and self.is_playing:
            self.vc.stop()
        self.music_queue = []
        try:
            current_path = os.getcwd()
            current_path=current_path.replace("/","//")
            # List all files in the folder
            files = os.listdir(current_path)

            # Iterate through each file
            for file in files:
                # Check if the file is an MP3 file
                if file.endswith(".mp4"):
                    # Construct the full file path
                    file_path = os.path.join(current_path, file)

                    # Delete the file
                    os.remove(file_path)
                    print(f"Deleted: {file_path}")
                         
        except:
            pass
        await ctx.send("```Music queue cleared```")

    @commands.command(name="stop", aliases=["disconnect", "l", "d"], help="Kick the bot from VC")
    async def dc(self, ctx):
        self.is_playing = False
        self.is_paused = False
        await self.vc.disconnect()
        try:
            current_path = os.getcwd()
            current_path=current_path.replace("/","//")
            # List all files in the folder
            files = os.listdir(current_path)

            # Iterate through each file
            for file in files:
                # Check if the file is an MP3 file
                if file.endswith(".mp4"):
                    # Construct the full file path
                    file_path = os.path.join(current_path, file)

                    # Delete the file
                    os.remove(file_path)
                    print(f"Deleted: {file_path}")
                         
        except:
            pass
        
        
    @commands.command(name="remove", help="Removes last song added to queue")
    async def re(self, ctx):
        self.music_queue.pop()
        await ctx.send("```last song removed```")