From ubuntu:latest

RUN apt update
RUN apt install python3 -y
RUN apt install python3-pip -y
RUN pip install salat
RUN pip install pytz
RUN pip install tabulate

WORKDIR /usr/app/src

COPY AzanClock.py ./