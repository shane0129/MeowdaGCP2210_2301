import io
import os

import cv2
import numpy as np
import torch
from matplotlib import pyplot as plt

from PIL import Image
from pathlib import Path
from torchvision import transforms

from models.experimental import attempt_load
from utils.datasets import letterbox
from utils.general import non_max_suppression
from utils.plots import output_to_keypoint, plot_skeleton_kpts


# FastAPI Yolov7 Server
import nest_asyncio
import uvicorn
from fastapi import FastAPI, UploadFile, File
from json import dumps

WEIGHTS = "./22cat_best.pt"
DEVICE = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
IMAGE_SIZE = 640  # Detection size

CLASSES = [
'躲貓貓Hide_and_Seek','麻糬Mochi','跩哥Malfoy','瞌睡蟲Sleepy','小孤獨Lonely','阿虎Tiger','豆花Douhua','小花Flower','美女Prettygirl','膽小鬼Coward','小妖豔Shower','小淘氣Player','小煤炭Soot_Spirits','傑克Jack','麒麟Kirin','熊貓Panda','站長Station_Master','萱萱Xuan_Xuan','跳跳虎Jumping_Tiger','沃卡萊姆Vodka_Lime','馬丁尼Martini','莫希托Mojito']

# Load YOLOv7
model = attempt_load(WEIGHTS, DEVICE)


# Assign an instance of the FastAPI class to the variable "app".
# You will interact with your api using this instance.
app = FastAPI(title='Deploying a Yolov7 with FastAPI')


@app.get("/", tags=["確認 API 是否成功運行"])
def home():
    return "恭喜! 你的 API 成功運行中，去 http://localhost:8000/docs 看看吧!"


@app.post("/predict", tags=["進行預測"]) 
def yolo(file: UploadFile = File(...)):

    def predict(image, image_size=640):
        image = np.asarray(image)
        
        # Resize image to the inference size
        ori_h, ori_w = image.shape[:2]
        image = cv2.resize(image, (image_size, image_size))
        
        # Transform image from numpy to torch format
        image_pt = torch.from_numpy(image).permute(2, 0, 1).to(DEVICE)
        image_pt = image_pt.float() / 255.0
        
        # Infer
        with torch.no_grad():
            pred = model(image_pt[None], augment=False)[0]
        
        # NMS
        pred = non_max_suppression(pred)[0].cpu().numpy()
        
        # Resize boxes to the original image size
        pred[:, [0, 2]] *= ori_w / image_size
        pred[:, [1, 3]] *= ori_h / image_size
        
        return pred

    image = Image.open(io.BytesIO(file.file.read()))
    pred = predict(image)
    return dumps(pred.tolist())


# Allows the server to be run in this interactive environment
nest_asyncio.apply()

# Host depends on the setup you selected (docker or virtual env)
# host = "0.0.0.0" if os.getenv("DOCKER-SETUP") else "127.0.0.1"

# # Spin up the server!    
# uvicorn.run(app, host=host, port=8000)