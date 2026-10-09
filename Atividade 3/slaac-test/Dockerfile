FROM ubuntu:24.04

RUN apt-get update && apt-get install -y --no-install-recommends \
    iproute2 \
    iputils-ping \
    radvd \
    tcpdump \
    iperf3 \
    procps \
    && rm -rf /var/lib/apt/lists/*

CMD ["sleep", "infinity"]
