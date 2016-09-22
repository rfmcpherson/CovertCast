# -*- coding: utf-8 -*-
"""
Created on Wed Jan 30 13:46:33 2013
modulates binary data into a video file
@author: amir
"""

import sys
from . import functions
import numpy as np
import cProfile

# Wraps img2data to measure timing
def data2imgsWrapper(data, width, height, start_height, bucket, q, 
        metaDataSize, metaDataOffset, enSize, modulation_type, imIndx):
    prof = cProfile.Profile()
    args = [data, width, height, start_height, bucket, q, 
        metaDataSize, metaDataOffset, enSize, modulation_type, imIndx]
    ret = prof.runcall(data2imgs, *args)
    prof.print_stats()
    return ret

# Converts raw data to images
def data2imgs(data, width, height, start_height, bucket, q, metaDataSize,
              metaDataOffset, enSize, modulation_type, imIndx, new_flag=False):
    """ 
    converts data block into an image using custom encoding.
    """
    
    from numpy import binary_repr, ceil
    from .video_helper_functions import reed, bit_array_2_bytes

    images = []
    
    # Everything but square_color is old and probably bad and slow
    if modulation_type in ["square_RGB", "square_YUV", "square_YUV2"]:
        imgSize=(width/bucket)*(height/bucket)*q*3 # num of data bits stored in one image
    else:
        raise Exception("Bad modulation type")

    if(0):
        print("Modulation Size (bits):", imgSize)
        print("Data Size (bits):", len(data))

    if( metaDataSize % 8 != 0):
        raise Exception("metaDataSize must be a multiple of 8")

    # Find size for actual data and number of frames
    # (keep in mind that we get a RS code for every 255 bytes)
    totMetaDataSize = metaDataSize + 8*enSize # (let's assume metadata < 255 bytes and a mult of 8)
    imgSizeData = imgSize - totMetaDataSize
    
    # Find size of last frame
    # clean up numbers
    # can probably drop the last three bits from lastDataLen
    bitOffset = 0
    lastDataLen = len(data)
    if(lastDataLen % 8 != 0):
      bitOffset = 8 - lastDataLen % 8
      lastDataLen = lastDataLen + bitOffset
    lastDataLenBin = binary_repr(lastDataLen, width=metaDataOffset)

    if(bitOffset == 8):
        bitOffset = 0
    bitOffsetBin = binary_repr(bitOffset, width=3)
    
    if(0):
        print("\n%%%%")
        print("len:", len(data))
        print("ImageSize:", imgSize )
        print("Per Frame:", imgSizeData)
        print("width:", metaDataSize-1)
        print("lastDataLen:", lastDataLen)
        print("%%%%\n")

    dataBits = []
    metaData = []        
    frameNum = binary_repr(imIndx, width=metaDataSize-metaDataOffset-3)
    
    # set first bit of frameNum to new_flag
    # TODO: less hacky way
    frameNum = str(int(new_flag)) + frameNum[1:]

    for j in range(len(frameNum)):
        metaData.append(int(frameNum[j]))
    for j in range(len(lastDataLenBin)):
        metaData.append(int(lastDataLenBin[j]))
    for j in range(len(bitOffsetBin)):
        metaData.append(int(bitOffsetBin[j]))
        
    # fill dataBits
    dataBits=data
    
    # make it a multiple of 8
    if(len(dataBits) % 8 != 0):
        dataBits = dataBits + [0]*(8-(len(dataBits)%8))
    
    # add reed to metaData
    if enSize != 0:
        dataBits = reed(metaData, enSize) + dataBits
    else:
        dataBits = metaData + dataBits

    if 0:
        print(bit_array_2_bytes(dataBits))
      
    # Everything but square_color is old and probably bad and slow
    if modulation_type=="square_RGB":
        imgRes=functions.modulate_Square_RGB(
            dataBits, width, height, start_height, bucket, q)
    elif modulation_type=="square_YUV":
        imgRes=functions.modulate_Square_YUV(
            dataBits, width, height, start_height, bucket, q)
    elif modulation_type=="square_YUV2":
        imgRes=functions.modulate_Square_YUV2(
            dataBits, width, height, start_height, bucket, q)
    else:
        raise Exception("modulation type not supported")

    return imgRes


# Wraps img2data to measure timing
def img2dataWrapper(image, width, height, bucket, q,
        metaDataSize, metaDataOffset, rsSize, modulation_type):
    prof = cProfile.Profile()
    args = [image, width, height, bucket, q, metaDataSize, metaDataOffset,
        rsSize, modulation_type]
    ret = prof.runcall(img2data, *args)
    prof.print_stats()
    return ret

    
