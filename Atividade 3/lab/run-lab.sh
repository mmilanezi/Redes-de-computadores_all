#!/usr/bin/env bash
# Orquestra o laboratorio IPv6 completo (r1 + c1 + c2) e loga cada etapa
# em lab/logs/, na mesma ordem das secoes do roteiro da Atividade 03.
export MSYS_NO_PATHCONV=1
set -e

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"
LOGDIR="$ROOT/logs"
mkdir -p "$LOGDIR"

compose() { docker compose "$@"; }

section() {
  echo
  echo "==================================================="
  echo "  $1"
  echo "==================================================="
}

section "Subindo ambiente (docker compose up --build)"
compose up -d --build 2>&1 | tee "$LOGDIR/00-up.log"

section "1. Caracterizacao do ambiente"
{
  echo "--- docker compose ps ---"
  compose ps
  for svc in r1 c1 c2; do
    echo
    echo "--- $svc: ip -6 addr show dev eth0 ---"
    compose exec -T "$svc" ip -6 addr show dev eth0
    echo "--- $svc: MTU ---"
    compose exec -T "$svc" ip link show dev eth0 | grep -o 'mtu [0-9]*'
  done
} 2>&1 | tee "$LOGDIR/01-ambiente.log"

section "2.2 Enderecos link-local (antes do RA)"
{
  for svc in c1 c2; do
    echo "--- $svc ---"
    compose exec -T "$svc" ip -6 addr show dev eth0 scope link
  done
} 2>&1 | tee "$LOGDIR/02-linklocal.log"

section "2.3 Configurando r1 (ULA + radvd) e aguardando SLAAC"
compose exec -T r1 /scripts/setup-router.sh 2>&1 | tee "$LOGDIR/03-router-setup.log"
sleep 3
{
  for svc in c1 c2; do
    echo "--- $svc: enderecos globais (scope global) ---"
    compose exec -T "$svc" ip -6 addr show dev eth0 scope global
  done
} 2>&1 | tee "$LOGDIR/03-slaac.log"

section "2.4 Capturando ICMPv6 (RA/NS/NA) em background"
compose exec -d r1 tcpdump -i eth0 -n -vv icmp6 -w /logs/icmpv6-capture.pcap
sleep 2

section "2.5 Testes de conectividade e desempenho"
{
  echo "--- ping c1 -> r1 (ULA) ---"
  compose exec -T c1 ping -6 -c 5 fd00:1234:5678::1

  C2_ULA=$(compose exec -T c2 sh -c "ip -6 addr show dev eth0 scope global | grep -oP '(?<=inet6 )fd00:1234:5678[^/]*'" | tr -d '\r')
  echo "IPv6 ULA de c2: $C2_ULA"

  echo "--- ping c1 -> c2 (ULA) ---"
  compose exec -T c1 ping -6 -c 5 "$C2_ULA"

  echo "--- tabela de vizinhanca em c1 ---"
  compose exec -T c1 ip -6 neigh show dev eth0

  echo "--- iperf3: subindo servidor em c2 ---"
  compose exec -d c2 iperf3 -s

  sleep 1
  echo "--- iperf3: cliente em c1 -> c2 ($C2_ULA), 10s ---"
  compose exec -T c1 iperf3 -6 -c "$C2_ULA" -t 10
} 2>&1 | tee "$LOGDIR/04-conectividade-desempenho.log"

section "Encerrando captura ICMPv6"
compose exec -T r1 pkill tcpdump || true
sleep 1
compose exec -T r1 bash -c "tcpdump -r /logs/icmpv6-capture.pcap -n" 2>&1 | tee "$LOGDIR/05-captura-icmpv6-resumo.log"

section "Concluido"
echo "Logs em: $LOGDIR"
echo "Pcap para abrir no Wireshark: $LOGDIR/icmpv6-capture.pcap"
