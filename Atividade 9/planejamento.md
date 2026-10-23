# Atividade 09 – Ethernet e MAC – Planejamento

## Ambiente
- Wireshark/TShark 4.6.8 + Npcap, Python 3.14 + Scapy 2.8.0 (`pip install scapy`).
- Interface de captura: **"Ethernet"** (Intel I219-V, nº 1 no Wireshark), MAC `e0:d5:5e:f4:8e:fa`.
  A placa física está ligada a um switch virtual do Hyper-V: o IP `192.168.1.2/24` fica na
  "vEthernet (Hyper-V) 2" (mesmo MAC). Capturar na física mostra o que realmente sai/entra pelo cabo.
- Gateway: `192.168.1.254`, MAC `cc:ed:21:66:c7:a0` (OUI `cc:ed:21` = Nokia Shanghai Bell).
- Driver Intel com "Prioridade de pacotes e VLAN" habilitada → a placa retira a tag 802.1Q na
  recepção antes do Npcap; por isso tráfego normal nunca aparece com tag.

## Scripts (`laboratório/`)
- `comum.py` – decodificação manual do cabeçalho MAC (regra Type/Length, tag 802.1Q, PAD, LLC).
- `injetar_quadros.py` – monta e envia 6 quadros de teste pela "Ethernet":
  `ethernet2` (EtherType 0x88B5, 59 B), `ieee8023` (802.3 + LLC TEST, Length 21 + PAD 25),
  `icmp` / `icmp-vlan` (mesmo ping sem/com tag VID 10, PCP 5), `max` / `max-vlan` (payload 1500).
  `--dry-run` só monta; sempre grava `quadros_gerados.pcap`.
- `analisar_captura.py` – resumo da captura (formatos, Types, VLAN, tamanhos por sentido, PAD) e
  detalhamento de quadros (`--quadros N ...`, números iguais aos do Wireshark; `--saida arquivo.txt`).

## Roteiro de execução (PowerShell como administrador, dentro de `laboratório/`)
1. Wireshark → capturar na interface **Ethernet**.
2. Gerar tráfego:
   - `arp -d *` e depois `ping 192.168.1.254 -n 4` → ARP request (broadcast) + reply, ICMP.
   - `ping 192.168.1.254 -f -l 1472 -n 2` → quadro de 1514 B (IP de 1500 = MTU).
   - `ping 192.168.1.254 -f -l 1473 -n 1` → "O pacote precisa ser fragmentado" (passa do MTU).
   - abrir um site qualquer (IPv4/IPv6).
3. `python injetar_quadros.py`
4. Parar a captura → salvar como `laboratório/captura_atividade9.pcapng`.
5. `python analisar_captura.py captura_atividade9.pcapng --saida saida_analise.txt`
   e depois `--quadros <nºs escolhidos>` para os quadros que vão para o relatório.
6. Prints no Wireshark (painel Ethernet II / 802.1Q / LLC expandido + bytes), filtros:
   `arp` · `icmp && !vlan` · `vlan` · `llc` · `eth.type == 0x88b5` · `frame.len >= 1514`.
   Dica: Exibir → Resolução de nomes → "Resolver endereços físicos" alterna entre
   `NokiaShangha_66:c7:a0` e o MAC cru.

## Previsões (feitas pela IA; o teste prévio de 21/10 confirmou, mas valem os dados da captura oficial)
- Tráfego normal: 100% Ethernet II (Type ≥ 0x0600: 0x86DD, 0x0800, 0x0806, 0xC0C0 do roteador); nenhum 802.3.
- Nenhuma tag VLAN no tráfego normal (driver retira na recepção).
- Quadros **enviados** pelo PC podem aparecer com < 60 B (ARP 42, TCP ACK 54): PAD e FCS são
  colocados pela placa depois do ponto de captura. Quadros **recebidos** têm ≥ 60 B (ex.: ARP reply
  do roteador = 60 B com 18 B de PAD), mas sem FCS (a placa confere e descarta).
- Máximo capturado: 1514 B sem tag / 1518 B com tag (1518 / 1522 com FCS).
- Quadro 802.3 injetado: Length = 0x0015 (21) mas área de dados = 46 → o Length separa dados do PAD.
- **Resultado inesperado do teste prévio:** o gateway respondeu também ao ping **com tag VID 10**
  (resposta sem tag). Hipóteses: o switch do roteador ignora/retira a tag, ou a tag não chegou ao
  cabo. Não dá para distinguir só com a captura deste PC (a placa retiraria uma tag na resposta).

## Checklist do relatório (PDF único)
- [x] Interface e método de captura
- [x] ≥ 3 quadros com campos Ethernet visíveis (MAC origem/destino, Type/Length)
- [x] Classificação Ethernet II × 802.3 com justificativa + como reconhecer o outro (quadro injetado)
- [x] Tamanhos: cabeçalho 14 B, payload 46–1500, preâmbulo 7 + SFD 1, FCS 4, por que não aparecem
- [x] VLAN: ausência no tráfego normal + quadro com tag (TPID 0x8100, TCI 0xA00A → PCP 5, DEI 0, VID 10), +4 B
- [x] Análise (3 perguntas da seção 5)
- [x] Uso de IA (ferramenta, etapas, verificação, exemplo confirmado/corrigido)
