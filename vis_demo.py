#!/usr/bin/python
#David Fouhey
#Visualize the data
#
#Pick a random (or specified) row and visualize it

import sunpy
from sunpy.cm import cm
import datetime, os, matplotlib
import numpy as np
from PIL import Image
from matplotlib.colors import LinearSegmentedColormap

#Channels that correspond to HMI Magnetograms 
HMI_WL = ['bx','by','bz']
#A colormap for visualizing HMI
HMI_CM = LinearSegmentedColormap.from_list("bwrblack",["#0000ff","#000000","#ff0000"])

def channelNameToMap(name):
    """Given channel name, return colormap"""
    return HMI_CM if name in HMI_WL else cm.cmlist.get('sdoaia%d' % int(name))

def vis(X,cm,clip):
    """Given image, colormap, and a clipping, visualize results"""
    Xc = np.clip((X-clip[0])/(clip[1]-clip[0]),0,1)
    Xcv = cm(Xc)
    return (Xcv[:,:,:3]*255).astype(np.uint8)

def getPctClip(X):
    """Return the 99.99th percentile"""
    return (0,np.quantile(X.ravel(),0.999))

def getSignedPctClip(X):
    """Return the 99.99th percentile by magnitude, but symmetrize it so 0 is in the middle"""
    v = np.quantile(np.abs(X.ravel()),0.999)
    return (-v,v)

def getClip(X,name):
    """Given an image and the channel name, get the right clip"""
    return getSignedPctClip(X) if name in HMI_WL else getPctClip(X)

if __name__ == "__main__":

    #Update to your location
    base = "/y/fouhey/SDO_MINI/"
    target = "imagesNew/"

    #None = random, otherwise it'll find the closest record for a date
    #showDate = None
    #In the middle of an X9 flare
    showDate = datetime.datetime(year=2017,month=9,day=6,hour=12,minute=0)

    if not os.path.exists(target):
        os.mkdir(target)
    
    csv = "%s/join.csv" % (base)
    lines = open(csv).read().strip().split("\n")

    header, body = lines[0], lines[1:]

    channels = header.split(",")[3:]

    #figure out the record to show 
    recordInd = np.random.choice(len(body))
    if showDate is not None:
        minDelta = datetime.timedelta(weeks=10000)
        for i in range(len(body)):
            recordDate = body[i].split(",")[2]
            diff = abs(showDate-datetime.datetime.strptime(recordDate,"%Y-%m-%d %H:%M:%S"))
            if diff < minDelta:
                print(diff)
                recordInd, minDelta = i, diff


    #load the record
    record = body[recordInd].split(",")
    recordDate = record[2]
    
    dt = datetime.datetime.strptime(recordDate,"%Y-%m-%d %H:%M:%S")
    channelFilenames = record[3:]

    #write an output
    fh = open("%s/view.htm" % target,"w")
    fh.write("%s<br/><br/>" % recordDate)

    #Show the EVE
    if record[0] == "None":
        fh.write("<br/><br/>No SDO/EVE data")
    else:
        ind = int(record[0])
        irradiance = np.load("%s/EVE/irradiance.npy" % base)[ind,:]
        eveWavelength = np.load("%s/EVE/wavelength.npy" % base,allow_pickle=True)
        eveNames = np.load("%s/EVE/name.npy" % base,allow_pickle=True)

        for j in range(irradiance.size):
            fh.write("%s (%d): %e; &nbsp; " % (eveNames[j],eveWavelength[j],irradiance[j]))


    fh.write("<br/><br/>")

    #for every channel
    for chanI in range(len(channelFilenames)):
        channelName = channels[chanI]

        #load, make an image, and save it
        X = np.load("%s/%s" % (base,channelFilenames[chanI]))['x'].astype(np.float64)
        V = vis(X,channelNameToMap(channelName),getClip(X,channelName))
        Image.fromarray(V).save("%s/%s.png" % (target,channelName))
      
        #write a description and the image into the html
        if channelName in HMI_WL:
            fh.write("SDO/HMI Magnetogram, component %s<br/>" % channelName)
        else:
            fh.write("SDO/AIA at %d Angstrom<br/>" % int(channelName)) 
        fh.write("<img src='%s.png'><br/><br/><hr/>" % channelName)
  

    fh.close()

         
