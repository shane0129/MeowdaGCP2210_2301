# MongoDB Atlas 
import pymongo                                      
import urllib.parse

# GCP_GCS 連線
import os
from google.cloud import storage

# Linebot
import requests
from flask import Flask, request
from linebot import LineBotApi, WebhookHandler

# 畫辨認貓咪相關套件
import io
import json
import numpy as np
from PIL import Image, ImageDraw, ImageFont

# LineBot flexmessage 模板
from views_template import Carousel_Template


# 導入設定檔
with open("env.json") as f:
    env = json.load(f)

line_bot_api = LineBotApi(env['YOUR_CHANNEL_ACCESS_TOKEN'])  # 確認 token 是否正確
handler = WebhookHandler(env['YOUR_CHANNEL_SECRET'])         # 確認 secret 是否正確
end_point = env["end_point"]



HEADER = {
    'Content-type': 'application/json',
    'Authorization': F'Bearer {env["YOUR_CHANNEL_ACCESS_TOKEN"]}'
}


# 與mongodb atlas做連線
username = urllib.parse.quote_plus(env['MG_username'])
password = urllib.parse.quote_plus(env['MG_password'])
myclient = pymongo.MongoClient(
    f"mongodb+srv://{username}:{password}@cluster0.fv5ng2z.mongodb.net/?retryWrites=true&w=majority")


# 與GCP_GCS連線
os.environ['GOOGlE_APPLICATION_CREDENTIALS'] = './GCS/ServiceKey_GoogleCloud.json'
storage_client = storage.Client()


CLASSES = [
'躲貓貓Hide_and_Seek','麻糬Mochi','跩哥Malfoy','瞌睡蟲Sleepy','小孤獨Lonely','阿虎Tiger','豆花Douhua','小花Flower','美女Prettygirl','膽小鬼Coward','小妖豔Shower','小淘氣Player','小煤炭Soot_Spirits','傑克Jack','麒麟Kirin','熊貓Panda','站長Station_Master','萱萱Xuan_Xuan','跳跳虎Jumping_Tiger','沃卡萊姆Vodka_Lime','馬丁尼Martini','莫希托Mojito']


# 用戶尚未收集的貓咪
StrF = "" 

app = Flask(__name__, static_url_path='/static')

UPLOAD_FOLDER = 'static'
ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'gif', 'HEIC', 'HEIF'])


@app.route("/", methods=['POST', 'GET'])
def linebot():
    if request.method == 'GET':
        return 'ok'
    body = request.json                                            # 可觀察印出來的訊息JSON格式
    events = body["events"]

    if "replyToken" in events[0]:
        payload = dict()
        replyToken = events[0]["replyToken"]
        payload['replyToken'] = replyToken                         # 回應憑證的格式 進入Line-server的基本資格
        source = events[0]["source"]                               # 產生event的來源與userID
        userId = source["userId"]
        print(userId)
        db_landing_user(userId)                                    # 建立用戶資料到mongodb

        if events[0]["type"] == "message":                         # 如果events類型是訊息
            if events[0]["message"]["type"] == "text":
                text = events[0]["message"]["text"]

                if text == "這隻貓叫作什麼名字?":
                    payload["messages"] = [openCamera()]           # 打開相機/打開相簿
                    replyMessage(payload)                          # 呼叫回傳訊息功能


                elif text == "附近景點":
                    payload["messages"] = [Carousel_Template()]    # 回應景點Carousel_Template
                    replyMessage(payload)

                elif text == "我收集到哪些貓咪?":
                    payload["messages"] = db_user_collection(userId)
                    replyMessage(payload)

                elif text == "查詢尚未收集到的貓咪們":
                    payload["messages"] = [
                        {
                            "type": "text",
                            "text": StrF
                        }
                    ]

                    replyMessage(payload)


                else:  # 都沒有觸發回應的文字就echo回他
                    payload["messages"] = [
                        {
                            "type": "text",
                            "text": text
                        }
                    ]
                    replyMessage(payload)

            if events[0]["message"]["type"] == "image":                                # 當用戶傳送照片時
                image_bytesio = get_user_content(events[0]["message"]["id"])           # 呼叫存照片功能得到照片儲存路徑
                cat_name, result_image =  whatscat(image_bytesio)                      # 呼叫功能一: 這隻貓叫作什麼名字
                print(cat_name)
                try:
                    try:
                        bs = io.BytesIO()
                        result_image.save(bs, "jpeg")
                        bs.seek(0)
                        upload_blob_from_stream('meowda', bs, f'result_cats_image/{userId}/{events[0]["message"]["id"]}')
                    except:
                        print("上傳GCS辨認框選照失敗")

                    payload["messages"] = [flexmessage(cat_name), reply_detect_img(userId, events[0]["message"]["id"])]
                    replyMessage(payload)
                    db_update_collection(cat_name, userId, events[0]["message"]["id"])
                    
                    try:
                        image_bytesio.seek(0)
                        upload_blob_from_stream('meowda', image_bytesio, f'user_cats_image/{userId}/{events[0]["message"]["id"]}')

                    except:
                        print("上傳GCS用戶貓咪照片失敗")

                except:
                    payload["messages"] = [
                        {
                            "type": "text",
                            "text": "無法辦認是哪隻貓咪\n可以再拍一張嗎?😅"
                        }
                    ]
                    replyMessage(payload)
    return 'OK'                                                                        # 驗證 Webhook 使用，不能省略


