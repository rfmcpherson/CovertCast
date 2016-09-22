""" 
This file contains code to modulate and demodulate bits to images
Originally created by Amir and heavily modified by Richard
"""

"""
Wrappers for RGB speed profiles
"""
def modulate_Square_RGB_Wrapper(data, width, height, start_height, bucket, q):
    import cProfile

    prof = cProfile.Profile()
    args = [data, width, height, start_height, bucket, q]
    imgRes = prof.runcall(modulate_Square_RGB, *args)
    prof.print_stats()
    return imgRes
 
def demodulate_Square_RGB_Fast_Wrapper(image, width, height, bucket, q):
    import cProfile

    prof = cProfile.Profile()
    args = [image, width, height, bucket, q]
    dataOut = prof.runcall(demodulate_Square_RGB_Fast, *args)
    prof.print_stats()
    return dataOut
   
 
"""
RGB modulate and demodulation functions
"""

"""
Modulates data into an RGB image
data is an array of 0s and 1s.
returns an openCV image.
"""
def modulate_Square_RGB(data, width, height, start_height, bucket, q):

    import cv2
    import numpy as np
    
    # Hardcoded values
    channels=3
    Q= np.power(2,q)
    border = 16
    width_start = 8

    # Color values for each binary square
    # Picked through experience with YouTube's encoding
    bitmap = [[19,96],[160,241]]

    # Max size of data
    imgSize= ((width/bucket)*(height/bucket))*q*channels 
    if np.size(data)> imgSize:
        print("Data larger than max image size.")
        print("It is", np.size(data))
        print("It's supposed to be", imgSize)
        print("Seriously, how did this happen?")
        raise Exception("Data too large for frame")

    # Clear the image
    imageData=np.zeros((720,1280,channels),np.uint8)

    # Number of boxes in the input data
    numBoxes=int(np.ceil(np.size(data)/(q*channels*1.0))) 

    # Insert 0s at the end to make it multiple of q
    for nullBits in range(numBoxes*q*channels-np.size(data)):
        data.append(0)

    # Color each box
    for i in range(numBoxes):

        # Get the RGB colors
        # REQUIRED: q == 2
        try:
            blueValue  = bitmap[ data[i*q*channels]   ][ data[i*q*channels+1] ]
            greenValue = bitmap[ data[i*q*channels+2] ][ data[i*q*channels+3] ]
            redValue   = bitmap[ data[i*q*channels+4] ][ data[i*q*channels+5] ]
        except Exception as e:
            print(i*q*channels)
            print(e)
       
        # Get the box locations
        x_index = int(np.divide(i,(width/bucket))) #inner in np?
        y_index = int(np.mod(i,(width/bucket)))
        x_range= range(x_index*bucket+start_height,(x_index+1)*bucket+start_height)
        y_range= range(y_index*bucket+width_start,(y_index+1)*bucket+width_start)

        # Color the box
        cv2.rectangle(imageData,
                      (y_range[0], x_range[0]),
                      (y_range[-1], x_range[-1]),
                      (redValue, greenValue, blueValue),
                      -1)
        
    return imageData

"""
Slower demodulation of RGB images to binary data
"""
def demodulate_Square_RGB(image,width,height,bucket,q):
    import numpy as np
    from operator import add

    # Hard coded values
    no_of_bits=8
    Q= np.power(2,q)
    channels = 3
    denom = np.power(2,no_of_bits)/Q
    boxSize = bucket*bucket

    dataOut=[]
    numBoxes= (width/bucket)*(height/bucket)

    # For every color box
    for byte in range(numBoxes):

        # Get the box size
        x_index = np.divide(byte,(width/bucket))
        y_index = np.mod(byte,(width/bucket))
        x_range= range(x_index*bucket,(x_index+1)*bucket)
        y_range= range(y_index*bucket,(y_index+1)*bucket)

        # Sum up the color values
        value = [0, 0, 0]
        for x in x_range:
            for y in y_range:
                pixel = image[x,y]
                value[0] += pixel[0]
                value[1] += pixel[1]
                value[2] += pixel[2]

        # Get the average color values for the box
        dblueByte = np.binary_repr(np.around(np.divide(value[0],np.multiply(boxSize,denom))-0.5)).zfill(q)
        dgreenByte = np.binary_repr(np.around(np.divide(value[1],np.multiply(boxSize,denom))-0.5)).zfill(q)
        dredByte = np.binary_repr(np.around(np.divide(value[2],np.multiply(boxSize,denom))-0.5)).zfill(q)
        
        # Append the values to the output list
        for t in range(q):
            dataOut.append(int(dredByte[t]))
        for t in range(q):
            dataOut.append(int(dgreenByte[t]))
        for t in range(q):
            dataOut.append(int(dblueByte[t]))
    
    return dataOut            


