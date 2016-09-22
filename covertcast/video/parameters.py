width = 1280-16#768-16#1280-16

height_cc = 720-16
start_height_cc = 0

height_yt = 720 - 16
start_height_yt = 8

base_height = 720
base_width = 1280

q=2 # data byte size
bucket=8 # num of pixels for each byte
metaDataSize = 40  # in bits. Breakdown as follows:
# 1 for last 
# 7 for index 
# X for offset 
# 3 for bitoffset
# metaData is index, last data len, bit offset

metaDataOffset = 17
enSize = 16
numBytesFilename=50
modulation_type="square_RGB"
encoding=None #"rs"
wait_time = 1.4
#wait_time = 0.01

frame_time_cc = 0.2
frame_time_yt = 0.5

def get_width():
  return width

def get_height(service="youtube"): 
  if service == "connectcast":
    return height_cc
  elif service == "youtube":
    return height_yt
  else:
    print("Bad service specified in get_height")
    return None
    
def get_start_height(service="youtube"):
  if service == "connectcast":
    return start_height_cc
  elif service == "youtube":
    return start_height_yt
  else:
    print("Bad service specified in get_start_height")
    return None
        
def get_base_width():
  return base_width

def get_base_height():
  return base_height

def get_q(): 
  return q

def get_bucket():
  return bucket

def get_metaDataSize():
  return metaDataSize

def get_metaDataOffset():
  return metaDataOffset

def get_rsSize():
  return enSize
    
def get_enSize():
  return enSize

def get_numBytesFilename():
  return numBytesFilename

def get_modulation_type():
  return modulation_type

def get_encoding():
  return encoding
    
def get_wait_time():
  return wait_time
    
def get_frame_time(service="youtube"):
  if service == "connectcast":
    return frame_time_cc
  elif service == "youtube":
    return frame_time_yt
  else:
    print("Bad service specified in get_frame_time")
    return None
