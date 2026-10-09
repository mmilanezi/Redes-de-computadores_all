#!/bin/bash
# Configura r1 ou r2 (detecta o papel pelo hostname) na topologia:
#   [c1] --net-c1-- [r1] --net-transit-- [r2] --net-c2-- [c2]
set -e

ROLE="$(hostname)"

find_iface() {
    # $1 = fragmento do IPv4 da rede (ex: "192.0.2.")
    ip -4 -o addr show | grep "$1" | awk '{print $2}'
}

if [ "$ROLE" = "r1" ]; then
    IFACE_CLIENT=$(find_iface "192\.0\.2\.")
    IFACE_TRANSIT=$(find_iface "198\.51\.100\.")
    CLIENT_V6_PREFIX="fd00:1234:5678:1::/64"
    CLIENT_V6_ADDR="fd00:1234:5678:1::1/64"
    TRANSIT_V6_ADDR="fd00:1234:5678:ffff::1/64"
    REMOTE_V4_NET="203.0.113.0/24"
    REMOTE_V6_NET="fd00:1234:5678:2::/64"
    NEXTHOP_V4="198.51.100.2"
    NEXTHOP_V6="fd00:1234:5678:ffff::2"
elif [ "$ROLE" = "r2" ]; then
    IFACE_CLIENT=$(find_iface "203\.0\.113\.")
    IFACE_TRANSIT=$(find_iface "198\.51\.100\.")
    CLIENT_V6_PREFIX="fd00:1234:5678:2::/64"
    CLIENT_V6_ADDR="fd00:1234:5678:2::1/64"
    TRANSIT_V6_ADDR="fd00:1234:5678:ffff::2/64"
    REMOTE_V4_NET="192.0.2.0/24"
    REMOTE_V6_NET="fd00:1234:5678:1::/64"
    NEXTHOP_V4="198.51.100.1"
    NEXTHOP_V6="fd00:1234:5678:ffff::1"
else
    echo "setup-router.sh: hostname '$ROLE' nao reconhecido (esperado r1 ou r2)" >&2
    exit 1
fi

echo "Papel: $ROLE | iface cliente: $IFACE_CLIENT | iface transito: $IFACE_TRANSIT"

ip -6 addr add "$CLIENT_V6_ADDR" dev "$IFACE_CLIENT" 2>/dev/null || echo "(endereco v6 cliente ja existia)"
ip -6 addr add "$TRANSIT_V6_ADDR" dev "$IFACE_TRANSIT" 2>/dev/null || echo "(endereco v6 transito ja existia)"

ip route replace "$REMOTE_V4_NET" via "$NEXTHOP_V4" 2>/dev/null || true
ip -6 route replace "$REMOTE_V6_NET" via "$NEXTHOP_V6" dev "$IFACE_TRANSIT" 2>/dev/null || true

cat > /etc/radvd.conf <<EOF
interface $IFACE_CLIENT {
	AdvSendAdvert on;
	AdvManagedFlag off;
	AdvOtherConfigFlag off;
	prefix $CLIENT_V6_PREFIX {
		AdvOnLink on;
		AdvAutonomous on;
	};
};
EOF

radvd -C /etc/radvd.conf -p /run/radvd.pid
echo "radvd iniciado (pid $(cat /run/radvd.pid)) anunciando $CLIENT_V6_PREFIX em $IFACE_CLIENT"
echo "Forwarding IPv4 (net.ipv4.ip_forward): $(cat /proc/sys/net/ipv4/ip_forward)"
echo "Forwarding IPv6 (net.ipv6.conf.all.forwarding): $(cat /proc/sys/net/ipv6/conf/all/forwarding)"
echo "Rota estatica adicionada: $REMOTE_V4_NET via $NEXTHOP_V4"