"""
Fast demodulation of RGB images to binary data
"""
def demodulate_Square_RGB_Fast(image,width,height,bucket,q):
    import numpy as np
    import cv2

    # Hardcoded parameters
    no_of_bits=8
    Q= np.power(2,q)
    channels = 3
    denom = np.power(2,no_of_bits)/Q
    boxSize = bucket*bucket
    four_denom = 4 * denom
    
    # Image to numpy array
    image = np.asarray(image[:,:])[:,:,:]
    
    dataOut=[]
    numBoxes= int((width/bucket)*(height/bucket))

    # Helpful computations used in the loop
    width_bucket = width/bucket
    #v1 = 64*9 
    #v2 = 128*9 
    #v3 = 192*9 
    v1 = 64*4 
    v2 = 128*4 
    v3 = 192*4 

    # For each box
    for byte in range(numBoxes):

        # Get the location of the box
        x_index = int(byte/width_bucket)
        y_index = int(byte%width_bucket) # is numpy faster?
        x_temp = int(x_index*bucket+bucket/2-1)
        y_temp = int(y_index*bucket+bucket/2-1)

        # Get an inner 2x2 set of pixels in the box
        #value = cv2.sumElems(image[x_temp-1:x_temp+2,y_temp-1:y_temp+2])
        value = cv2.sumElems(image[x_temp:x_temp+2,y_temp:y_temp+2])

        # Find the binary values for each color
        if value[2] < v1:
            dataOut.extend([0,0])
        elif value[2] < v2:
            dataOut.extend([0,1])
        elif value[2] < v3:
            dataOut.extend([1,0])
        else:
            dataOut.extend([1,1])
            
        if value[1] < v1:
            dataOut.extend([0,0])
        elif value[1] < v2:
            dataOut.extend([0,1])
        elif value[1] < v3:
            dataOut.extend([1,0])
        else:
            dataOut.extend([1,1])
            
        if value[0] < v1:
            dataOut.extend([0,0])
        elif value[0] < v2:
            dataOut.extend([0,1])
        elif value[0] < v3:
            dataOut.extend([1,0])
        else:
            dataOut.extend([1,1])

    return dataOut            


"""
Demodulate RGB images to metadata
This function just pulls out the metadata 
and does not demodulate the whole thing
"""
def demodulate_Square_RGB_Fast_Meta(image,width,height,bucket,q,totMetaDataSize):

    import numpy as np
    import cv2

    # Hardcoded parameters
    no_of_bits=8
    Q= np.power(2,q)
    channels = 3
    denom = np.power(2,no_of_bits)/Q
    boxSize = bucket*bucket
    four_denom = 4 * denom
    
    # Image to numpy array
    image = np.asarray(image[:,:])[:,:,:]

    
    dataOut=[]
    numBoxes= int((width/bucket)*(height/bucket))
    width_bucket = width/bucket
    
    # For each box
    for byte in range(numBoxes):

        # Get the location of the box
        x_index = int(byte/width_bucket)
        y_index = int(byte%width_bucket) # is numpy faster?
        x_temp = int(x_index*bucket+bucket/2-1)
        y_temp = int(y_index*bucket+bucket/2-1)

        # Get an inner 2x2 set of pixels
        value = cv2.sumElems(image[x_temp:x_temp+2,y_temp:y_temp+2])
        
        # Find the binary values for each color
        if value[2] < 256:
            dataOut.extend([0,0])
        elif value[2] < 512:
            dataOut.extend([0,1])
        elif value[2] < 768:
            dataOut.extend([1,0])
        else:
            dataOut.extend([1,1])
            
        if value[1] < 256:
            dataOut.extend([0,0])
        elif value[1] < 512:
            dataOut.extend([0,1])
        elif value[1] < 768:
            dataOut.extend([1,0])
        else:
            dataOut.extend([1,1])
            
        if value[0] < 256:
            dataOut.extend([0,0])
        elif value[0] < 512:
            dataOut.extend([0,1])
        elif value[0] < 768:
            dataOut.extend([1,0])
        else:
            dataOut.extend([1,1])
            
        # Stop when we've hit the end of the metadata
        if len(dataOut) >= totMetaDataSize:
            break
            
    return dataOut            


