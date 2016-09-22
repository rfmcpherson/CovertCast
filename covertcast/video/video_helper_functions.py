def extract_metadata(dataList,metaDataOffset):
    new_frame = int(dataList[0])
    index = int("".join(str(d) for d in dataList[1:len(dataList)-metaDataOffset-3]),2)
    offset = int("".join(str(d) for d in dataList[len(dataList)-metaDataOffset-3:len(dataList)-3]),2)
    bitoffset = int("".join(str(d) for d in dataList[len(dataList)-3:]),2)
    return new_frame, index, offset, bitoffset


def bytes_2_bit_list(data):
    bits = []
    for byte in data:
        bits.append((byte >> 7) & 1)
        bits.append((byte >> 6) & 1)
        bits.append((byte >> 5) & 1)
        bits.append((byte >> 4) & 1)   
        bits.append((byte >> 3) & 1)      
        bits.append((byte >> 2) & 1)
        bits.append((byte >> 1) & 1)
        bits.append((byte     ) & 1)

    return bits

def bit_array_2_bytes(data):
    from bitstring import BitArray
    c = BitArray(data)
    return c.bytes


def bytes_2_ascii(data):
    return data.decode("utf-8")

# given a list of bits
# make a Reed-Solomon ECC
# return list of bits
def reed(data, rsSize):
    import reedsolo
    rs = reedsolo.RSCodec(rsSize) # Set RS
    Bytes = bit_array_2_bytes(data) # Turn bits into bytes
    encoded = rs.encode(list(Bytes)) # Encode list of bytes
    return bytes_2_bit_array(encoded)

# This doesn't work because it assumes the white is only in the video
def image_dem(img):
    import numpy as np
    
    white = (255,255,255)
    top = 0
    bottom = 0
    left = 0
    right = 0

    h,w,_ = img.shape
    midh = h/2
    midw = w/2  

    # i and j are all messed up because numpy does it one way and pil
    # does it the other
    lower = 0
    upper = h-1
    while(lower != upper):
        j = int((upper-lower)/2)+lower
        if isPixWhite(img[j,midw]):
            lower = j
        else:
            upper = j
        if upper - lower == 1:
            if isPixWhite(img[upper,midw]):
                j = upper
            else:
                j = lower
            break
    bottom = j    
    
    
    lower = 0
    upper = h-1
    while(lower != upper):
        j = int((upper-lower)/2)+lower
        if isPixWhite(img[j,midw]):
            upper = j
        else:
            lower = j
        if upper - lower == 1:
            if isPixWhite(img[upper,midw]):
                j = upper
            else:
                j = lower
            break
    top = j
    
    lower = 0
    upper = w-1
    while(lower != upper):
        i = int((upper-lower)/2)+lower
        if isPixWhite(img[midh,i]):
            upper = i
        else:
            lower = i
        if upper - lower == 1:
            if isPixWhite(img[midh,upper]):
                i = upper
            else:
                i = lower
            break
    left = i
    
    lower = 0
    upper = w-1
    while(lower != upper):
        i = int((upper-lower)/2)+lower
        if isPixWhite(img[midh,i]):
            lower = i
        else:
            upper = i
        if upper - lower == 1:
            if isPixWhite(img[midh,upper]):
                i = upper
            else:
                i = lower
            break
    right = i

    return top, bottom, left, right


def image_dem_old2(img):
    import numpy as np
    
    white = (255,255,255)
    top = 0
    bottom = 0
    left = 0
    right = 0

    h,w,_ = img.shape
    midh = h/2
    midw = w/2  
    #print h, w

    # i and j are all messed up because numpy does it one way and pil
    # does it the other
    i = midh
    while(i >= 0 and isPixWhite(img[i,midw])):
        i-=1
        top = i + 1

    i = midh
    while(i < h and isPixWhite(img[i,midw])):
        i+=1
        bottom = i - 1
      
    j = midw
    while(j >= 0 and isPixWhite(img[midh,j])):
        j-=1
        left = j + 1
        
    j= midw
    while(j < w and isPixWhite(img[midh,j])):
        j+=1
        right = j - 1

    return top, bottom, left, right

# Checks if numbers are close
def close(x, y, delta):
    if abs(x-y) > delta:
        return False
    return True

# Checks if the pixel is white
def isPixWhite(pix):
    if( close(pix[0], 255, 20) and close(pix[1], 255, 20) and close(pix[2], 255, 20)):
        return True
    return False
        
# Checks if the image is white
# works on local, but will need robustness in 
# distributed system
def isWhite(im):
    import cv2
    resized_image = cv2.resize(im,(1,1))
    return isPixWhite(resized_image[0,0])

def test():
    print("extract_metadata")
    print("SKIP\n")
    
    print("bytes_2_bit_list")
    input = b"A"
    output = [0,1,0,0,0,0,0,1]
    if bytes_2_bit_list(input) == output:
        print("PASS\n")
    else:
        print("FAIL\n")
        
    print("bit_array_2_bytes")
    input = [0,1,0,0,0,0,0,1]
    output = b"A"
    if bit_array_2_bytes(input) == output:
        print("PASS\n")
    else:
        print("FAIL\n")
    
    print("bytes_2_ascii")
    input = b"HELLO"
    output = "HELLO"
    if bytes_2_ascii(input) == output:
        print("PASS\n")
    else:
        print("FAIL\n")
        
    print("reed")
    print("SKIP\n")
    
    print("reed")
    print("SKIP\n")
    
    print("image_dem")
    print("SKIP\n")
    
    print("isWhite")
    print("SKIP\n")
