FROM python:3.9

WORKDIR /yolov7

COPY . /yolov7

ENV ENV TZ=Asia/Taipei

RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && \
    echo $TZ > /etc/timezone && \
    apt-get update && \
    apt-get -y install libgl1-mesa-glx && \
    pip install torch torchvision torchaudio --extra-index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir -r /yolov7/requirements.txt

EXPOSE 8000

CMD [ "uvicorn", "app:app", "--proxy-headers", "--host", "0.0.0.0" ]