"""
YUV modulation and demodulation functions
"""


"""
Wrappers for YUV speed profiles
"""
def modulate_Square_YUV_Wrapper(data, width, height, start_height, bucket, q):
    import cProfile

    prof = cProfile.Profile()
    args = [data, width, height, start_height, bucket, q]
    imgRes = prof.runcall(modulate_Square_YUV, *args)
    prof.print_stats()
    return imgRes
 
def demodulate_Square_YUV_Fast_Wrapper(image, width, height, bucket, q):
    import cProfile

    prof = cProfile.Profile()
    args = [image, width, height, bucket, q]
    dataOut = prof.runcall(demodulate_Square_YUV_Fast, *args)
    prof.print_stats()
    return dataOut


"""
Modulates data into a YUV image
data is an array of 0s and 1s.
returns an openCV image.
"""
def modulate_Square_YUV(data,width,height,start_height,bucket,q):
    import cv2
    import numpy as np

    # Hardcoded values
    channels=3
    Q= np.power(2,q)
    border = 16
    width_start = 8

    # Color values for each binary pair
    bitmap = [[32,96],[160,224]]

    # Max size of data
    imgSize= ((width/bucket)*(height/bucket))*q*channels 

    if np.size(data)> imgSize:
        print("Data larger than max image size.")
        print("It is", np.size(data))
        print("It's supposed to be", imgSize)
        print("Seriously, how did this happen?")
        raise Exception("Data too large for frame")
    
    # Clear the image
    #imageData=np.zeros((720,1280,channels),np.uint8)
    black = [16, 128, 128]
    imageData = np.tile(np.array(black, dtype=np.uint8), (720, 1280, 1))

    # Number of boxes in the input data
    numBoxes=int(np.ceil(np.size(data)/(q*channels*1.0))) 

    # Insert 0s at the end to make it multiple of q
    for nullBits in range(numBoxes*q*channels-np.size(data)):
        data.append(0)

    print(data[:15])
        
    # For each box, create the colors
    for i in range(numBoxes):
        
        # Get the RGB colors
        # REQUIRED: q == 2
        try:
            blueValue  = bitmap[ data[i*q*channels]   ][ data[i*q*channels+1] ]
            greenValue = bitmap[ data[i*q*channels+2] ][ data[i*q*channels+3] ]
            redValue   = bitmap[ data[i*q*channels+4] ][ data[i*q*channels+5] ]
        except Exception as e:
            print(i*q*channels)
            print(e)
            
        if i < 10:
            print(blueValue, greenValue, redValue)
            
        # Find the box location
        x_index = int(np.divide(i,(width/bucket))) #inner in np?
        y_index = int(np.mod(i,(width/bucket)))
        x_range= range(x_index*bucket+start_height,(x_index+1)*bucket+start_height)
        y_range= range(y_index*bucket+width_start,(y_index+1)*bucket+width_start)

        # Color the box 
        cv2.rectangle(imageData,
                      (y_range[0], x_range[0]),
                      (y_range[-1], x_range[-1]),
                      (redValue, greenValue, blueValue),
                      -1)
    
    return imageData

