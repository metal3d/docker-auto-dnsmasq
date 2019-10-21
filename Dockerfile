FROM python:3-alpine

RUN set -xe; \
    apk add --no-cache --update dnsmasq; \
    pip3 install docker

ADD dnsmasq.conf /etc/dnsmasq.conf
ADD docker-auto-dns.py /usr/local/bin/
ADD entrypoint.sh /entrypoint.sh

ENTRYPOINT ["/bin/sh", "/entrypoint.sh"]
CMD ["python3", "/usr/local/bin/docker-auto-dns.py"]
