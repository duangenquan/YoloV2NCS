from libpydetector import YoloDetector
import os, io, numpy, time
import numpy as np
from mvnc import mvncapi as mvnc
from skimage.transform import resize

class BBox(object):
    def __init__(self, bbox):
        self.left = bbox.left
        self.top = bbox.top
        self.right = bbox.right
        self.bottom = bbox.bottom
        self.confidence = bbox.confidence
        self.objType = bbox.objType
        self.name = bbox.name

class ObjectWrapper():
    def __init__(self, graphfile):
        select = 1
        self.detector = YoloDetector(select)
        mvnc.SetGlobalOption(mvnc.GlobalOption.LOG_LEVEL, 2)
        devices = mvnc.EnumerateDevices()
        if len(devices) == 0:
            print('No MVNC devices found')
            quit()
        self.device = mvnc.Device(devices[0])
        self.device.OpenDevice()
        opt = self.device.GetDeviceOption(mvnc.DeviceOption.OPTIMISATION_LIST)
        # load blob
        with open(graphfile, mode='rb') as f:
            blob = f.read()
        self.graph = self.device.AllocateGraph(blob)
        self.graph.SetGraphOption(mvnc.GraphOption.ITERATIONS, 1)
        iterations = self.graph.GetGraphOption(mvnc.GraphOption.ITERATIONS)

        self.dim = (416,416)
        self.blockwd = 12
        self.wh = self.blockwd*self.blockwd
        self.targetBlockwd = 12
        self.classes = 20
        self.threshold = 0.2
        self.nms = 0.4


    def __del__(self):
        self.graph.DeallocateGraph()
        self.device.CloseDevice()
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
        return im,offx,offy

    def Reshape(self, out, dim):
        shape = out.shape
        out = np.transpose(out.reshape(self.wh, int(shape[0]/self.wh)))  
        out = out.reshape(shape)
        return out

    def Detect(self, img):
        imgw = img.shape[1]
        imgh = img.shape[0]

        im,offx,offy = self.PrepareImage(img, self.dim)
        self.graph.LoadTensor(im.astype(np.float16), 'user object')
        out, userobj = self.graph.GetResult()
        out = self.Reshape(out, self.dim)

        internalresults = self.detector.Detect(out.astype(np.float32), int(out.shape[0]/self.wh), self.blockwd, self.blockwd, self.classes, imgw, imgh, self.threshold, self.nms, self.targetBlockwd)
        pyresults = [BBox(x) for x in internalresults]
        return pyresults



