"""
Fast demodulation of YUV images to binary data
"""
def demodulate_Square_YUV_Fast(image,width,height,bucket,q):

    import cv2
    from PIL import Image
    import numpy as np
    
    # Hardcoded parameters
    no_of_bits=8
    Q= np.power(2,q)
    channels = 3
    denom = np.power(2,no_of_bits)/Q
    boxSize = bucket*bucket
    four_denom = 4 * denom
    
    # convert image to YUV
    image = Image.fromarray(image, mode="YCbCr")
    image = image.convert("YCbCr")
    #image = np.asarray(image, dtype=np.uint8)
    
    # Image to numpy array
    #image = np.asarray(image[:,:])[:,:,:]
    image = np.asarray(image, dtype=np.uint8)
    
    dataOut=[]
    numBoxes= int((width/bucket)*(height/bucket))

    # Helpful computations used in the loop
    width_bucket = width/bucket
    v1 = 64*9 
    v2 = 128*9 
    v3 = 192*9 

    # For each box
    for byte in range(numBoxes):

        # Get the location of the box
        x_index = int(byte/width_bucket)
        y_index = int(byte%width_bucket) # is numpy faster?
        x_temp = int(x_index*bucket+bucket/2-1)
        y_temp = int(y_index*bucket+bucket/2-1)

        # Get an inner set 3x3 pixels in the box
        value = cv2.sumElems(image[x_temp-1:x_temp+2,y_temp-1:y_temp+2])
        
        # find the binary values for each color
        if value[2] < v1:
            dataOut.extend([0,0])
        elif value[2] < v2:
            dataOut.extend([0,1])
        elif value[2] < v3:
            dataOut.extend([1,0])
        else:
            dataOut.extend([1,1])
            
        if value[1] < v1:
            dataOut.extend([0,0])
        elif value[1] < v2:
            dataOut.extend([0,1])
        elif value[1] < v3:
            dataOut.extend([1,0])
        else:
            dataOut.extend([1,1])
            
        if value[0] < v1:
            dataOut.extend([0,0])
        elif value[0] < v2:
            dataOut.extend([0,1])
        elif value[0] < v3:
            dataOut.extend([1,0])
        else:
            dataOut.extend([1,1])

    return dataOut
    
  
"""
Modulates data into a YUV image
data is an array of 0s and 1s
returns an openCV image
assumes q=3
"""  
def modulate_Square_YUV2(data,width,height,start_height,bucket,q):
    import cv2
    import numpy as np
    
    # Hardcoded values
    channels = 3
    Q = np.power(2,q)
    border = 16
    width_start = 8

    # Color values for each binary pair
    #bitmap = [[32,96],[160,224]]
    bitmap = [[[16, 48],   [80,  112]],
              [[144, 176], [208, 240]]]  
    
    # Max size of data
    imgSize= ((width/bucket)*(height/bucket))*q*channels 

    if np.size(data)> imgSize:
        print("Data larger than max image size.")
        print("It is", np.size(data))
        print("It's supposed to be", imgSize)
        print("Seriously, how did this happen?")
        raise Exception("Data too large for frame")
    
    # Clear the image
    #imageData=np.zeros((720,1280,channels),np.uint8)
    black = [16, 128, 128]
    #black = [0, 0, 0]
    imageData = np.tile(np.array(black, dtype=np.uint8), (720, 1280, 1))

    # Number of boxes in the input data
    numBoxes=int(np.ceil(np.size(data)/(q*channels*1.0))) 

    # Insert 0s at the end to make it multiple of q
    for nullBits in range(numBoxes*q*channels-np.size(data)):
        data.append(0)
        
    # For each box, create the colors
    for i in range(numBoxes):
        
        # Get the YUV colors
        # REQUIRED: q == 3
        try:
            Y_Value = bitmap[
                data[i*q*channels]][
                data[i*q*channels+1]][
                data[i*q*channels+2]]
            U_Value = bitmap[
                data[i*q*channels+3]][
                data[i*q*channels+4]][
                data[i*q*channels+5]]
            V_Value = bitmap[
                data[i*q*channels+6]][
                data[i*q*channels+7]][
                data[i*q*channels+8]]
        except Exception as e:
            print(i*q*channels)
            print(e)
            
        # Find the box location
        x_index = int(np.divide(i,(width/bucket))) #inner in np?
        y_index = int(np.mod(i,(width/bucket)))
        x_range= range(x_index*bucket+start_height,(x_index+1)*bucket+start_height)
        y_range= range(y_index*bucket+width_start,(y_index+1)*bucket+width_start)

        # Color the box 
        cv2.rectangle(imageData,
                      (y_range[0], x_range[0]),
                      (y_range[-1], x_range[-1]),
                      (Y_Value, U_Value, V_Value),
                      -1)
    
    return imageData

