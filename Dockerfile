FROM Python:latest

COPY ./app /app 

WORKDIR /app

RUN pip install requirements.txt

