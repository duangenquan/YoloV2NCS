#!/bin/bash

filename=tiny-yolo-voc
yolocfg=./yolomodels/$filename.cfg
yoloweight=./yolomodels/$filename.weights


yolocfgcaffe=./caffemodels/$filename.prototxt
yoloweightcaffe=./caffemodels/$filename.caffemodel

echo $yolocfg
echo $yoloweight

echo "convert yolo to caffe"
python ../python/create_yolo_prototxt.py $yolocfg $yolocfgcaffe
python ../python/create_yolo_caffemodel.py -m $yolocfgcaffe -w $yoloweight -o $yoloweightcaffe

echo "done"