# Converts images to raw data
def img2data(image,width,height,bucket,q,metaDataSize,metaDataOffset,enSize,modulation_type):
    """
    insert in blocks
    """
    from . import video_helper_functions as vhf
    import reedsolo
    
    if modulation_type=="square_RGB":
        dataOut = functions.demodulate_Square_RGB_Fast(
            image, width, height, bucket, q)
    elif modulation_type=="square_YUV":
        dataOut = functions.demodulate_Square_YUV_Fast(
            image, width, height, bucket, q)
    elif modulation_type=="square_YUV2":
        dataOut = functions.demodulate_Square_YUV_Fast2(
            image, width, height, bucket, q)
    else:
        raise Exception("modulation type not supported")
        
    # Get metadata
    totMetaDataSize = metaDataSize + 8*enSize
    metaData = dataOut[:totMetaDataSize]

    # Handle Reed-Solomon if needed
    # THIS MIGHT NOT WORK
    if enSize != 0:
        metaData = bytearray(vhf.bit_array_2_bytes(metaData))
        rs = reedsolo.RSCodec(enSize)
        metaData = vhf.bytes_2_bit_list(rs.decode(metaData))

    new_frame, index, offset, bitoffset = vhf.extract_metadata(metaData, metaDataOffset)
    
    if(0):
        print("\n%%%%")
        print("index", index)
        print("offset", offset)
        print("bitoffset", bitoffset)
        print("length", len(dataOut))
        print("metadata len", totMetaDataSize)
        print("%%%%\n")

    # cut up data
    message = dataOut[totMetaDataSize:totMetaDataSize+offset]
    size = totMetaDataSize + offset - bitoffset
    
    if 0:
        print(vhf.bit_array_2_bytes(dataOut[:totMetaDataSize+offset]))

    return message[:len(message)-bitoffset], new_frame, index, offset, bitoffset, size
    
# Converts images to raw data, but only gets the metadata
# A different function to allow quicker demodulation
def img2meta(image,width,height,bucket,q,metaDataSize,metaDataOffset,enSize,modulation_type):
    from . import video_helper_functions as vhf
    import reedsolo
    import sys
    import traceback
    
    try:
        totMetaDataSize = metaDataSize + 8*enSize
        
        if modulation_type=="square_RGB":
            dataOut = functions.demodulate_Square_RGB_Fast_Meta(
                image, width, height, bucket, 
                q, totMetaDataSize)
        elif modulation_type=="square_YUV":
            dataOut = functions.demodulate_Square_YUV_Fast_Meta(
                image, width, height, bucket, 
                q, totMetaDataSize)
        else:
            print("Unsupported img2meta modulation_type")

        # Get metadata
        metaData = dataOut[:totMetaDataSize]
        metaData = bytearray(vhf.bit_array_2_bytes(metaData))
        if enSize != 0:
            # Set up Reed-Solomon
            rs = reedsolo.RSCodec(enSize)
            metaData = vhf.bytes_2_bit_list(rs.decode(metaData))
        else:
            metaData = vhf.bytes_2_bit_list(metaData)
        new_frame, index, offset, bitoffset = vhf.extract_metadata(metaData,metaDataOffset)
        
        return new_frame, index, offset, bitoffset
    except Exception as e:
        import sys, traceback
        print("Exception in img2meta")
        print(e)
        print(traceback.print_tb(sys.exc_info()[2]))
    
# Test the modulation/demodulation
def test(service):

    import cv2
    import random 

    from . import parameters
    #from .servervideo import format_data
    from . import video_helper_functions as vhf
    
    # Get all the parameters
    width = parameters.get_width()
    height = parameters.get_height(service)
    start_height = parameters.get_start_height(service)
    q = parameters.get_q()
    bucket = parameters.get_bucket()
    metaDataSize = parameters.get_metaDataSize()
    metaDataOffset = parameters.get_metaDataOffset()
    enSize = parameters.get_enSize()
    enSize = 0
    modulation_type = parameters.get_modulation_type()

    # Size of one image
    #   total - metadata - encoding - length
    size = width/bucket*height/bucket*q*3 - metaDataSize - 8*enSize - 32

    # Create random buffer
    buf = []
    for i in range(int(size/8)):
        buf.append(random.randint(0,255))
    buf = bytearray(buf)

    # Encode the image
    buf = vhf.bytes_2_bit_list(buf)
    #buf = format_data(buf, 'youtube')

    image = data2imgs(
        buf, width, height, start_height, bucket, q, metaDataSize, 
        metaDataOffset, enSize, modulation_type, 0)
    image = image[start_height:start_height+height,8:8+width]
 
    # Save image
    cv2.imwrite("test.jpeg", image)
   
    # Decode the image 
    buf2, _, _, _, _ = img2data(
        image, width, height, bucket, q, metaDataSize, 
        metaDataOffset, enSize, modulation_type)

    return buf == buf2

