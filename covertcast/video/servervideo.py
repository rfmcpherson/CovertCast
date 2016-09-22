import cProfile
import cv2
import datetime
import multiprocessing 
import numpy as np
from numpy import binary_repr
import os 
from PIL import Image
import queue
import signal
import subprocess
import time
import threading

from . import modulate
from . import parameters
from .video_helper_functions import *


class ffmpegHelper(multiprocessing.Process):
    def __init__(self, queue, kill_e, service, next_page_e, flags):
        multiprocessing.Process.__init__(self)
        self.image_queue = queue
        self.kill_e = kill_e
        self.service = service
        self.next_page_e = next_page_e
        self.skip_vid = flags[0]
        
        self.width = parameters.get_width()
        self.height = parameters.get_height(self.service)
        self.start_height = parameters.get_start_height(self.service)
        
        self.modulation_type = parameters.get_modulation_type()

        self.white_count = 0
        self.next_packet_count = 10

        self.count = 0
        
        # Make white image
        base_height = parameters.get_base_height()
        base_width = parameters.get_base_width()
        self.white = np.zeros((base_height, base_width, 3), np.uint8)
        start_width = 8
        cv2.rectangle(
          self.white, 
          (start_width, self.start_height),
          (self.width + start_width, self.height + self.start_height), 
          (255, 255, 255), 
          -1)
                
        self.timer = parameters.get_frame_time(self.service)

    def tick(self):
        if self.kill_e.is_set():
            return

        # schedule the next tick
        threading.Timer(self.timer,self.tick).start()

        temp = None
        try:

            # if we have data to send
            if not self.image_queue.empty():

                self.white_count = 0
                temp = self.image_queue.get()

                # if the data is YUV 
                if(self.modulation_type.startswith("square_YUV")):
                    temp = Image.fromarray(temp, mode="YCbCr")
                    temp.save("temp.jpg","JPEG",quality=100)
                    os.rename("temp.jpg","out.jpg")
                
                # if the data is RGB
                else:
                    cv2.imwrite("temp.jpg",temp)
                    os.rename("temp.jpg","out.jpg")

                now = datetime.datetime.now()
                print("Sent {} @ {}".format(self.count, now.strftime("%H:%M:%S.%f")))
                self.count += 1

            # no data to send, so use a white image
            else:
                # write the data
                temp = self.white
                cv2.imwrite("temp.jpg",temp)
                os.rename("temp.jpg","out.jpg")

                if self.white_count == 0:
                    now = datetime.datetime.now()
                    print("WHITE @ {}".format(now.strftime("%H:%M:%S.%f")))

                # update the count
                self.white_count += 1
                if self.white_count == self.next_packet_count:
                    self.next_page_e.set()

        except Exception as e:
            print("Temp didn't get fully written")
            print("Skipping this frame")
            print(e)

        
    def run(self):

        if not self.skip_vid:
            last = time.time()
            self.tick()
            while not self.kill_e.is_set():
                time.sleep(1)
        else:
            imIndex = 0
            white_count = 0

            self.next_page_e.set()

            while(not self.kill_e.is_set()):
                if not self.image_queue.empty():
                    white_count = 0

                    image = self.image_queue.get()

                    imgDir="/home/richard/svn/voip-cs/server-write/"
                    outFile="".join([imgDir,"im",str(imIndex),".jpg"])
                    
                    cv2.imwrite(outFile, image)
                    print("Wrote im" + str(imIndex))
                    imIndex += 1
                else:
                    white_count += 1
                    time.sleep(1)
                    if white_count == 3:
                        self.next_page_e.set()
 
        self.end()
        return
           
    def end(self):
        print("FFMPEG ended")
        return

        '''
        while(1):
            try:
                self.image_queue.get(True, 1)
            except:
                print("FFMPEG ended")
                return
        '''

