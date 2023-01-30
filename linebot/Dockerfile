FROM python:3.9

WORKDIR /linebot

COPY . /linebot

ENV TZ=Asia/Taipei

RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && \
    echo $TZ > /etc/timezone && \
    apt-get update && \
    apt-get -y install libgl1-mesa-glx && \
    pip install --upgrade pip && \
    pip install google-cloud-storage && \
    pip install --no-cache-dir -r /linebot/requirements.txt


CMD uwsgi -w meowdabot:app --http-socket :$PORT