# 回傳訊息功能
def replyMessage(payload):
    response = requests.post('https://api.line.me/v2/bot/message/reply', headers=HEADER, json=payload)
    return 'OK'


# template 訊息: 選擇拍照/挑選照片
def openCamera():
    message = {
        "type": "template",
        "altText": "拍張猴硐貓村的貓咪貓咪照吧~",
        "template": {
            "type": "confirm",
            "text": "拍張猴硐貓村的貓咪照📸",
            "actions": [
                {
                    "type": "camera",
                    "label": "打開相機"
                },
                {
                    "type": "cameraRoll",
                    "label": "挑選照片"
                }
            ]
        }
    }
    return message


# 儲存用戶傳來的照片
def get_user_content(message_id):
    res = requests.get(f'https://api-data.line.me/v2/bot/message/{message_id}/content', headers=HEADER, stream=True)
    image_bytes = res.content
    image_bytesio = io.BytesIO(image_bytes)
    return image_bytesio             


# 這隻貓叫作什麼名字
def whatscat(image_bytesio):

    files = {'file': image_bytesio}

    try:
        url = env["yolo_url"]
        res = requests.post(url=url, files=files, stream=True)         # request yolov7 server
        pred = np.asarray(json.loads(res.json()))                      # 得到推論結果
        image = Image.open(image_bytesio)

        try:
            # 畫出偵測結果框選圖片
            draw = ImageDraw.Draw(image)
            font = ImageFont.truetype("./wqy-zenhei/wqy-zenhei.ttc", 40, encoding="unic")  # 設置字體
            for x1, y1, x2, y2, conf, class_id in pred:                # 看class_id決定第幾個標籤得到貓咪分類
                text = f"{CLASSES[int(class_id)]}  {conf:.2f}"         
                draw.rectangle(((x1+10, y1+40), (x2+20, y2+10)), outline='blue', width=15)
                draw.rectangle(((x1+10, y1+10), (x2+20, y1+50)), fill='yellow')
                draw.text((x1+20, y1+10), text, fill ="red", font = font, align ="right")
        except:
            pass
        return text[:-6], image

    except:                                                            # 推論失敗就跳出
        return ""


# FlexMessage 貓咪卡片
def flexmessage(cat_name):
    flex_contents = f"./flexmessage_template/{cat_name}_flexmessage.json"
    with open(flex_contents, 'rb') as f:
        contents = json.load(f)
        message = dict()
        message = {
            "type": "flex",
            "altText": "猴硐貓村附近景點推薦給您~",
            "contents": contents
        }
        return message


# 貓咪偵測框選結果照片
def reply_detect_img(user_id, message_id):
    print("https://storage.googleapis.com/meowda/result_cats_image/"+ user_id +"/"+ message_id)
    message = {
        "type": "image",
        "originalContentUrl": "https://storage.googleapis.com/meowda/result_cats_image/"+ user_id + "/" + message_id,
        "previewImageUrl": "https://storage.googleapis.com/meowda/result_cats_image/" + user_id+ "/" + message_id
    }
    return message


