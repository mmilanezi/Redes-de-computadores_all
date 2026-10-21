"""Funções compartilhadas pelos scripts da Atividade 09 (Ethernet e MAC).

Toda a decodificação do cabeçalho MAC é feita "na mão", byte a byte, a partir
dos bytes crus do quadro, para deixar explícito o que cada campo significa
(Aula 11, slides 33 e 34). O Scapy é usado só para descobrir a interface,
ler/gravar arquivos de captura e enviar quadros.
"""

# Limites do campo Type/Length (IEEE 802.3, cláusula 3.2.6)
MAX_LENGTH = 1500          # 0x05DC: até aqui o campo é Length (IEEE 802.3)
MIN_ETHERTYPE = 1536       # 0x0600: a partir daqui o campo é Type (Ethernet II / DIX)

TPID_8021Q = 0x8100        # Tag Protocol Identifier da IEEE 802.1Q
TPID_8021AD = 0x88A8       # Q-in-Q (IEEE 802.1ad), só para reconhecer

# Tamanhos do quadro (bytes)
PREAMBULO = 7
SFD = 1
CABECALHO = 14             # destino 6 + origem 6 + Type/Length 2
TAG_VLAN = 4               # TPID 2 + TCI 2
FCS = 4
PAYLOAD_MIN = 46
PAYLOAD_MAX = 1500
QUADRO_MIN = 64            # com FCS
QUADRO_MAX = 1518          # com FCS, sem tag
QUADRO_MAX_VLAN = 1522     # com FCS, com tag 802.1Q

ETHERTYPES = {
    0x0800: "IPv4",
    0x0806: "ARP",
    0x86DD: "IPv6",
    0x8100: "IEEE 802.1Q (VLAN)",
    0x88A8: "IEEE 802.1ad (Q-in-Q)",
    0x88CC: "LLDP",
    0x888E: "EAPOL (802.1X)",
    0x8863: "PPPoE Discovery",
    0x8864: "PPPoE Session",
    0x893A: "IEEE 1905.1",
    0x88B5: "IEEE Local Experimental 1",
    0x88B6: "IEEE Local Experimental 2",
    0x8899: "Realtek RRCP",
    0x88E1: "HomePlug AV",
}

SAPS_LLC = {
    0x00: "Null SAP",
    0x42: "Spanning Tree (BPDU)",
    0xAA: "SNAP",
    0xE0: "Novell IPX",
    0xF0: "NetBIOS",
    0xFE: "ISO Network Layer",
}


def nome_ethertype(valor):
    return ETHERTYPES.get(valor, "desconhecido/proprietário")


def mac_str(b):
    return ":".join(f"{x:02x}" for x in b)


def tipo_endereco(mac):
    """Classifica um MAC pelos bits I/G e U/L do primeiro octeto."""
    if mac == b"\xff" * 6:
        return "broadcast"
    grupo = "multicast" if mac[0] & 0x01 else "unicast"
    admin = "local" if mac[0] & 0x02 else "global (OUI)"
    return f"{grupo}, administrado {admin}"


def classificar_type_length(valor):
    """Regra que diferencia Ethernet II de IEEE 802.3 pelo valor do campo."""
    if valor <= MAX_LENGTH:
        return "IEEE 802.3", f"{valor} <= 1500 (0x05DC): o campo é Length"
    if valor >= MIN_ETHERTYPE:
        return "Ethernet II (DIX)", f"{valor} >= 1536 (0x0600): o campo é EtherType"
    return "indefinido", f"{valor} está entre 1501 e 1535: valor inválido nos dois formatos"


def decodificar_tci(tci):
    return {
        "pcp": tci >> 13,            # 802.1p, 3 bits
        "dei": (tci >> 12) & 0x1,    # antigo CFI, 1 bit
        "vid": tci & 0x0FFF,         # VLAN ID, 12 bits
    }


