# This is a simple test script to check that validity of one
# image. Most of the code is from test.py, so the comments may be a
# bit off...


import cv2
import sys
import datetime
import random
import Image
import reedsolo
from Queue import Queue

import modulate
from video_helper_functions import *
import parameters
import functions

def print_it(message_bits, width, height, bucket, q, metaDataSize, metaDataOffset, modulation_type):
  print ""
  print "Width (px):        ", width
  print "Height (px):       ", height
  print "Message Size (b):  ", len(message_bits)
  print "Metadata Size (b): ", metaDataSize
  print "Metadata Offset(b):", metaDataOffset


service = "youtube"
  
width = parameters.get_width()
height = parameters.get_height(service)
start_height = parameters.get_start_height(service)
q = parameters.get_q()
bucket = parameters.get_bucket()
metaDataSize = parameters.get_metaDataSize()
metaDataOffset = parameters.get_metaDataOffset()
rsSize = parameters.get_rsSize()
numBytesFilename = parameters.get_numBytesFilename()
modulation_type = parameters.get_modulation_type()
wait_time = parameters.get_wait_time()

def validate(input):
  '''
  print "************************"
  print "TESTING IMAGE VALIDITY"
  print "************************"
  '''

  # Get and save image
  images = []

  # Replace images[0] with loaded image to double check correctness
  image = cv2.imread(input)

  image = cv2.resize(image,(1264, 704))

  # Demodulate
  demes = functions.demodulate_Square_Color_Fast(image, width, height, bucket, q)

  return bit_array_2_bytes(demes)


if __name__ == "__main__":
  if(len(sys.argv) < 2):
    print "Needs the image name as argument!"
    quit()
  else:
    validate(sys.argv[1])
