from libpydetector import YoloDetector
import os, io, numpy, time
import numpy as np
from mvnc import mvncapi as mvnc
from skimage.transform import resize

class BBox(object):
    def __init__(self, bbox, xscale, yscale, offx, offy):
        self.left = int(bbox.left / xscale)-offx
        self.top = int(bbox.top / yscale)-offy
        self.right = int(bbox.right / xscale)-offx
        self.bottom = int(bbox.bottom / yscale)-offy
        self.confidence = bbox.confidence
        self.objType = bbox.objType
        self.name = bbox.name

class ObjectWrapper():
    mvnc.SetGlobalOption(mvnc.GlobalOption.LOG_LEVEL, 2)
    devices = mvnc.EnumerateDevices()
    devNum = len(devices)
    if len(devices) == 0:
        print('No MVNC devices found')
        quit()
    devHandle = []
    graphHandle = []
    def __init__(self, graphfile):
        select = 1
        self.detector = YoloDetector(select)
        
        for i in range(ObjectWrapper.devNum):
            ObjectWrapper.devHandle.append(mvnc.Device(ObjectWrapper.devices[i]))
            ObjectWrapper.devHandle[i].OpenDevice()
            opt = ObjectWrapper.devHandle[i].GetDeviceOption(mvnc.DeviceOption.OPTIMISATION_LIST)
            # load blob
            with open(graphfile, mode='rb') as f:
                blob = f.read()
            ObjectWrapper.graphHandle.append(ObjectWrapper.devHandle[i].AllocateGraph(blob))
            ObjectWrapper.graphHandle[i].SetGraphOption(mvnc.GraphOption.ITERATIONS, 1)
            iterations = ObjectWrapper.graphHandle[i].GetGraphOption(mvnc.GraphOption.ITERATIONS)

            self.dim = (416,416)
            self.blockwd = 12
            self.wh = self.blockwd*self.blockwd
            self.targetBlockwd = 13
            self.classes = 20
            self.threshold = 0.2
            self.nms = 0.4


    def __del__(self):
        for i in range(ObjectWrapper.devNum):
            ObjectWrapper.graphHandle[i].DeallocateGraph()
            ObjectWrapper.devHandle[i].CloseDevice()
    def PrepareImage(self, img, dim):
        imgw = img.shape[1]
        imgh = img.shape[0]
        imgb = np.empty((dim[0], dim[1], 3))
        imgb.fill(0.5)

        if imgh/imgw > dim[1]/dim[0]:
            neww = int(imgw * dim[1] / imgh)
            newh = dim[1]
        else:
            newh = int(imgh * dim[0] / imgw)
            neww = dim[0]
        offx = int((dim[0] - neww)/2)
        offy = int((dim[1] - newh)/2)

        imgb[offy:offy+newh,offx:offx+neww,:] = resize(img.copy()/255.0,(newh,neww),1)
        im = imgb[:,:,(2,1,0)]
        return im, int(offx*imgw/neww), int(offy*imgh/newh), neww/dim[0], newh/dim[1]

    def Reshape(self, out, dim):
        shape = out.shape
        out = np.transpose(out.reshape(self.wh, int(shape[0]/self.wh)))  
        out = out.reshape(shape)
        return out

    def Detect(self, img):
        imgw = img.shape[1]
        imgh = img.shape[0]

        im,offx,offy,xscale,yscale = self.PrepareImage(img, self.dim)
        #print('xscale = {}, yscale = {}'.format(xscale, yscale))
        ObjectWrapper.graphHandle[0].LoadTensor(im.astype(np.float16), 'user object')
        out, userobj = ObjectWrapper.graphHandle[0].GetResult()
        out = self.Reshape(out, self.dim)

        internalresults = self.detector.Detect(out.astype(np.float32), int(out.shape[0]/self.wh), self.blockwd, self.blockwd, self.classes, imgw, imgh, self.threshold, self.nms, self.targetBlockwd)
        pyresults = [BBox(x,xscale,yscale, offx, offy) for x in internalresults]
        return pyresults

    def Parallel(self, img):
        pyresults = {}
        for i in range(ObjectWrapper.devNum):
            im, offx, offy, w, h = self.PrepareImage(img[i], self.dim)
            ObjectWrapper.graphHandle[i].LoadTensor(im.astype(np.float16), 'user object')
        for i in range(ObjectWrapper.devNum):
            out, userobj = ObjectWrapper.graphHandle[i].GetResult()
            out = self.Reshape(out, self.dim)
            imgw = img[i].shape[1]
            imgh = img[i].shape[0]
            internalresults = self.detector.Detect(out.astype(np.float32), int(out.shape[0]/self.wh), self.blockwd, self.blockwd, self.classes, imgw, imgh, self.threshold, self.nms, self.targetBlockwd)
            res = [BBox(x, w, h, offx, offy) for x in internalresults]
            if i not in pyresults:
                pyresults[i] = res
        return pyresults
