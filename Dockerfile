FROM arm64v8/python:3.11
#FROM arm64v8/python:3.11-alpine

WORKDIR /usr/src/app

COPY requirements.txt ./
#RUN apk add --no-cache gcc
RUN pip install --no-cache-dir -r requirements.txt

COPY huaweimqtt.py ./
COPY config.ini ./

CMD [ "python", "./huaweimqtt_v1_0.py" ]
