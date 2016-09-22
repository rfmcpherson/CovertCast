from bitstring import BitArray
from ctypes import *
import cv2
import datetime
import multiprocessing
import numpy as np
import os
from PIL import Image
import reedsolo
import sys
import time
import traceback
if os.name != "posix":
    import win32event

from . import modulate
from . import parameters
from . import video_helper_functions as vhf
    
# Reads screenshots from a C program and extracts the frames
# Can also read from saved images
class Vid2Frames(multiprocessing.Process):

    def __init__(self, output_q, kill_e, service, flags):
        multiprocessing.Process.__init__(self)
        
        self.output_q = output_q
        self.kill_e = kill_e
        self.service = service
        self.skip_vid = flags[0]
        self.rec_queue = flags[2]
        self.record_delay = flags[3]
        
        self.seen = []
        
        self.test_results = []
        
        # cv2.CV_LOAD_IMAGE_UNCHANGED don't seem to have been ported
        self.CV_LOAD_IMAGE_UNCHANGED = -1
        
    def _load_video_parameters(self):
        self.width = parameters.get_width()
        self.height = parameters.get_height(self.service)
        self.q = parameters.get_q()
        self.bucket = parameters.get_bucket()
        self.metaDataSize = parameters.get_metaDataSize()
        self.metaDataOffset = parameters.get_metaDataOffset() 
        if parameters.get_encoding() == "rs":
            self.enSize = parameters.get_enSize()
        else:
            self.enSize = 0
        self.modulation_type = parameters.get_modulation_type()
        
    # Sets some variables for interacting with the C program
    def _set_c_variables(self):
        # Some C variables
        self.FILE_MAP_ALL_ACCESS = 0xF001F
        self.INVALID_HANDLE_VALUE = 0xFFFFFFFF
        FALSE = 0
        #TRUE = 1
        #SHMEMSIZE = 1200
        self.szName = c_char_p(b"ImageMap")
        
        # win/python event handlers
        self.serverEventHandle = win32event.CreateEvent(None, 0, 0, "ServerEvent")
        self.clientEventHandle = win32event.CreateEvent(None, 0, 0, "ClientEvent")


    # Finds the image size/location by measuring a white frame from  
    #   either the video or a saved image
    def _calculate_image_size(self):

        while not self.kill_e.is_set():
            
            # if reading from video
            if not self.skip_vid:
            
                # wait for signal to read
                out = win32event.WaitForSingleObject(self.serverEventHandle, 1000)
                if out == win32event.WAIT_TIMEOUT:
                    continue

                # try to read from file mapping
                hMapObject = windll.kernel32.OpenFileMappingA(
                    self.FILE_MAP_ALL_ACCESS, 0, self.szName)
                if (hMapObject == 0):
                    print("Could not open file mapping object")
                    raise WinError()
                pBuf = windll.kernel32.MapViewOfFile(
                    hMapObject, self.FILE_MAP_ALL_ACCESS, 0, 0, 0)
                if (pBuf == 0):
                    print("Could not map view of file")
                    raise WinError()
                else:
                    pBuf_str = cast(pBuf, c_char_p)
                    pBuf_bytes = (c_ubyte * 10000000).from_address(pBuf)

                # copy data to np array
                np_bytes = np.copy(np.frombuffer(pBuf_bytes, np.uint8))
                
                # set "client done" event and clear buffer
                win32event.SetEvent(self.clientEventHandle)
                windll.kernel32.UnmapViewOfFile(pBuf)
                windll.kernel32.CloseHandle(hMapObject)
                
                # load np array to cv2 image
                white = cv2.imdecode(np_bytes, self.CV_LOAD_IMAGE_UNCHANGED)
                
                # try to get coordinates
                try:
                    top, bottom, left, right = vhf.image_dem_old2(white)
                    #top, bottom, left, right = vhf.image_dem(white)
                    return [top, bottom, left, right]
                except Exception as e:
                    print(e)
                    traceback.print_tb(sys.exc_info()[2])
                    break
                if top == -1 or bottom == -1 or left == -1 or right == -1:
                    print("Dimensions Failed!")
                    continue
            else:
                # hard coded for connectcast
                white = cv2.imread("C:\\Users\\richard\\svn\\voip\\RGB\\white.png")
                top, bottom, left, right = vhf.image_dem(white)
                return [top, bottom, left, right]

        
        return None

        
    def run(self):        

        # load the parameters from where ever
        self._load_video_parameters()
        
        # set c variables
        self._set_c_variables()

        # expected image number for each message
        imgNum = 0
        
        last_num = 0
        missing = 0
        
        # find the image size and location
        try:
            ret = self._calculate_image_size()
        except Exception as e:
            print(e)
            traceback.print_tb(sys.exc_info()[2])
            return

        if ret:
            top, bottom, left, right = ret
        else:
            print("Problem with calculating image location")
            return
            
        # loop reading the images
        while not self.kill_e.is_set():  
            try:  
                # if we're reading from the video
                if not self.skip_vid:
                
                    # wait for signal to read
                    out = win32event.WaitForSingleObject(
                        self.serverEventHandle, 1000)
                    if out == win32event.WAIT_TIMEOUT:
                        continue
        
                    # try to read from file mapping
                    hMapObject = windll.kernel32.OpenFileMappingA(
                        self.FILE_MAP_ALL_ACCESS, 0, self.szName)
                    if (hMapObject == 0):
                        print("Could not open file mapping object")
                        raise WinError()
                    pBuf = windll.kernel32.MapViewOfFile(
                        hMapObject, self.FILE_MAP_ALL_ACCESS, 0, 0, 0)
                    if (pBuf == 0):
                        print("Could not map view of file")
                        raise WinError()
                    else:
                        pBuf_str = cast(pBuf, c_char_p)
                        pBuf_bytes = (c_ubyte * 10000000).from_address(pBuf)
                    
                    # copy data to np array
                    np_bytes = np.copy(np.frombuffer(pBuf_bytes, np.uint8))

                    # set "client done" event and clear buffers
                    win32event.SetEvent(self.clientEventHandle)
                    windll.kernel32.UnmapViewOfFile(pBuf)
                    windll.kernel32.CloseHandle(hMapObject)
        
                    # load np array to cv2 image
                    image = cv2.imdecode(np_bytes, self.CV_LOAD_IMAGE_UNCHANGED)
                
                # if reading from disk
                else:
                    f_name = "C:\\Users\\richard\\svn\\voip\\RGB\\im{}.png".format(imgNum)
                    if os.path.isfile(f_name):
                        image = cv2.imread(f_name)
                    else:
                        image = cv2.imread("C:\\Users\\richard\\svn\\voip\\RGB\\white.png")
                        
                if vhf.isWhite(image[top:bottom, left:right]):
                    #cv2.imwrite("white.png", image[top:bottom, left:right])
                    continue
                        
                # if we just want to measure streaming delay
                if 0 and self.record_delay:
                    now = datetime.datetime.now()
                    time_str = now.strftime("%H:%M:%S.%f")
                    print("First image at {}".format(time_str))
                    return
                
                # crop and resize image
                image = image[top:bottom, left:right]
                resized_image = cv2.resize(image,(self.width, self.height))
                #cv2.imwrite("resized.png", resized_image)
               
                # demodulate metadata
                new_frame, index, _, _ = modulate.img2meta(
                    resized_image, self.width, self.height, self.bucket,
                    self.q, self.metaDataSize, self.metaDataOffset, 
                    self.enSize, self.modulation_type)
                
                # hey, what time is it?
                #now = datetime.datetime.now()
                #print(index, now.strftime("%H:%M:%S.%f"))
                
                if 0:
                    if index not in self.seen:
                        now = datetime.datetime.now()
                        print(index, '(V2F)', now.strftime("%H:%M:%S.%f"))
                        self.seen.append(index)
                        self.output_q.put(resized_image)
                    continue

                if last_num != index:
                    missing += index-last_num-1
                    
                
                    
                # if we missed an image
                if index != imgNum:

                    # if we can catch up, do it
                    if new_frame and imgNum != index + 1:
                        print("Found new_frame (V2F)\n\t Updating imgNum from {} to {}".format(imgNum, index))
                        imgNum = index

                    # missed an image
                    if index > imgNum:
                        if index != last_num:
                            print("Bad index (V2F)\n\t Have {}, Want {}, Missing {}".format(index, imgNum, missing))
                            now = datetime.datetime.now()
                            print('\t', now.strftime("%H:%M:%S.%f"))
                        
                        if 0:
                            if(self.modulation_type.startswith("square_YUV")):
                                temp_image = Image.fromarray(resized_image, mode="YCbCr")
                                temp_image = temp_image.convert("YCbCr")
                                temp_image.save("wrong.jpg","JPEG",quality=100)
                            else:
                                cv2.imwrite("wrong.jpg", resized_image)
                    
                        last_num = index
                        continue
                        
                    # repeated image
                    if index == imgNum-1:
                        continue
                
                last_num = index
                
                # hey, what time is it?
                if new_frame:
                    if not self.test_results:
                        last_time = datetime.datetime.now()
                    self.test_results.append(last_time.strftime("%H:%M:%S.%f"))
                    print('Results: {}'.format(self.test_results))
                last_time = datetime.datetime.now()
                print(index, '(V2F)', missing, last_time.strftime("%H:%M:%S.%f"))
                imgNum += 1

                '''
                # if we need to record
                if self.rec_queue:
                    self.rec_queue.put(["general","{}: Image:{} White Count:{}\n".format(time.strftime("%m/%d/%y %H:%M:%S"), imgNum, white_count)])
                '''
                
                # pass the image frame along
                # unresized image works a little better for youtube
                if self.service == "youtube":
                    self.output_q.put(resized_image)
                else:
                    self.output_q.put(resized_image)
                
            except Exception as e:
                print("Error in Vid2Data!")
                print(e)
                traceback.print_tb(sys.exc_info()[2])
                return
           

# Debugging class to save a set of images           
class Save_Images(multiprocessing.Process):
  def __init__(self, input_q):
    multiprocessing.Process.__init__(self)
    self.input_q = input_q
  
  def run(self):
    i = 0
    while(1):
      image = self.input_q.get()
      cv2.imwrite("images/{}.png".format(i),image)
      i += 1
      

# Run Vid2Frame but save the images locally      
if __name__ == '__main__':

    input_q = multiprocessing.Queue()
    containerImg2 = "C:\\Users\\richard\\svn\\win\\client-read\\"
    
    #dec = Data2Responses(in_queue, out_queue)
    dec = Save_Images(input_q)
    dec.start()
    
    kill = multiprocessing.Event()
    send = multiprocessing.Event()
    vid = Vid2Frames(
        input_q, kill, "youtube"
        (False, False, None, False))
    vid.start()
    
    try:
        vid.join()
    except:
        pass
    dec.kill()
    
