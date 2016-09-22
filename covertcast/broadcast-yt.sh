#!/bin/sh

# check out https://trac.ffmpeg.org/wiki/Encode/H.264

# -g 60 ???
#ffmpeg -re -loop 1 -i out.jpg -re -f lavfi -i aevalsrc=0 -codec:v libx264 -video_size 1280x720 -pix_fmt yuv420p -profile:v main -minrate 3000k -maxrate 3000k -b:v 3000k -c:a libvo_aacenc -g 30 -f flv -strict experimental rtmp://a.rtmp.youtube.com/live2/XXX


INPUT=""
# Read input as native framerate
INPUT="$INPUT -re"
# Loop over input stream
INPUT="$INPUT -loop 1"
# Input file
INPUT="$INPUT -i out.jpg"

AUDIO=""
# Read input as native framerate
AUDIO="$AUDIO -re"
# Audio codec (lavfi is better for bandwidth?)
AUDIO="$AUDIO -f lavfi"
# Input (dummy)
AUDIO="$AUDIO -i aevalsrc=0"

OUTPUT=""
# Video codec
OUTPUT="$OUTPUT -c:v libx264"
# Video resolution
OUTPUT="$OUTPUT -video_size 1280x720"
# Pixel format
#OUTPUT="$OUTPUT -pix_fmt yuv420p"
# Sets H.265 profile to high efficieny lossless whatever
#OUTPUT="$OUTPUT -preset ultrafast -qp 0"
# Attempt to force bitrate at 3000k
OUTPUT="$OUTPUT -b:v 1500k -maxrate 1500k -minrate 1500k"
# frames per second
OUTPUT="$OUTPUT -r 25"
# quality
OUTPUT="$OUTPUT -q:v 20"
# Audio codec
OUTPUT="$OUTPUT -c:a libvo_aacenc"
# GOP size (calculates intraframes)
OUTPUT="$OUTPUT -g 30"
# Format
OUTPUT="$OUTPUT -f flv"
# Allow use of "experimental" encoders
OUTPUT="$OUTPUT -strict experimental"
# Testing
OUTPUT="$OUTPUT rtmp://a.rtmp.youtube.com/live2/XXX"
#OUTPUT="$OUTPUT whatever3.flv"

ffmpeg $INPUT $AUDIO -threads 8 -y $OUTPUT
