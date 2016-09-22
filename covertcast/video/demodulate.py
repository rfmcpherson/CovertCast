# -*- coding: utf-8 -*-
"""
    Created on Wed Jan 30 13:46:33 2013
    demodulate data from a video file
@author: amir
"""

import cv
import numpy as np
import sys

def main(argv):
    if len(argv) < 3:
        sys.stderr.write("Usage: %s <inVideoFile> <outDataFile>\n" % (argv[0],))
        return 1

    """ parameters"""
    width=100
    height=100
    q=3 # data byte size
    bucket=100# num of pixels for each byte
    no_of_bits=8
    Q= np.power(2,q)

    inFile="out0.avi"
    inFile = sys.argv[1]
    vidIn = cv.CreateFileCapture(inFile)
    numFrames = int(cv.GetCaptureProperty(vidIn, cv.CV_CAP_PROP_FRAME_COUNT))
    fps = cv.GetCaptureProperty(vidIn, cv.CV_CAP_PROP_FPS)
    #print 'Num. Frames = ', nFrames
    #print 'Frame Rate = ', fps, ' frames per sec'

    dataOut=[]
    numBytes=width*height/bucket
    for i in xrange(numFrames):
        img=cv.QueryFrame(vidIn)
        for byte in range(numBytes):
            tmpList=[]
            for i in range(bucket):
                x=np.mod(byte*bucket+i,width)
                y=np.divide(byte*bucket+i,height)
                value=cv.Get2D(img,y,x)
                tmpList.append((value[1]/(np.power(2,no_of_bits)/Q))-0.5)
            dByte = np.binary_repr(np.ceil(np.mean(tmpList[0:bucket-10]))).zfill(3)
            for t in range(q):
                dataOut.append(int(dByte[t]))

    # outputing the data
    np.savetxt(sys.argv[2],dataOut,fmt='%1d')

    # difference
    """
    dif=dataOut - data
    error=sum(abs(dif))/np.size(dif)
    print error
    """
if __name__ == "__main__":
    sys.exit(main(sys.argv))




