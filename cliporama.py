# A python program that chooses a random video file from a directory of video files, 
# makes a random clip of various lengths (eg - 5-10 seconds), writes that to a new file 
# and serves it via http to a receiving application (i.e. - OBS Studio). 
#
# The concept for came from scrubbing through episodes of Futurama, realizing that
# "no matter where you scrub to, you seem to get a good funny little clip" and this just automates
# that procedure.  It might work well for other video collections, it might not.  You 
# can get wacky results using it on a corpus of Tom Baker era Doctor Who episdoes, I find.  
#
# Most of the heavy lifting is done by ffmpeg-python  https://github.com/kkroening/ffmpeg-python
#
# Steven Cogswell https://github.com/scogswell/

import os
import sys
import random
import ffmpeg
import subprocess

# This can be a subdirectory, or an absolute path.  
#searchDirectory = "video"
#searchDirectory ="/Volumes/NightAttack/Night Attack"
searchDirectory ="/Volumes/NightAttack/Doctor Who/"

# Note some video files (e.g. flv) will not work because ffmpeg-python can't
# read the duration information from them properly.  "your mileage may vary"
allowed_files=[".mp4",".m4v"]

# You can change the clip_name if you want, the program keeps track. 
clip_name = "out.mp4"
clip_length_minimum = 5   # seconds
clip_length_maximum = 10  # seconds

# ffmpeg http streaming parameters 
stream_video_format = "flv"
stream_server_url = "http://0.0.0.0:8080"
stream_timeout = 30  # timeout for serving clip via http, in seconds. 

# Extract a clip of duration from a file 
#
# https://github.com/kkroening/ffmpeg-python/issues/184#issuecomment-504390452
# It is WAY FASTER to use ss= to seek the video rather than trim it 
# https://trac.ffmpeg.org/wiki/Seeking#Cuttingsmallsections
# https://github.com/kkroening/ffmpeg-python/issues/155#issuecomment-498060127
def extract_clip(input_path, output_path, start=30, end=60, size=480):
    input_stream = ffmpeg.input(input_path, ss=start, t=end-start)

    vid = (
        input_stream.video
        .setpts('PTS-STARTPTS')
        .filter('scale', size,-2)
    )
    aud = (
        input_stream.audio
        .filter_('asetpts', 'PTS-STARTPTS')
    )
    joined = ffmpeg.concat(vid, aud, v=1, a=1).node
    output = ffmpeg.output(joined[0], joined[1], output_path).overwrite_output()
    output.run(capture_stdout=True, capture_stderr=True)

# Serve up a video clip as an http (tcp) stream.  Note someone (OBS) must read the stream or it just blocks until the timeout. 
def serve_clip_via_http(clip_name,stream_server_url,stream_video_format):
    #https://github.com/kkroening/ffmpeg-python/blob/master/examples/README.md#stream-from-a-local-video-to-http-server
    #https://github.com/kkroening/ffmpeg-python/issues/608#issuecomment-957781280
    # You need the re=None in the input, as the global_args doesn't appear to work for it.
    # "re" makes ffmpeg process in realtime, so the process ends roughly when the video has 
    # been transmitted in total.   
    # Error handling: https://github.com/kkroening/ffmpeg-python/issues/165#issuecomment-493587798
    # If you get the bind error already in use from a crashed previous run, on osx use: sudo lsof -nP -i:8080|grep LISTEN 
    # to find the pid to kill it.  Other systems are probably similar, eh. 
    # https://alexandra-zaharia.github.io/posts/kill-subprocess-and-its-children-on-timeout-python/
    # https://docs.python.org/3/library/subprocess.html
    try:
        process = (
            ffmpeg
            .input(clip_name, re=None)
            .output(
                stream_server_url, 
                codec = "copy", # use same codecs of the original video
                listen=1, # enables HTTP server
                f=stream_video_format)
            .run_async(pipe_stdout=True, pipe_stderr=True)
        )
        ret = process.communicate(timeout=stream_timeout)
        if process.returncode != 0:
            print(f"stdout: {ret[0].decode('utf8')}\nstderr: {ret[1].decode('utf8')}")
            print("Some sort of error happened, sorry")
    except ffmpeg.Error as e:
        print('stdout:', e.stdout.decode('utf8'))
        print('stderr:', e.stderr.decode('utf8'))
        raise e
    except subprocess.TimeoutExpired:
        print(f'Timeout. Attempting to kill process')
        process.terminate()

# searches a directory recursively and makes a list of all valid video files (via "allowed_files" suffixes)
def make_list_of_video_files(searchDirectory, allowed_files=".mp4"):
    allVideoFiles=[]
    for root, dirs, files, in os.walk(searchDirectory):
        for f in files:
            for exts in allowed_files:
                if f.endswith(exts):
                    allVideoFiles.append(os.path.join(root, f))
                    break
    return allVideoFiles

# The actual main program 
def play_random_clip():
    if os.path.isdir(searchDirectory) == False:
        print(f"Can't find directory {searchDirectory}")
        return

    print(f"Scanning for video files in {searchDirectory}")
    allVideoFiles = make_list_of_video_files(searchDirectory, allowed_files)

    num_files = len(allVideoFiles)
    print(f"Found {num_files} video files")
    if num_files < 1:
        print(f"You should have video files with the right extensions {allowed_files} in the directory")
        return

    # Pick a file from the list of files at random
    random_file_index = random.randint(0,num_files-1)
    random_file_name = allVideoFiles[random_file_index]

    # Read a video file to get the duration of it.  
    # https://github.com/kkroening/ffmpeg-python/blob/master/examples/video_info.py#L15
    try:
        probe = ffmpeg.probe(random_file_name)
    except ffmpeg.Error as e:
        print(e.stderr, file=sys.stderr)
        return
    video_stream = next((stream for stream in probe['streams'] if stream['codec_type'] == 'video'), None)
    width = int(video_stream['width'])
    height = int(video_stream['height']) 
    duration = float(video_stream['duration'])

    # Pick a random clip length from clip_length_minimum to clip_length_maximum seconds, starting anywhere in the video 
    clip_duration = random.randint(clip_length_minimum,clip_length_maximum)
    clip_start = random.uniform(0,duration - clip_duration)
    # In the case of short clips, the duration can be longer than the video 
    # so adjust start and endpoints apporpriately 
    if clip_start < 0:
        clip_start = 0
    if clip_start+clip_duration > duration:
        clip_duration = duration-clip_start
    clip_end = clip_start + clip_duration

    print(f"Clip from {random_file_name} (random file {random_file_index}):")
    print(f"Original video width is {width}, height is {height}, duration is {duration}")
    print(f"Clip is from time {clip_start} s to {clip_end} s, ({clip_duration} seconds)")

    # This makes the clip as a file called clip_name defined above.  If you just want the clip
    # to use in other sources you can just use this
    print(f"Trimming Clip...")
    extract_clip(random_file_name,clip_name,clip_start,clip_end, 480)

    # If you just wanted to generate the clip via clip_name you can comment out this next part
    # which serves it up via http to OBS or whatever. 
    print("Sending Clip via http...")
    serve_clip_via_http(clip_name, stream_server_url, stream_video_format)
    
    print(f"Done")

# lol python you so crazy 
if __name__ == '__main__':
    play_random_clip()