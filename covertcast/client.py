import argparse
import multiprocessing
import sys
import traceback

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
        help='Skips sending the frames to video and loads them locally')
    parser.add_argument(
        '-skipaddon', action='store_true', dest='skip_addon', default=False, 
        help='Skips using the add-on and saves the requests to request.txt')
    parser.add_argument(
        '-skipbrowser', action='store_true', dest='skip_browser', default=False,
        help='Skips sending data to the client and just prints it'
    )
    parser.add_argument(
        '-delay', action='store_true', dest='record_delay', default=False, 
        help='Record time from request to first image')

    
    # Change major functionality (i.e. code flow)
    parser.add_argument(
        '-time', action='store_true', dest='timer', default=False, 
        help='Runs the timing functions on critical sections of the code')
    parser.add_argument(
        '-test', action='store_true', dest='tester', default=False, 
        help='Runs the simple tests we have')
    parser.add_argument(
        '-fake', action='store_true', dest='fake', default=False, 
        help='Runs a fake web client')
    parser.add_argument(
        '-imtest', action='store', dest='image_test', default=None, 
        help='Reads and decodes a given image')
    parser.add_argument(
        '-testnetwork', action='store_true', dest='test_network', default=False,
        help='Reads [supposed] 100 images from YouTube')

    return parser.parse_args()

    
def main():
    multiprocessing.freeze_support()
    
    # Load config stuff
    #config.load_config('config\config-client')

    # Load command line arguments
    args = parse()

    # Check for valid service
    if not args.service.lower() in ['connectcast', 'youtube']:
        print("Streaming service not found")
        print("Exiting")
        return

    # Run stand alone sets of code
    if args.timer:
        video.function_speeds(args.service)
        return 
    elif args.tester:
        video.test(args.service)
        return
    elif args.fake:
        fake = web.FakeWebClient()
        fake.start()
        fake.join()
        return
    elif args.image_test:
        video.image_test(args.service, args.image_test)
    elif args.test_network:
        image_q = multiprocessing.Queue()
        kill_Data2Responses = multiprocessing.Event()
        kill_Vid2Frames = multiprocessing.Event()

        data2responses = video.RawResponses(
            image_q, kill_Data2Responses)
        data2responses.start()
        
        video2frames = video.Vid2Frames(
            image_q, kill_Vid2Frames,
            args.service.lower(), [False, None, None, False])
        video2frames.start()

        while(1):
            var = input("Press q to quit:\n")
            if var.lower().startswith('q'):
                print("Got End Signal!")
                kill_Data2Responses.set()
                kill_Vid2Frames.set()
                return
    
    
    # Create kill events
    kill_WebClient = multiprocessing.Event()
    kill_Data2Responses = multiprocessing.Event()
    kill_Vid2Frames = multiprocessing.Event()
    
    rec_queue = None
    
    try:
        # Compile all branching flags
        flags = (
            args.skip_vid, args.skip_addon, rec_queue, 
            args.record_delay, args.skip_browser)

        data_q = web.AsyncProcessQueue() # Cleaned data
        image_q = multiprocessing.Queue() # Single, unique images

        # Takes raw data and interfaces with the client's browser
        if not args.skip_browser:
            webclient = web.WebClient(
                data_q, kill_WebClient, flags)
            webclient.start()
        
        # Takes invidual images and decodes them into raw data
        # sends the data to WebClient
        data2responses = video.Data2Responses(
            image_q, data_q, kill_Data2Responses,
            args.service, flags)
        data2responses.start()
        
        # Captures images and sends them to Data2Responses
        video2frames = video.Vid2Frames(
            image_q, kill_Vid2Frames,
            args.service.lower(), flags)
        video2frames.start()
    
        while(1):
            var = input("Press q to quit:\n")
            if var.lower().startswith('q'):
                print("Got End Signal!")
                kill_WebClient.set()
                kill_Data2Responses.set()
                kill_Vid2Frames.set()
                if rec_queue:
                    rec_queue.put(None)
                print("End events set")
                return
    
    except Exception as e:
        print("Caught error in client")
        print(e)
        traceback.print_tb(sys.exc_info()[2])
        kill_WebClient.set()
        kill_Data2Responses.set()
        kill_Vid2Frames.set()
        if rec_queue:
            rec_queue.put(None)
            

    
if __name__ == '__main__':
    main()
