FROM python:3.10

WORKDIR /home/modbuslogger
COPY ./ /home/modbuslogger/

RUN apt-get update -y
RUN apt-get install ranger vim -y

RUN apt-get -y install libpq-dev gcc

RUN pip install --no-cache-dir \
    pyserial \
    minimalmodbus \
    psycopg2 \
    typing

CMD ["sh", "-c", "while true; do if [ -f /home/modbuslogger/modbuslogger.py ]; then python /home/modbuslogger/modbuslogger.py; else sleep 60; fi; done"]