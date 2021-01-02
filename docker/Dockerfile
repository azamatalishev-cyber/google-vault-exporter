FROM alpine:latest

RUN apk add --update --no-cache bash curl git python3 py-cryptography py-openssl py3-pip \
    && apk add --update --no-cache libxml2 libxslt g++ gcc libxslt-dev py-lxml \
    && rm -rf /var/cache/apk/*

ENV PATH="/opt/gam/src:$PATH"

RUN mkdir -p /opt/bin \
    && mkdir -p /root/.gam/gamcache \
    && mkdir -p /root/Downloads \
    && git clone https://github.com/taers232c/GAMADV-XTD3 /opt/gam \
    && pip3 install slack-webhook==1.0.3

WORKDIR /opt/gam/src/
COPY entrypoint.sh /opt/gam/src/

COPY gam.cfg /root/.gam/

COPY main.py /opt/gam/src/

ENTRYPOINT ["entrypoint.sh"]