# 登入用戶資料到mongoDB
def db_landing_user(userId):
    cats_dict = dict()
    db = myclient["meow_cat_data"]

    cursor = db.user.find({"_id": userId})

    x = dict()
    for i in cursor:
        x.update(i)

    if not x:
        try:
            db.user.insert_one({"_id": userId})
            for x in db.cat_data.find({}, {"name": 1}):
                print(x["name"])
                cats_dict[x["name"]] = ""
            print(cats_dict)
            myquery = {"_id": userId}
            newvalues = {"$set": cats_dict}
            db.user.update_one(myquery, newvalues)
            cursor = db.user.find()
        except:
            print("重複登入 待修改")

    else:
        print("此用戶之前新增過, 所以不用再新增")
        pass


# 更新貓咪收集情況
def db_update_collection(cat_name, userId, message_id):
    db = myclient["meow_cat_data"]
    cursor = db.user.find({"_id": userId})
    x = dict()
    for i in cursor:
        x.update(i)

    if x:
        cat_dict = {cat_name: message_id}
        myquery = {"_id": userId}
        newvalues = {"$set": cat_dict}
        db.user.update_one(myquery, newvalues)


# 查詢mongoDB貓咪收集情況
def db_user_collection(userId):
    global StrF  # 用戶尚未收集的貓咪
    db = myclient["meow_cat_data"]
    cursor = db.user.find({"_id": userId})
    x = dict()
    T_cats = []  # 已收集的貓咪
    F_cats = []  # 未收集的貓咪
    StrT = ""
    StrF = ""  # 每次先清空上次的查詢在更新

    for i in cursor:
        x.update(i)

    if x:  # 查詢此用戶的收集情況 新用戶T_cats為空
        for key, value in x.items():
            if str(value) != "":
                if key == '_id':
                    pass
                else:
                    T_cats.append(key)
            elif str(value) == "":
                F_cats.append(key)
            else:
                pass

        for i in T_cats:  # T_cats轉字串做✅修飾
            StrT += "✅  " + str(i) + "\n"

        for i in F_cats:
            StrF += "🔰 " + str(i) + "\n"

        if not T_cats:  # 新用戶第先按"收集貓貓"的回應
            message = [
                {
                    "type": "text",
                    "text": "打開相機開始收集吧~。📸"
                },
                {
                    "type": "text",
                    "text": "小提示😆小貓咪們都在圈圈處🐈"
                },
                {
                    "type": "image",
                    "originalContentUrl": end_point + "/static/element/" + "cats_map.jpg",
                    "previewImageUrl": end_point + "/static/element/" + "cats_map.jpg"
                }
            ]
            return message

        elif len(T_cats) == 22:
            message = [
                {
                    "type": "text",
                    "text": "🎉🎉🎉🎉🎉🎉\n您太厲害了!所有貓咪們都收集完了🎉🎉🎉🎉🎉🎉"
                }
            ]
            return message

        if T_cats:  # 舊用戶回應"收集貓貓"
            message = [
                {
                    "type": "text",
                    "text": "您已收集到的貓咪🐈:\n\n" + StrT
                },
                {
                    "type": "text",
                    "text": f"還有🐈{len(F_cats)}隻貓咪\n尚未收集到😅"
                },
                {
                    "type": "image",
                    "originalContentUrl": end_point + "/static/element/" + "cats_map.jpg",
                    "previewImageUrl": end_point + "/static/element/" + "cats_map.jpg"
                },
                {
                    "type": "template",
                    "altText": "This is a buttons template",
                    "template": {
                        "type": "buttons",
                        "text": "查詢尚未收集到的貓咪們🐈",
                        "actions": [
                            {
                                "type": "message",
                                "label": "查詢貓咪們",
                                "text": "查詢尚未收集到的貓咪們"
                            }
                        ]
                    }
                }
            ]
            return message


# 上傳stream圖片到GCS
def upload_blob_from_stream(bucket_name, file_obj, destination_blob_name):
    """Uploads bytes from a stream or other file-like object to a blob."""
    try:
        storage_client = storage.Client()
        bucket = storage_client.get_bucket(bucket_name)
        blob = bucket.blob(destination_blob_name)
        blob.content_type = 'image/jpeg'
        # Upload data from the stream to your bucket.
        blob.upload_from_file(file_obj)
       
        print(
            f"Stream data uploaded to {destination_blob_name} in bucket {bucket_name}."
        )
    
    except Exception as e:
        print(e)
        return False

if __name__ == "__main__":
    app.run()
