from bitstring import BitArray
import cv2
import datetime
import multiprocessing
import os
import reedsolo
import sys
import time
import traceback
if os.name != "posix":
    import win32event
  
from . import modulate
from . import parameters
from .video_helper_functions import *

# Skips the ECC data
# NOT CURRENTLY USED
def skip_ecc(data, enSize):
    ret = []
    while len(data) > 255:
        temp = data[:255-enSize]
        data = data[255:]
        ret.extend(temp)
    if len(data) != 0:
        ret.extend(data[:-enSize])
    return ret

# Turns the frames into data
# Should probably be renamed
class Data2Responses(multiprocessing.Process):
    def __init__(self, input_q, output_q, kill_e, service, flags):
        multiprocessing.Process.__init__(self)
        
        self.input_q = input_q
        self.output_q = output_q
        self.kill_e = kill_e
        self.service = service
        self.rec_queue = flags[2]
        self.skip_browser = flags[4]

        
    def _end(self):
        print("Data2Responses ending...")
        
        # empty the input queue
        while not self.kill_e.is_set():
            try:
                self.input_q.get(block=False)
            except:
                pass
                
        print("Data2Responses ended")
    
    
    def _load_preferences(self):
        self.width = parameters.get_width()
        self.height = parameters.get_height(self.service)
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
      
      
    def run(self):        
        
        # load preferences from where ever
        self._load_preferences()
        
        if self.encoding == "rs":
            rs = reedsolo.RSCodec(self.enSize)
            
        # A bunch of variables
        # TODO: Fix hardcoded
        len_size = 4
        data = b''
        length = None
        tot_size = 0 
        imgNum = 0
        
        try:
            while not self.kill_e.is_set():
                
                # if there's a frame in the queue
                if not self.input_q.empty():
                    
                    # load the image
                    image = self.input_q.get()
                    
                    # demodulate the image
                    try:
                        dataOutList, new_frame, index, _, _, size = modulate.img2data(
                            image, self.width, self.height, self.bucket, 
                            self.q, self.metaDataSize, self.metaDataOffset,
                            self.enSize, self.modulation_type)
                    except Exception as e:
                        print("Problem with demodulation")
                        print("Saving as 'ERROR.png'")
                        cv2.imwrite("ERROR.png", image)
                        print(e)
                        traceback.print_tb(sys.exc_info()[2])
                        break
                        
                    # if we're recording data
                    if self.rec_queue:
                        tot_size += size
                        self.rec_queue.put(["general","{}: Index:{} Size:{} Total Sizes:{}\n".format(time.strftime("%m/%d/%y %H:%M:%S"),index,size,tot_size)])
                    
                    # check if the demodulation screwed up
                    if dataOutList == []:
                        print("Empty demodulation")
                        break
                        
                    ## hey, what time is it?
                    now = datetime.datetime.now()
                    print('(F2D)', index, now.strftime("%H:%M:%S.%f"))
                    
                    if new_frame and imgNum not in [index, index + 1]:
                        print("(F2D) Updating index num\n\tFrom {} to {}".format(imgNum, index))
                        imgNum = index
                    
                    # if it's the expected index
                    if index == imgNum:
                        #messageBytes = BitArray(bin="".join(str(d) for d in dataOutList[:len(dataOutList)/8*8])).bytes
                        messageBytes = BitArray(bin="".join(str(d) for d in dataOutList)).bytes
                        data += messageBytes
                        imgNum += 1
                        
                    # if it's a repeat index
                    # this should have been caught earlier
                    elif index < imgNum:
                        print("(F2D) Repeat image {}".format(index))
                        continue
                        
                    # if we missed an index
                    elif index > imgNum:
                        print("XXX Missed an image XXX")
                        continue
                        # TODO: handle...
                        
                
                if data:
                    response = bytearray(data)
                    
                    # if we're using a WebClient, put the data on the queue
                    if not self.skip_browser:
                        self.output_q.put((new_frame, response))
                        
                    # if we're not using a WebClient, just print it
                    else:
                        print(response)
                        
                    data = b''
                
            self._end()
            return 
            
        except Exception as e:
            print("Found a problem in Data2Responses")
            print(e)
            traceback.print_tb(sys.exc_info()[2])
            self._end()
            

class RawResponses(Data2Responses):

    def __init__(self, input_q, kill_e):
        output_q = multiprocessing.Queue()

        Data2Responses.__init__(
            self, input_q, output_q, kill_e, 'youtube', 
            [None, None, None, False, False])

    def run(self):
        import random
        
        num = 100

        self._load_preferences()
        count = 0

        SIZE = int((self.width/self.bucket)*(self.height/self.bucket)*self.q*3-(self.metaDataSize+8*self.enSize))

        good = 0

        while not self.kill_e.is_set():
            
            if not self.input_q.empty():
                
                image = self.input_q.get()

                try:
                    dataOutList, new_frame, index, _, _, size = modulate.img2data(
                        image, self.width, self.height, self.bucket, 
                        self.q, self.metaDataSize, self.metaDataOffset,
                        self.enSize, self.modulation_type)
                except Exception as e:
                    print(e)

                if index > num-1:
                    continue

                count += 1
                    
                print("\tRAW: {}".format(index))

                random.seed(index)
                messageBytes = BitArray(bin="".join(str(d) for d in dataOutList)).bytes
                for byte in messageBytes:
                    if byte == random.randint(0,255):
                        good += 1

        print("Count: {}".format(count))
        print("Good: {}".format(good))    
        print("Total: {}".format(int(SIZE/8*num)))    
        print("Percent: {}".format(good/(SIZE/8*num)*100))    

                
                
