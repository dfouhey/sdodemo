#!/usr/bin/python
#David Fouhey
#Linear regression demo
#SDO/AIA + SDO/HMI -> SDO/EVE
#
# Given the AIA and HMI data files, predict the EVE values
#

import numpy as np
import os, pdb, datetime, multiprocessing


def getX(record):
    """Given a record from csv, produce a feature vector from the image"""
    vals = []
    print(record[2])
    for fn in record[3:]:
        X = np.load(fn)['x'].astype(np.float64)
        vals += [np.mean(X),np.std(X),np.mean(np.abs(X)),np.std(np.abs(X))]
    return np.array(vals)


def learnify(XTr,Xs):
    """Given training inputs and a set of features, z-score the inputs and add a one"""
    mu, std = np.mean(XTr,axis=0,keepdims=True), np.std(XTr,axis=0,keepdims=True)+1e-8

    XOut = []
    for X in Xs:
        Xd = (X-mu) / std
        XOut.append( np.hstack([Xd,np.ones((X.shape[0],1))]))
    return XOut

if __name__ == "__main__":
    base = "/y/fouhey/SDO_MINI/"

    csv = "%s/join.csv" % (base)
    lines = open(csv).read().strip().split("\n")
    
    eveInd = list(range(13))+[14]

    #load EVE Data
    irradiance = np.load("%s/EVE/irradiance.npy" % (base))
    eveWavelengths = np.load("%s/EVE/wavelength.npy" % (base),allow_pickle=True)
    eveNames = np.load("%s/EVE/name.npy" % (base),allow_pickle=True)


    #Load csv
    header, body = lines[0], lines[1:]

    trainToValSplit = datetime.datetime(year=2012,month=6,day=30)
    valToTestSplit = datetime.datetime(year=2013,month=6,day=30)

    #Records for train/val/test
    trainSamples, valSamples, testSamples = [], [], []

    for line in body:
        record = line.split(",")
        if record[0] == "None":
            continue
        record[0], record[1] = int(record[0]), int(record[1])
        record[2] = datetime.datetime.strptime(record[2],"%Y-%m-%d %H:%M:%S")

        for i in range(3,len(record)):
            record[i] = "%s/%s" % (base,record[i])

        if record[2] < trainToValSplit:
            trainSamples.append(record)
        elif record[2] > valToTestSplit:
            testSamples.append(record)
        else:
            valSamples.append(record)


    if not os.path.exists("precache.npz"):
        #Compute features
        P = multiprocessing.Pool(32)
        print("Train")
        XTr = np.vstack(P.map(getX,trainSamples))
        print("Val")
        XVa = np.vstack(P.map(getX,valSamples))
        print("Test")
        XTe = np.vstack(P.map(getX,testSamples))

        #Extract Y
        EITr = [v[0] for v in trainSamples]  
        EIVa = [v[0] for v in valSamples]  
        EITe = [v[0] for v in testSamples]  
        YTr = np.array(irradiance[EITr,:])[:,eveInd]
        YVa = np.array(irradiance[EIVa,:])[:,eveInd]
        YTe = np.array(irradiance[EITe,:])[:,eveInd]

        np.savez("precache.npz",XTr=XTr,XVa=XVa,XTe=XTe,YTr=YTr,YVa=YVa,YTe=YTe)


    #Load data
    data = np.load("precache.npz")
    XTr, XVa, XTe = data['XTr'], data['XVa'], data['XTe']
    YTr, YVa, YTe = data['YTr'], data['YVa'], data['YTe']
    
    #make masks of invalid datapoints
    maskTr, maskVa, maskTe = YTr<0, YVa<0, YTe<0

    YTr[maskTr] = 0; YVa[maskVa] = 0 
    YTr *= 1e6; YVa *= 1e6; YTe *= 1e6

    #Turn this into normalized features
    XTr, XVa, XTe = learnify(XTr,[XTr,XVa,XTe])

    #Fit a model
    W, _, _, _  = np.linalg.lstsq(XTr,YTr,rcond=-1)

    #Predict
    YTeHat = np.dot(XTe,W)

    #Get the |y-yh| / y value
    E = np.abs(YTeHat-YTe) / YTe

    #set the invalid data points to NaN
    E[maskTe] = np.NaN

    relErrors = np.nanmean(E,axis=0)*100

    print("SDO/AIA + SDO/HMI -> SDO/EVE")
    for ii in range(len(eveInd)):
        print("%10s (%3dA): %.1f%%" % (eveNames[eveInd[ii]].strip(), eveWavelengths[eveInd[ii]]*10,relErrors[ii]))



