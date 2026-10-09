FROM ubuntu:24.04

RUN apt-get update && apt-get install -y --no-install-recommends \
    iproute2 \
    iputils-ping \
    radvd \
    tcpdump \
    iperf3 \
    procps \
    grep \
    && rm -rf /var/lib/apt/lists/*

COPY radvd.conf /etc/radvd.conf
COPY scripts/ /scripts/
RUN chmod +x /scripts/*.sh

CMD ["sleep", "infinity"]