def decodificar_quadro(raw):
    """Separa o cabeçalho MAC de um quadro cru (sem preâmbulo/SFD e sem FCS)."""
    q = {
        "tamanho": len(raw),
        "dst": raw[0:6],
        "src": raw[6:12],
        "vlans": [],
    }
    pos = 12
    valor = int.from_bytes(raw[pos:pos + 2], "big")
    # Pode haver uma ou mais tags (802.1Q / Q-in-Q) antes do Type/Length real
    while valor in (TPID_8021Q, TPID_8021AD) and len(raw) >= pos + 6:
        tci = int.from_bytes(raw[pos + 2:pos + 4], "big")
        q["vlans"].append({"tpid": valor, "tci": tci, "offset": pos, **decodificar_tci(tci)})
        pos += 4
        valor = int.from_bytes(raw[pos:pos + 2], "big")
    q["type_length"] = valor
    q["offset_tl"] = pos
    q["cabecalho"] = pos + 2
    q["formato"], q["justificativa"] = classificar_type_length(valor)
    q["payload"] = raw[pos + 2:]
    q.update(_analisar_payload(q))
    return q


def _analisar_payload(q):
    """Calcula quantos bytes do payload são dados úteis e quantos são PAD."""
    p, tl = q["payload"], q["type_length"]
    info = {"protocolo": None, "dados_uteis": None, "pad": None, "llc": None}
    if q["formato"] == "IEEE 802.3":
        info["dados_uteis"] = tl
        info["pad"] = max(len(p) - tl, 0)
        if p[:2] == b"\xff\xff":
            info["protocolo"] = "Novell raw 802.3 (IPX sem LLC)"
        elif len(p) >= 3:
            dsap, ssap, ctrl = p[0], p[1], p[2]
            info["llc"] = {"dsap": dsap, "ssap": ssap, "controle": ctrl}
            info["protocolo"] = "LLC" + (" + SNAP" if dsap == 0xAA else "")
        return info
    if q["formato"] != "Ethernet II (DIX)":
        return info
    info["protocolo"] = nome_ethertype(tl)
    # O Ethernet II não informa o tamanho dos dados; quem sabe é a camada de cima
    if tl == 0x0800 and len(p) >= 4:
        info["dados_uteis"] = int.from_bytes(p[2:4], "big")      # IPv4 Total Length
    elif tl == 0x86DD and len(p) >= 6:
        info["dados_uteis"] = 40 + int.from_bytes(p[4:6], "big")  # IPv6 header + Payload Length
    elif tl == 0x0806:
        info["dados_uteis"] = 28                                  # ARP sobre Ethernet/IPv4
    if info["dados_uteis"] is not None:
        info["pad"] = max(len(p) - info["dados_uteis"], 0)
    return info


def dump_hex(raw, limite=64):
    linhas = []
    for i in range(0, min(len(raw), limite), 16):
        bloco = raw[i:i + 16]
        hexa = " ".join(f"{x:02x}" for x in bloco)
        linhas.append(f"  {i:04x}  {hexa}")
    if len(raw) > limite:
        linhas.append(f"  ... (+{len(raw) - limite} bytes)")
    return "\n".join(linhas)


def descobrir_rede(iface_nome="Ethernet"):
    """Retorna a interface de captura/injeção, o MAC/IP do host e o gateway.

    Neste PC a placa física ("Ethernet") está ligada a um switch virtual do
    Hyper-V, então o IP fica na "vEthernet (Hyper-V) 2" (mesmo MAC). Por isso
    o IP vem da rota padrão e a interface de injeção é escolhida pelo nome.
    """
    from scapy.all import conf, getmacbyip

    iface = conf.ifaces.dev_from_name(iface_nome)
    _, host_ip, gw_ip = conf.route.route("8.8.8.8")
    gw_mac = getmacbyip(gw_ip) if gw_ip and gw_ip != "0.0.0.0" else None
    return {
        "iface": iface,
        "host_mac": iface.mac,
        "host_ip": host_ip,
        "gw_ip": gw_ip,
        "gw_mac": gw_mac,
    }