class Data2Frames(multiprocessing.Process):
    """ 
    read from the queue and write it to the virtual webcam 
    """
    def __init__(self, in_queue, image_queue, kill_e, service, branches):
        multiprocessing.Process.__init__(self)
        self.daemon = True
        self.in_queue = in_queue
        self.image_queue = image_queue
        self.kill_e = kill_e
        self.buffer = []
        self.service = service
        self.skip_vid = branches[0]
        
        self.width = parameters.get_width()
        self.height = parameters.get_height(self.service)
        self.start_height = parameters.get_start_height(self.service)
        self.q = parameters.get_q()
        self.bucket = parameters.get_bucket()
        self.metaDataSize = parameters.get_metaDataSize()
        self.metaDataOffset = parameters.get_metaDataOffset()
        self.encoding = parameters.get_encoding()
        if self.encoding:
            self.enSize = parameters.get_enSize()
        else:
            self.enSize = 0
        self.modulation_type = parameters.get_modulation_type()

        self.SIZE = (self.width/self.bucket)*(self.height/self.bucket)*self.q*3-(self.metaDataSize+8*self.enSize)
        self.SIZE = int(self.SIZE)
        
        self.imIndex = 0


    def run(self):
        
        last = None
        start = True
        new_flag = True
        
        while True:
            if self.kill_e.is_set():
                self.end()
                return
            try:
                while len(self.buffer) < self.SIZE:

                    if self.kill_e.is_set():
                        self.end()
                        return

                    # If there's nothing in the queue, just go
                    try:
                        block_bytes = self.in_queue.get(False)
                    except queue.Empty:
                        break
                    except Exception as e:
                        print(e)

                    # Get the next object
                    block_bits = bytes_2_bit_list(block_bytes)
                    self.buffer.extend(block_bits)

                # If there's data in the buffer, send it
                if self.buffer:

                    # Remove desired data from buffer
                    if len(self.buffer) < self.SIZE:
                        data = self.buffer
                        self.buffer = []
                    else:
                        data = self.buffer[:self.SIZE]
                        self.buffer = self.buffer[self.SIZE:]

                    # Modulate
                    image = modulate.data2imgs(
                        data, self.width, self.height, self.start_height,
                        self.bucket, self.q, self.metaDataSize,
                        self.metaDataOffset, self.enSize, self.modulation_type,
                        self.imIndex, new_flag)

                    new_flag = False

                    if(self.modulation_type.startswith("square_YUV")):
                        self.image_queue.put(image)
                    else:                            
                        self.image_queue.put(image)
                    
                    #print("Sent", self.imIndex)
                    self.imIndex += 1
                
                # we have a break in the buffer, so we can mark the next frame
                # as new information
                else:
                    new_flag = True

            except KeyboardInterrupt:
                print("ERROR/INTERRUPT?")
                return

    def end(self):
        self.image_queue.cancel_join_thread()
        print("file2vid ended")
        return


# Send 100 images for network/bandwidth testing
class RawFrames(Data2Frames):

    def __init__(self, image_queue, kill_e):
        Data2Frames.__init__(self, None, image_queue, kill_e, 'youtube', [None])


    def run(self):
        import random

        num = 100

        while not self.kill_e.is_set(): 
            while self.imIndex < num:

                random.seed(self.imIndex)
                
                data_ints = []
                
                # make data
                for i in range(int(self.SIZE/8)):
                    data_ints.append(random.randint(0,255))

                data_bytes = bytes(data_ints)
                self.buffer = bytes_2_bit_list(data_bytes)
                
                image = modulate.data2imgs(
                    self.buffer, self.width, self.height, self.start_height,
                    self.bucket, self.q, self.metaDataSize,
                    self.metaDataOffset, self.enSize, self.modulation_type,
                    self.imIndex, False)
                
                self.image_queue.put(image)
                
                self.imIndex += 1

        else:
            self.image_queue.cancel_join_thread()
            print("RawFrames ended")
            return
            

if __name__ == '__main__':
  pass
