"""Gera e envia quadros de teste para a Atividade 09 (Ethernet e MAC).

A captura normal do PC só mostra Ethernet II sem tag VLAN. Este script envia,
pela placa física, quadros montados byte a byte para que o Wireshark capture
também os formatos que não aparecem sozinhos:

  1. ethernet2    Ethernet II com EtherType experimental 0x88B5
  2. ieee8023     IEEE 802.3 + LLC (TEST), com Length < área de dados (PAD)
  3. icmp         ICMP Echo para o gateway, SEM tag (referência)
  4. icmp-vlan    o mesmo ICMP Echo, COM tag 802.1Q (VID 10, PCP 5)
  5. max          Ethernet II com payload de 1500 bytes (maior quadro sem tag)
  6. max-vlan     o mesmo, com tag 802.1Q (maior quadro com tag)

Uso (PowerShell como administrador, Wireshark capturando na "Ethernet"):
  python injetar_quadros.py              envia os 6 quadros
  python injetar_quadros.py --dry-run    só monta e grava quadros_gerados.pcap
  python injetar_quadros.py --so icmp icmp-vlan
"""

import argparse
import sys
import time
from pathlib import Path

from scapy.all import ICMP, IP, LLC, Dot1Q, Dot3, Ether, Raw, conf, sendp, wrpcap

import comum

PASTA = Path(__file__).resolve().parent
MARCA = b"UNISINOS-A09"


def montar(rede, vid, pcp):
    dst, src = rede["gw_mac"], rede["host_mac"]
    ip = IP(src=rede["host_ip"], dst=rede["gw_ip"])
    dados_llc = MARCA + b" 802.3"
    quadros = {}

    quadros["ethernet2"] = (
        "Ethernet II, EtherType 0x88B5 (IEEE Local Experimental)",
        Ether(dst=dst, src=src, type=0x88B5) / Raw(MARCA + b" Ethernet II " + b"." * 20),
    )

    # Length = só LLC + dados; o PAD que completa os 46 bytes não entra na conta
    quadros["ieee8023"] = (
        "IEEE 802.3 + LLC TEST (DSAP/SSAP 0x00), Length menor que a área de dados",
        Dot3(dst=dst, src=src, len=3 + len(dados_llc))
        / LLC(dsap=0x00, ssap=0x00, ctrl=0xE3)
        / Raw(dados_llc)
        / Raw(b"\x00" * (46 - 3 - len(dados_llc))),
    )

    icmp = ICMP(type=8, id=0x0A09, seq=1) / Raw(MARCA + b" ICMP sem/com tag")
    quadros["icmp"] = (
        "ICMP Echo Request para o gateway, sem tag (referência)",
        Ether(dst=dst, src=src) / ip / icmp,
    )
    quadros["icmp-vlan"] = (
        f"ICMP Echo Request idêntico, com tag 802.1Q (VID {vid}, PCP {pcp})",
        Ether(dst=dst, src=src) / Dot1Q(prio=pcp, dei=0, vlan=vid) / ip / icmp,
    )

    # IP Total Length = 1500 (MTU): 20 IP + 8 ICMP + 1472 de dados
    grande = ICMP(type=8, id=0x0A09, seq=2) / Raw((MARCA + b" MTU " + b"." * 1472)[:1472])
    quadros["max"] = (
        "Ethernet II com payload de 1500 bytes (maior quadro sem tag)",
        Ether(dst=dst, src=src) / ip / grande,
    )
    quadros["max-vlan"] = (
        f"Mesmo quadro máximo, com tag 802.1Q (VID {vid}, PCP {pcp})",
        Ether(dst=dst, src=src) / Dot1Q(prio=pcp, dei=0, vlan=vid) / ip / grande,
    )
    return quadros


def descrever(nome, titulo, pkt):
    raw = bytes(pkt)
    q = comum.decodificar_quadro(raw)
    print(f"[{nome}] {titulo}")
    print(f"  tamanho entregue ao driver: {len(raw)} bytes (sem FCS)")
    for v in q["vlans"]:
        print(f"  tag: TPID 0x{v['tpid']:04x}  TCI 0x{v['tci']:04x}"
              f" -> PCP {v['pcp']}, DEI {v['dei']}, VID {v['vid']}")
    print(f"  Type/Length: 0x{q['type_length']:04x} ({q['type_length']}) -> {q['formato']}")
    print(f"  cabeçalho MAC: {q['cabecalho']} bytes | payload: {len(q['payload'])} bytes")
    if q["pad"]:
        print(f"  dados úteis: {q['dados_uteis']} bytes + PAD {q['pad']} bytes")
    print(comum.dump_hex(raw, limite=32))
    print()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--iface", default="Ethernet", help='nome da interface (padrão: "Ethernet")')
    ap.add_argument("--vlan", type=int, default=10, help="VLAN ID da tag (padrão: 10)")
    ap.add_argument("--pcp", type=int, default=5, help="prioridade 802.1p da tag (padrão: 5)")
    ap.add_argument("--so", nargs="+", metavar="QUADRO", help="envia só os quadros escolhidos")
    ap.add_argument("--dry-run", action="store_true", help="não envia, só grava o .pcap")
    args = ap.parse_args()

    if not 0 <= args.vlan <= 4095 or not 0 <= args.pcp <= 7:
        sys.exit("VLAN ID deve estar entre 0 e 4095 e PCP entre 0 e 7.")

    conf.verb = 0
    rede = comum.descobrir_rede(args.iface)
    if not rede["gw_mac"]:
        sys.exit("Não consegui descobrir o MAC do gateway (ARP sem resposta).")

    print(f"Interface : {rede['iface'].name} ({rede['iface'].description})")
    print(f"Host      : {rede['host_mac']}  {rede['host_ip']}")
    print(f"Gateway   : {rede['gw_mac']}  {rede['gw_ip']}")
    print()

    quadros = montar(rede, args.vlan, args.pcp)
    escolhidos = args.so or list(quadros)
    invalidos = [n for n in escolhidos if n not in quadros]
    if invalidos:
        sys.exit(f"Quadro(s) desconhecido(s): {', '.join(invalidos)}. Opções: {', '.join(quadros)}")

    enviados = []
    for nome in escolhidos:
        titulo, pkt = quadros[nome]
        descrever(nome, titulo, pkt)
        enviados.append(pkt)
        if not args.dry_run:
            sendp(pkt, iface=rede["iface"])
            time.sleep(0.5)

    saida = PASTA / "quadros_gerados.pcap"
    wrpcap(str(saida), enviados)
    acao = "montados (dry-run, nada enviado)" if args.dry_run else "enviados"
    print(f"{len(enviados)} quadro(s) {acao}. Cópia em {saida.name}")


if __name__ == "__main__":
    main()