"""
Fast demodulation of YUV images to binary data
Assumes q=3
"""
def demodulate_Square_YUV_Fast2(image,width,height,bucket,q):

    import cv2
    from PIL import Image
    import numpy as np
    
    # Hardcoded parameters
    no_of_bits=8
    Q= np.power(2,q)
    channels = 3
    denom = np.power(2,no_of_bits)/Q
    boxSize = bucket*bucket
    four_denom = 4 * denom
    

    # convert image to YUV
    image = Image.fromarray(image, mode="YCbCr")
    image = image.convert("YCbCr")
    #image = np.asarray(image, dtype=np.uint8)
    
    # Image to numpy array
    #image = np.asarray(image[:,:])[:,:,:]
    image = np.asarray(image, dtype=np.uint8)
    
    dataOut=[]
    numBoxes= int((width/bucket)*(height/bucket))

    # Helpful computations used in the loop
    width_bucket = width/bucket
    v0 = 32*1*9 
    v1 = 32*2*9
    v2 = 32*3*9
    v3 = 32*4*9
    v4 = 32*5*9
    v5 = 32*6*9
    v6 = 32*7*9
    v7 = 32*8*9

    # For each box
    for byte in range(numBoxes):

        # Get the location of the box
        x_index = int(byte/width_bucket)
        y_index = int(byte%width_bucket) # is numpy faster?
        x_temp = int(x_index*bucket+bucket/2-1)
        y_temp = int(y_index*bucket+bucket/2-1)

        # Get an inner set 3x3 pixels in the box
        # n.b. value will be a 4-tuple (alpha channel)
        value = cv2.sumElems(image[x_temp-1:x_temp+2,y_temp-1:y_temp+2])
        
        for v in value[:3]:
            if v < v0:
                dataOut.extend([0,0,0])
            elif v < v1:
                dataOut.extend([0,0,1])
            elif v < v2:
                dataOut.extend([0,1,0])
            elif v < v3:
                dataOut.extend([0,1,1])
            elif v < v4:
                dataOut.extend([1,0,0])
            elif v < v5:
                dataOut.extend([1,0,1])
            elif v < v6:
                dataOut.extend([1,1,0])
            else:# v < v7:
                dataOut.extend([1,1,1])
           
    return dataOut

"""
Demodulate YUV images to metadata
This function just pulls out the metadata 
and does not demodulate the whole thing
"""
# CURRENLTY DOES NOTHING WITH YUV
def demodulate_Square_YUV_Fast_Meta(image,width,height,bucket,q,totMetaDataSize):

    import numpy as np
    import cv2

    # Hardcoded parameters
    no_of_bits=8
    Q= np.power(2,q)
    channels = 3
    denom = np.power(2,no_of_bits)/Q
    boxSize = bucket*bucket
    four_denom = 4 * denom
    
    # Image to numpy array
    image = np.asarray(image[:,:])[:,:,:]

    
    dataOut=[]
    numBoxes= int((width/bucket)*(height/bucket))
    width_bucket = width/bucket

    # For each box
    for byte in range(numBoxes):
        x_index = int(byte/width_bucket)
        y_index = int(byte%width_bucket) # is numpy faster?
        x_temp = int(x_index*bucket+bucket/2-1)
        y_temp = int(y_index*bucket+bucket/2-1)

        # Get an inner 2x2 set of pixels
        value = cv2.sumElems(image[x_temp:x_temp+2,y_temp:y_temp+2])
        
        # Find the binary values for each color
        if value[2] < 256:
            dataOut.extend([0,0])
        elif value[2] < 512:
            dataOut.extend([0,1])
        elif value[2] < 768:
            dataOut.extend([1,0])
        else:
            dataOut.extend([1,1])
            
        if value[1] < 256:
            dataOut.extend([0,0])
        elif value[1] < 512:
            dataOut.extend([0,1])
        elif value[1] < 768:
            dataOut.extend([1,0])
        else:
            dataOut.extend([1,1])
            
        if value[0] < 256:
            dataOut.extend([0,0])
        elif value[0] < 512:
            dataOut.extend([0,1])
        elif value[0] < 768:
            dataOut.extend([1,0])
        else:
            dataOut.extend([1,1])
            
        if byte < 10:
            print(value[:3])
            
        if byte == 5:
            print(dataOut)
            
        # Stop when we've hit the end of the metadata
        if len(dataOut) >= totMetaDataSize:
            break
            
    return dataOut
