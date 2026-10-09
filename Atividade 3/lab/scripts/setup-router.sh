#!/bin/bash
set -e

ip -6 addr add fd00:1234:5678::1/64 dev eth0 2>/dev/null || echo "(endereco ja existia, ok)"

echo "Forwarding (net.ipv6.conf.all.forwarding): $(cat /proc/sys/net/ipv6/conf/all/forwarding)"

radvd -C /etc/radvd.conf -p /run/radvd.pid
echo "radvd iniciado, pid $(cat /run/radvd.pid)"
