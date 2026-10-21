"""Analisa uma captura (.pcap/.pcapng) do Wireshark para a Atividade 09.

Para cada quadro, lê os bytes crus e aplica a regra do campo Type/Length
(<= 1500 -> IEEE 802.3, >= 1536 -> Ethernet II), procura tags 802.1Q
(TPID 0x8100) e confere os tamanhos contra os limites teóricos.

Uso:
  python analisar_captura.py captura.pcapng
  python analisar_captura.py captura.pcapng --quadros 12 57 230
  python analisar_captura.py captura.pcapng --saida saida_analise.txt

Sem --quadros, escolhe automaticamente um exemplo de cada categoria
(ARP, IPv4, IPv6, 802.3, VLAN, quadros gerados pelo injetar_quadros.py...).
Os números de quadro são os mesmos da coluna "No." do Wireshark.
"""

import argparse
import io
import sys
from collections import Counter
from pathlib import Path

from scapy.all import PcapNgReader, PcapReader

import comum


def ler_quadros(caminho):
    with open(caminho, "rb") as f:
        magica = f.read(4)
    leitor = PcapNgReader if magica == b"\x0a\x0d\x0d\x0a" else PcapReader
    with leitor(str(caminho)) as r:
        return [bytes(p) for p in r]


def detectar_host(quadros, host_mac):
    if host_mac:
        return bytes.fromhex(host_mac.replace(":", "").replace("-", ""))
    # Origem mais frequente entre os MACs das placas deste PC. Sem filtrar,
    # o gateway costuma ganhar (num download ele envia mais quadros que o host).
    from scapy.all import conf

    locais = {bytes.fromhex(i.mac.replace(":", "")) for i in conf.ifaces.values() if i.mac}
    origens = Counter(q[6:12] for q in quadros)
    for mac, _ in origens.most_common():
        if mac in locais:
            return mac
    return origens.most_common(1)[0][0]


def categoria(q):
    if q["vlans"]:
        return "VLAN 802.1Q"
    if q["formato"] == "IEEE 802.3":
        return "IEEE 802.3"
    if q["formato"] != "Ethernet II (DIX)":
        return "indefinido"
    if q["type_length"] == 0x88B5:
        return "EtherType 0x88B5 (gerado)"
    if q["type_length"] == 0x0800 and q["tamanho"] >= 1514:
        return "IPv4 máximo"
    return q["protocolo"]


def resumo(quadros, decod, host, out):
    p = lambda *a: print(*a, file=out)
    enviados = [q for q in decod if q["src"] == host]
    recebidos = [q for q in decod if q["src"] != host]

    p("=" * 72)
    p("RESUMO DA CAPTURA")
    p("=" * 72)
    p(f"Quadros: {len(decod)}  (enviados pelo host: {len(enviados)}, recebidos: {len(recebidos)})")
    p(f"MAC do host: {comum.mac_str(host)}")
    p()

    p("Formato do quadro MAC (regra do campo Type/Length):")
    for fmt, n in Counter(q["formato"] for q in decod).most_common():
        p(f"  {fmt:<22} {n:>7}")
    p()

    p("Valores do campo Type/Length (após eventuais tags):")
    p(f"  {'valor':<8} {'decimal':>7}  {'formato':<18} {'protocolo':<28} {'qtd':>6}")
    tipos = Counter((q["type_length"], q["formato"], q["protocolo"] or "-") for q in decod)
    for (tl, fmt, proto), n in tipos.most_common():
        p(f"  0x{tl:04x}   {tl:>7}  {fmt:<18} {proto:<28} {n:>6}")
    p()

    tagged = [q for q in decod if q["vlans"]]
    p(f"Quadros com tag VLAN (TPID 0x8100/0x88A8): {len(tagged)}")
    for vid, n in Counter(v["vid"] for q in tagged for v in q["vlans"]).most_common():
        p(f"  VLAN ID {vid}: {n} quadro(s)")
    p()

    p("Tamanhos capturados (bytes, sem preâmbulo/SFD e sem FCS):")
    for rotulo, grupo in (("todos", decod), ("enviados", enviados), ("recebidos", recebidos)):
        if grupo:
            t = [q["tamanho"] for q in grupo]
            p(f"  {rotulo:<10} min {min(t):>5}  max {max(t):>5}  média {sum(t) / len(t):8.1f}")
    abaixo = [q for q in decod if q["tamanho"] < 60]
    acima = [q for q in decod if q["tamanho"] > 1514 + comum.TAG_VLAN * len(q["vlans"])]
    p(f"  < 60 bytes (abaixo do mínimo sem FCS): {len(abaixo)}"
      f"  -> enviados pelo host: {sum(q['src'] == host for q in abaixo)}")
    p(f"  > 1514 bytes (+4 por tag): {len(acima)}")
    com_pad = [q for q in recebidos if q["pad"]]
    p(f"  recebidos com PAD: {len(com_pad)}"
      + (f" (ex.: {com_pad[0]['tamanho']} bytes, {com_pad[0]['pad']} de PAD)" if com_pad else ""))
    p()


