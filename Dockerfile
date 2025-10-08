FROM python:3-slim

COPY requirements.txt /tmp/

RUN apt-get update && \
    apt-get install -y gcc && \
    pip install -r /tmp/requirements.txt && \
    rm /tmp/requirements.txt && \
    apt autoremove -y gcc && \
    apt-get clean

RUN mkdir /opt/growatt-charger

COPY defaults /opt/growatt-charger/defaults
COPY src /opt/growatt-charger/src
COPY growatt_charger.py /opt/growatt-charger/

RUN mkdir -p /opt/growatt-charger/conf \
    /opt/growatt-charger/output \
    /opt/growatt-charger/logs \
    && chmod 777 /opt/growatt-charger/logs \
    /opt/growatt-charger/output

VOLUME /opt/growatt-charger/conf
VOLUME /opt/growatt-charger/output
VOLUME /opt/growatt-charger/logs

ENTRYPOINT ["python", "/opt/growatt-charger/growatt_charger.py"]
