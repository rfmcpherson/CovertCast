#!/usr/bin/python3
import argparse
import multiprocessing
import sys
import traceback

import config
import video
import web

# Load parser arguments
def parse():
    parser = argparse.ArgumentParser()

    # Properties
    parser.add_argument(
        '-service', action='store', dest='service', default='youtube', 
        help='Streaming server: connectcast or youtube')

    # Change minor functionality (i.e. small branches)
    parser.add_argument(
        '-skipvid', action='store_true', dest='skip_vid', default=False, 
        help='Skips sending the frames to video and saves them locally')
    parser.add_argument(
        '-skipguide', action='store_true', dest='skip_guide', default=False, 
        help='Skips using the guide and returns a set url')
    parser.add_argument(
        '-record', action='store', dest='record_location', default=None, 
        help='Location to store all data for testing')

    # Change major functionality (i.e. code flow)
    parser.add_argument(
        '-time', action='store_true', dest='timer', default=False, 
        help='Runs the timing functions on critical sections of the code')
    parser.add_argument(
        '-test', action='store_true', dest='tester', default=False, 
        help='Runs the simple tests we have')
    parser.add_argument(
        '-fake', action='store_true', dest='fake', default=False, 
        help='Runs a fake web server')
    parser.add_argument(
        '-testguide', action='store_true', dest='test_guide', default=False,
        help='Test guides')
    parser.add_argument(
        '-testnetwork', action='store_true', dest='test_network', default=False,
        help='Sends 100 images to YouTube')


    return parser.parse_args()

'''
def main1():
    from prefetching import pick

    pick()
#'''
    
def main():

    # Load command line arguments
    args = parse()

    # Check for valid service
    if not args.service.lower() in ['connectcast', 'youtube']:
        print("Streaming service {} not found".format(args.service))
        print("Exiting")
        return

    # Run stand-alone sets of code
    if args.timer:
        video.function_speeds(args.service)
        return 
    elif args.tester:
        video.test(args.service)
        return
    elif args.fake:
        fake = web.FakeWebServer()
        fake.start()
        fake.join()
        return
    elif args.test_guide:
        test = web.TestGuide()
        test.start()
        test.join()
        return
    elif args.test_network:
        image_queue = multiprocessing.Queue()
        kill_broadcaster = multiprocessing.Event()
        kill_Data2Frames = multiprocessing.Event()
        next_page_e = multiprocessing.Event()

        # Broadcater
        broadcaster = video.ffmpegHelper(
            image_queue, kill_broadcaster, args.service.lower(), 
            next_page_e, [False])
        broadcaster.start()
        
        # Data to video
        data2frames = video.RawFrames(
             image_queue, kill_Data2Frames)
        data2frames.start()

        while(1):
            var = input("Press q to quit:\n")
            if var.lower().startswith('q'):
                print("Got End Signal!")
                kill_broadcaster.set()                
                kill_Data2Frames.set()
                return

    # Load config parameters
    config.load_config('config/config-server')

    # Create kill events
    kill_WebServer = multiprocessing.Event() 
    kill_broadcaster = multiprocessing.Event()
    kill_Data2Frames = multiprocessing.Event()

    # Set next_page event
    next_page_e = multiprocessing.Event()
    next_page_e.set()

    rec_queue = None
    
    try:
        # Compile all branching variables
        flags = (args.skip_vid, args.skip_guide, rec_queue)

        packet_queue = multiprocessing.Queue()
        image_queue = multiprocessing.Queue()
        
        # Web Server
        webserver = web.WebServer(
            packet_queue, kill_WebServer, next_page_e, flags)
        webserver.start()
    
        # Broadcater
        broadcaster = video.ffmpegHelper(
            image_queue, kill_broadcaster, args.service.lower(), 
            next_page_e, flags)
        broadcaster.start()
        
        # Data to video
        data2frames = video.Data2Frames(
             packet_queue, image_queue,
            kill_Data2Frames, args.service.lower(), flags)
        data2frames.start()

        while(1):
            var = input("Press q to quit:\n")
            if var.lower().startswith('q'):
                print("Got End Signal!")
                kill_WebServer.set()
                kill_broadcaster.set()                
                kill_Data2Frames.set()
                if rec_queue:
                    rec_queue.put(None)
                break

    except Exception as e:
        print("Caught error in server.py")
        print(e)
        traceback.print_tb(sys.exc_info()[2])
        kill_WebServer.set()
        kill_broadcaster.set()
        kill_Data2Frames.set()

        if rec_queue:
            rec_queue.put(None)

    '''
    webserver.join()
    broadcaster.join()
    data2frames.join()
    '''
    
    return
     
    
if __name__ == '__main__':
    #main1()
    main()