def detalhar(n, q, host, out):
    p = lambda *a: print(*a, file=out)
    sentido = "enviado pelo host" if q["src"] == host else "recebido"
    p("-" * 72)
    p(f"Quadro nº {n}  |  {q['tamanho']} bytes capturados  |  {sentido}")
    p("-" * 72)
    p(f"  Destino : {comum.mac_str(q['dst'])}  ({comum.tipo_endereco(q['dst'])})")
    p(f"  Origem  : {comum.mac_str(q['src'])}  ({comum.tipo_endereco(q['src'])})")
    for v in q["vlans"]:
        p(f"  Tag     : TPID 0x{v['tpid']:04x}  TCI 0x{v['tci']:04x}"
          f"  -> PCP {v['pcp']} | DEI {v['dei']} | VLAN ID {v['vid']}"
          f"  (bytes {v['offset']}-{v['offset'] + 3})")
    tl = q["type_length"]
    p(f"  Type/Len: 0x{tl:04x} = {tl}  (bytes {q['offset_tl']}-{q['offset_tl'] + 1})")
    p(f"  Formato : {q['formato']}  [{q['justificativa']}]")
    if q["formato"] == "IEEE 802.3" and q["llc"]:
        l = q["llc"]
        p(f"  LLC     : DSAP 0x{l['dsap']:02x} ({comum.SAPS_LLC.get(l['dsap'], '?')})"
          f"  SSAP 0x{l['ssap']:02x}  Controle 0x{l['controle']:02x}")
    elif q["protocolo"]:
        p(f"  Protocolo da camada acima: {q['protocolo']}")
    p(f"  Cabeçalho MAC: {q['cabecalho']} bytes  |  payload: {len(q['payload'])} bytes")
    if q["dados_uteis"] is not None:
        fonte = "campo Length" if q["formato"] == "IEEE 802.3" else "camada superior"
        p(f"  Dados úteis: {q['dados_uteis']} bytes ({fonte})  |  PAD: {q['pad']} bytes")
    no_fio = max(q["tamanho"], 60) + comum.FCS
    p(f"  No meio físico: {comum.PREAMBULO + comum.SFD} (preâmbulo+SFD) + {no_fio} (quadro MAC com"
      f" FCS{' e PAD da placa' if q['tamanho'] < 60 else ''}) = {comum.PREAMBULO + comum.SFD + no_fio} bytes")
    raw = bytes(q["dst"] + q["src"]) + b"".join(
        v["tpid"].to_bytes(2, "big") + v["tci"].to_bytes(2, "big") for v in q["vlans"]
    ) + tl.to_bytes(2, "big") + q["payload"]
    p("  Bytes iniciais:")
    p(comum.dump_hex(raw, limite=48))
    p()


def escolher_exemplos(decod):
    vistos, escolhidos = set(), []
    for i, q in enumerate(decod, start=1):
        c = categoria(q)
        if c not in vistos:
            vistos.add(c)
            escolhidos.append(i)
    return escolhidos


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("captura", type=Path)
    ap.add_argument("--quadros", nargs="+", type=int, metavar="N", help="números dos quadros a detalhar")
    ap.add_argument("--host-mac", help="MAC do host (padrão: origem mais frequente)")
    ap.add_argument("--saida", type=Path, help="grava o relatório em UTF-8 neste arquivo")
    args = ap.parse_args()

    if not args.captura.exists():
        sys.exit(f"Arquivo não encontrado: {args.captura}")
    quadros = ler_quadros(args.captura)
    if not quadros:
        sys.exit("A captura está vazia.")
    decod = [comum.decodificar_quadro(q) for q in quadros]
    host = detectar_host(quadros, args.host_mac)

    out = io.StringIO()
    resumo(quadros, decod, host, out)
    nums = args.quadros or escolher_exemplos(decod)
    print("=" * 72, file=out)
    print("QUADROS DETALHADOS" + ("" if args.quadros else " (um exemplo de cada categoria)"), file=out)
    print("=" * 72, file=out)
    for n in nums:
        if not 1 <= n <= len(decod):
            print(f"Quadro {n} não existe (a captura tem {len(decod)}).\n", file=out)
            continue
        detalhar(n, decod[n - 1], host, out)

    texto = out.getvalue()
    print(texto, end="")
    if args.saida:
        args.saida.write_text(texto, encoding="utf-8")
        print(f"Relatório gravado em {args.saida}")


if __name__ == "__main__":
    main()