def image_test(service, image_location):
    import cv2
    from . import parameters
    
    # Get all the parameters
    width = parameters.get_width()
    height = parameters.get_height(service)
    start_height = parameters.get_start_height(service)
    q = parameters.get_q()
    bucket = parameters.get_bucket()
    metaDataSize = parameters.get_metaDataSize()
    metaDataOffset = parameters.get_metaDataOffset()
    enSize = parameters.get_enSize()
    enSize = 0
    modulation_type = parameters.get_modulation_type()
    
    # load image
    image = cv2.imread(image_location)
    
    # decode image
    buf, _, _, _, _ = img2data(
        image, width, height, bucket, q, metaDataSize, 
        metaDataOffset, enSize, modulation_type)

    print("image data:")
    print(buf)
    
def modulation_speeds(service):
    import cv2
    from PIL import Image
    import random
    
    from . import parameters
    from . import video_helper_functions as vhf

    width = parameters.get_width()
    height = parameters.get_height(service)
    start_height = parameters.get_start_height(service)
    q = parameters.get_q()
    bucket = parameters.get_bucket()
    metaDataSize = parameters.get_metaDataSize()
    metaDataOffset = parameters.get_metaDataOffset()
    enSize = parameters.get_enSize()
    enSize = 0
    modulation_type = parameters.get_modulation_type()
    
    q=2

    # size of one image
    imgsize = width/bucket*height/bucket*q*3 - metaDataSize - 8*enSize - 32
    imgsize = int(imgsize)
    
    print("Image Size:", imgsize)
    
    # generate random buffer
    buf = []
    for i in range(int(imgsize/8)):
        #buf.append(random.randint(0,255))
        buf.append(0)
    buf = bytearray(buf)
    
    # encode the image
    buf = vhf.bytes_2_bit_list(buf)
    
    if 1:
        # run the profilers on RGB modulate
        print("RGB Modulate")
        for i in range(1):
            image = data2imgsWrapper(
                buf, width, height, start_height, bucket, q, metaDataSize,
                metaDataOffset, enSize, "square_RGB", 0)     
        
        # convert to PIL Image
        #    it's actually in BGR mode
        #    this isn't really needed, it's symmetric with the YUV below
        image = Image.fromarray(image, mode="RGB")
        #image.save("temp.jpg", "JPEG", quality=100)
        
        # read image
        image = np.asarray(image, dtype=np.uint8)
        
        # if we save it we need to convert back to BGR format
        #image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
        
        # crop image
        image = image[start_height:start_height+height, 8:8+width]
        
        # run the profilers on RGB demodulate
        print("RGB FastDemodulate")
        for i in range(1):
            out, _, _, _, _, _ = img2dataWrapper(
                image, width, height, bucket, q, metaDataSize, 
                metaDataOffset, enSize, "square_RGB")
            
        # check if the input/output matches
        print("RGB good:", out == buf)
        print()
        
    if 0:
        # run the profilers on YUV modulate
        print("YUV Modulate")
        for i in range(1):
            image = data2imgsWrapper(
                buf, width, height, start_height, bucket, q, metaDataSize,
                metaDataOffset, enSize, "square_YUV2", 0)
        
        # convert to YUV PIL Image (now in demodulate)
        #image = Image.fromarray(image, mode="YCbCr")
        #image.save("temp.jpg","JPEG", quality=100)
        
        # read image, convert back from/to YUV format (now in demodulate)
        #image = image.convert("YCbCr")
        #image = np.asarray(image, dtype=np.uint8)
        
        # crop
        image = image[start_height:start_height+height, 8:8+width]
        cv2.imwrite("temp.png", image)
        
        # run the profilers on YUV demodulate
        print("YUV Fast Demodulate")
        for i in range(1):
            out, _, _, _, _  = img2dataWrapper(
                image, width, height, bucket, q, metaDataSize, 
                metaDataOffset, enSize, "square_YUV2")
            
        # check if the input/output matches
        print("YUV good:", out == buf)
        print()

if __name__ == "__main__":
    print("use 'client -test'")
    #print(test("youtube"))
