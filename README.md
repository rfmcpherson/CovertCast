# CovertCast

We design, implement, and evaluate CovertCast, a censorship circumvention system
that broadcasts the content of popular websites in real-time, encrypted video
streams on common live-streaming services such as YouTube. CovertCast does not
require any modifications to the streaming service and employs the same
protocols, servers, and streaming software as any other user of the
service. Therefore, CovertCast cannot be distinguished from other live streams
by IP address filtering or protocol fingerprinting, raising the bar for censors.

This is proof of concept code and should NOT be used in production without
further refining and testing of security. 

See CovertCast-PETS16.pdf for details.

## Dependencies

Both the client and server use Python3. The client is designed for Windows and
also makes use of C++. The server is designed for Linux. If one operating system
is desired, it will probably easier to port the client to Linux than the server
to Windows.

### Client (Windows)

pywin32 [Download and install](http://sourceforge.net/projects/pywin32/)

nghttp2 [My own personal hack](https://gist.github.com/rfmcpherson/3697969c5a518eeeaf0a)

### Server (Linux)

ffmpeg [So annoying to get right](https://gist.github.com/rfmcpherson/f24aca04e77afe78ad623bf286c9266b) <- Install instructions may be out of date.

ghost.py `sudo pip install Ghost.py`

### Both

numpy           Linux: `sudo apt-get install python3-numpy`

                [Windows](http://www.lfd.uci.edu/~gohlke/pythonlibs/#numpy)
                
                
cv2             Linux: `sudo apt-get install python3-opencv`

                [Windows](http://www.lfd.uci.edu/~gohlke/pythonlibs/#opencv)
                
                
PIL             `sudo pip install Pillow`

reedsolo        `sudo pip install reedsolo`

bitstring       `sudo pip install bitstring`


## How to use

The client code is written for Windows. The server runs on Linux.

1. Start up a RTMP live stream on YouTube. 
2. Run broadcast-yt.sh on the server (edit the script for your RTMP). If there is no out.jpg, run `python3 server` for a second and then stop it.
4. Load the stream on the client in a browser (bigger box. not full screen. 720p video).
5. Load another browser using an HTTP2 proxy pointed at the `h2ip` in `h2clientweb.py`.
7. Start `python3 client.py` on the client.
8. Start the screen scraping code on the client.
6. Start `python3 server.py` on the server.

## Parts

Information about the individual code in each folder.

### covertcast

Contains the source code needed to run the thing.

`broadcast-yt.sh` Creates a silent RTMP video from out.jpg and streams
it to YouTube. You'll need to update the YouTube RTMP URL.

`client.py` Launches the client version of the code. See options with
`python3 client.py --help`

`server.py` Launches the server version of the code. See options with
`python3 server.py --help`

#### config

Some stored configuration files. ```config-server``` is read in
``server.py``.

#### logger

Code used for logging and debugging.

#### obj

Python lib containing some named tuples used in HTTP management.

#### prefetching

The library we use for picking what links to prefetch.

#### util

Some various utility functions.

#### video

Code used in the modulation and demodulation of data and video.

`clientframes2data.py` converts individual images to data
`clientvideo2frames.py` converts video to individual frames
`functions.py` modulates/demodulates data (or metadata) from a frame
`modulate.py` deals with metadata and calls functions.py for frames/data
`parameters.py` hardcoded parameters
`servervideo.py` used to help create images and save them for ffmpeg
`tests.py` tests stuff
`valid_image.py` tests if a CovertCast image is valid
`video_helper_functions.py` lots of little things

#### web

Handles the HTTP/proxy stuff

We call the code that directs the web scraper ``guides''. Currently they load
the main page of a news site and then iterate through the linked stories,
sending one of them at a time.

The folder README covers a lot of important stuff
`fake*` are versions used for testing
`h2*` are newer versions of the web code. You should use these
`h2guides` picks what stories to read

### screenscraper

C code used to scrap a browser window in Windows. Change the `hwnd`
variable in `main` to use a different browser/streaming
service. Interacts with code in
`covertcast/video/clientvideo2frames.py`

