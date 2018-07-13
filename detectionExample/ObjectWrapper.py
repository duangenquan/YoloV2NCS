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
    mvnc.global_set_option(mvnc.GlobalOption.RW_LOG_LEVEL, 2)
    devices = mvnc.enumerate_devices()
    devNum = len(devices)
    if len(devices) == 0:
        print('No MVNC devices found')
        quit()
    devHandle = []
    graphHandle = []
    fifoInHandle = []
    fifoOutHandle = []

    def __init__(self, graphfile):
        select = 1
        self.detector = YoloDetector(select)
        for i in range(ObjectWrapper.devNum):
            ObjectWrapper.devHandle.append(mvnc.Device(ObjectWrapper.devices[i]))
            ObjectWrapper.devHandle[i].open()
            # load blob
            with open(graphfile, mode='rb') as f:
                blob = f.read()
            # create graph instance
            ObjectWrapper.graphHandle.append(mvnc.Graph('inst' + str(i)))
            # allocate resources
            fifoIn, fifoOut = ObjectWrapper.graphHandle[i].allocate_with_fifos(ObjectWrapper.devHandle[i], blob)
            ObjectWrapper.fifoInHandle.append(fifoIn)
            ObjectWrapper.fifoOutHandle.append(fifoOut)
 
        self.dim = (416,416)
        self.blockwd = 12
        self.wh = self.blockwd*self.blockwd
        self.targetBlockwd = 13
        self.classes = 20
        self.threshold = 0.2
        self.nms = 0.4

    def __del__(self):
        for i in range(ObjectWrapper.devNum):
            ObjectWrapper.fifoInHandle[i].destroy()
            ObjectWrapper.fifoOutHandle[i].destroy()
            ObjectWrapper.graphHandle[i].destroy()
            ObjectWrapper.devHandle[i].close()

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

    def Detect(self, img, idx=0):
        """Send image for inference on a single compute stick
           
            Args:
                img: openCV image type
                idx: index of the compute stick to use for inference
            Returns:
                [<BBox>]: array of BBox type objects for each result in the detection
        """
        imgw = img.shape[1]
        imgh = img.shape[0]

        im,offx,offy,xscale,yscale = self.PrepareImage(img, self.dim)
        #print('xscale = {}, yscale = {}'.format(xscale, yscale))

        ObjectWrapper.graphHandle[idx].queue_inference_with_fifo_elem(
                ObjectWrapper.fifoInHandle[idx],
                ObjectWrapper.fifoOutHandle[idx],
                im.astype(np.float32), 'user object')
        out, userobj = ObjectWrapper.fifoOutHandle[idx].read_elem()
        out = self.Reshape(out, self.dim)

        internalresults = self.detector.Detect(out.astype(np.float32), int(out.shape[0]/self.wh), self.blockwd, self.blockwd, self.classes, imgw, imgh, self.threshold, self.nms, self.targetBlockwd)
        pyresults = [BBox(x,xscale,yscale, offx, offy) for x in internalresults]
        return pyresults

    def Parallel(self, img):
        """Send array of images for inference on multiple compute sticks
           
            Args:
                img: array of images to run inference on
           
            Returns:
                { <int>:[<BBox] }: A dict with key-value pairs mapped to compute stick device numbers and arrays of the detection boxs (BBox)
        """
        pyresults = {}
        for i in range(ObjectWrapper.devNum):
            im, offx, offy, w, h = self.PrepareImage(img[i], self.dim)
            ObjectWrapper.graphHandle[i].queue_inference_with_fifo_elem(
                    ObjectWrapper.fifoInHandle[i],
                    ObjectWrapper.fifoOutHandle[i],
                    im.astype(np.float32), 'user object')
        for i in range(ObjectWrapper.devNum):
            out, userobj = ObjectWrapper.fifoOutHandle[i].read_elem()
            out = self.Reshape(out, self.dim)
            imgw = img[i].shape[1]
            imgh = img[i].shape[0]
            internalresults = self.detector.Detect(out.astype(np.float32), int(out.shape[0]/self.wh), self.blockwd, self.blockwd, self.classes, imgw, imgh, self.threshold, self.nms, self.targetBlockwd)
            res = [BBox(x, w, h, offx, offy) for x in internalresults]
            if i not in pyresults:
                pyresults[i] = res
        return pyresults
