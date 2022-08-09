# README

A python program that chooses a random video file from a directory of video files, 
makes a random clip of various lengths (e.g. - 5-10 seconds), writes that to a new file 
and serves it via http to a receiving application (e.g. - OBS Studio). 

The concept for came from scrubbing through episodes of Futurama, realizing that
"no matter where you scrub to, you seem to get a good funny little clip", and this just automates that procedure.  It might work well for other video collections, it might not.  You 
can get wacky results using it on a corpus of Tom Baker era Doctor Who episdoes, I find.  

The clip is resized to fit in a 480 pixel box, change that if you want bigger or smaller.  

Depending on host computer power this can take a few seconds to process the clip.   It may be worthwhile to pre-process all the video files to be proper size/codec to speed things up.  

Most of the heavy lifting is done by ffmpeg-python  https://github.com/kkroening/ffmpeg-python

## Usage

1. Setup a Virtual environment:

```
    python -m venv .venv
    . .venv/bin/activate
```

2. Install ffmpeg-python:

```
pip install ffmpeg-python
```

3. Edit variables in `cliporama.py` to point at your source video files and setup clip parameters:

```
searchDirectory =  "video" (path to where video files are stored, this can be a subdirectory of where the script file is run from)
allowed_files=[".mp4",".m4v"]
clip_name = "out.mp4"
clip_length_minimum = 5   # seconds
clip_length_maximum = 10  # seconds
```

4. Add a `Media Source` to OBS Studio:

```
Restart playback when source becomes active: checked 

input: URL of machine serving the clip, e.g. - http://127.0.0.1:8080

Reconnect Delay: 1s  (Shorter appears to make it start up faster when the clip is generated)

```

If OBS or other application is not available to consume the http stream, it will timeout after 30 seconds.

It's easiest to adjust the `Media Source` object's size and position in OBS when a clip is actually playing.  When the clip is not playing the `Media Source` has no visible outline placeholder. 