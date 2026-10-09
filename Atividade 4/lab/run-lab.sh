#!/usr/bin/env bash
# Orquestra o laboratorio de ICMPv4/ICMPv6 (Atividade 04): sobe a topologia
# [c1] --net-c1-- [r1] --net-transit-- [r2] --net-c2-- [c2], configura os
# roteadores, corrige as rotas necessarias, captura ICMP/ICMPv6 e roda os
# testes do Cenario A (rede local) + o experimento de TTL/Hop Limit.
#
# O Cenario B (Internet) NAO roda por este script: precisa ser executado
# no sistema operacional real do host, fora do Docker. Ver README.md.
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
  for svc in c1 r1 r2 c2; do
    echo
    echo "--- $svc: enderecos IPv4 ---"
    compose exec -T "$svc" ip -4 -o addr show | grep -v ' lo '
    echo "--- $svc: enderecos IPv6 ---"
    compose exec -T "$svc" ip -6 -o addr show | grep -v ' lo '
    echo "--- $svc: MTU ---"
    compose exec -T "$svc" ip link show | grep -o 'mtu [0-9]*' | head -1
    echo "--- $svc: rota padrao IPv4 ---"
    compose exec -T "$svc" ip route show default || true
    echo "--- $svc: rota padrao IPv6 ---"
    compose exec -T "$svc" ip -6 route show default || true
  done
} 2>&1 | tee "$LOGDIR/01-ambiente.log"

section "2. Configurando roteadores r1 e r2 (enderecos, rotas estaticas, radvd)"
{
  echo "--- r1 ---"
  compose exec -T r1 /scripts/setup-router.sh
  echo
  echo "--- r2 ---"
  compose exec -T r2 /scripts/setup-router.sh
} 2>&1 | tee "$LOGDIR/02-router-setup.log"

section "2.1 Corrigindo rota padrao IPv4 de c1/c2 e removendo rota IPv6 fantasma do Docker"
{
  echo "--- c1: rota padrao IPv4 -> r1 ---"
  compose exec -T c1 ip route replace default via 192.0.2.1
  echo "--- c2: rota padrao IPv4 -> r2 ---"
  compose exec -T c2 ip route replace default via 203.0.113.1
  echo "--- c1: removendo rota IPv6 padrao do IPAM do Docker (mantem so a do RA) ---"
  compose exec -T c1 ip -6 route del default via fd00:dead:beef:1::1 2>/dev/null || echo "(ja removida ou nao existia)"
  echo "--- c2: removendo rota IPv6 padrao do IPAM do Docker (mantem so a do RA) ---"
  compose exec -T c2 ip -6 route del default via fd00:dead:beef:2::1 2>/dev/null || echo "(ja removida ou nao existia)"
  echo
  echo "--- c1: rotas finais ---"
  compose exec -T c1 ip route show default
  compose exec -T c1 ip -6 route show default
  echo "--- c2: rotas finais ---"
  compose exec -T c2 ip route show default
  compose exec -T c2 ip -6 route show default
} 2>&1 | tee "$LOGDIR/02.1-fix-rotas.log"

section "Aguardando SLAAC em c1/c2"
sleep 3
{
  for svc in c1 c2; do
    echo "--- $svc: enderecos globais IPv6 (scope global) ---"
    compose exec -T "$svc" ip -6 addr show dev eth0 scope global
  done
} 2>&1 | tee "$LOGDIR/03-slaac.log"

C2_V6=$(compose exec -T c2 sh -c "ip -6 addr show dev eth0 scope global | grep -oP '(?<=inet6 )fd00:1234:5678:2[^/]*'" | tr -d '\r')
echo "IPv6 (ULA) de c2 detectado: $C2_V6"

section "3. Iniciando captura ICMP/ICMPv6 em r1 (todas as interfaces)"
compose exec -d r1 tcpdump -i any -n -vv 'icmp or icmp6' -w /logs/icmp-capture.pcap
sleep 2

section "4. Cenario A - trafego IPv4 e IPv6 entre c1 e c2"
{
  echo "--- ping IPv4 c1 -> c2 (192.0.2.11 -> 203.0.113.12) ---"
  compose exec -T c1 ping -4 -c 5 203.0.113.12

  echo
  echo "--- ping IPv6 c1 -> c2 ($C2_V6) ---"
  compose exec -T c1 ping -6 -c 5 "$C2_V6"
} 2>&1 | tee "$LOGDIR/04-cenario-a.log"

section "5. Provocando e interpretando erro de TTL / Hop Limit"
{
  echo "=== IPv4: TTL=1 (deve expirar em r1) ==="
  compose exec -T c1 ping -4 -c 3 -t 1 203.0.113.12 || true
  echo
  echo "=== IPv4: TTL=2 (deve expirar em r2) ==="
  compose exec -T c1 ping -4 -c 3 -t 2 203.0.113.12 || true
  echo
  echo "=== IPv4: TTL=3 (deve chegar em c2) ==="
  compose exec -T c1 ping -4 -c 3 -t 3 203.0.113.12 || true
  echo
  echo "=== IPv6: Hop Limit=1 (deve expirar em r1) ==="
  compose exec -T c1 ping -6 -c 3 -t 1 "$C2_V6" || true
  echo
  echo "=== IPv6: Hop Limit=2 (deve expirar em r2) ==="
  compose exec -T c1 ping -6 -c 3 -t 2 "$C2_V6" || true
  echo
  echo "=== IPv6: Hop Limit=3 (deve chegar em c2) ==="
  compose exec -T c1 ping -6 -c 3 -t 3 "$C2_V6" || true
} 2>&1 | tee "$LOGDIR/05-ttl-hoplimit.log"

section "Encerrando captura"
compose exec -T r1 pkill tcpdump || true
sleep 1
compose exec -T r1 bash -c "tcpdump -r /logs/icmp-capture.pcap -n" 2>&1 | tee "$LOGDIR/06-captura-resumo.log"

section "Concluido"
echo "Logs em: $LOGDIR"
echo "Pcap para abrir no Wireshark: $LOGDIR/icmp-capture.pcap"
echo
echo "LEMBRETE: o Cenario B (ping/captura contra a Internet, ex: 8.8.8.8) precisa"
echo "ser executado fora do Docker, no sistema operacional real do host."
