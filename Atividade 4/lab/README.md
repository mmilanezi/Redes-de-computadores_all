# Laboratório ICMPv4/ICMPv6 — Atividade 04 (Redes de Computadores, UNISINOS)

Ambiente reprodutível para a Atividade 04 (ICMP/ICMPv6, TTL/Hop Limit), continuação direta da Atividade 03. Reaproveita a base de containers Docker daquela atividade, evoluída para uma topologia com dois roteadores (necessária para provocar erros reais de TTL/Hop Limit). Este documento cobre o **Cenário A** (rede local, dentro do Docker); o **Cenário B** (Internet real) roda fora deste ambiente, direto no sistema operacional do host — ver `../relatorio.md` e `../devlog.md` para os detalhes e evidências desse cenário.

OBS: em `/lab/logs` há os logs e a captura usados para construir o relatório, caso o professor queira analisar. Rodar `run-lab.sh` de novo substitui esses arquivos.

## Topologia

```
[c1] --net-c1-- [r1] --net-transit-- [r2] --net-c2-- [c2]
```

Quatro containers Ubuntu 24.04 (c1, r1, r2, c2) em três redes Docker separadas. r1 e r2 são roteadores **dual-stack** (roteiam IPv4 e IPv6 ao mesmo tempo), cada um com uma interface para um cliente e outra para a rede de trânsito entre eles.

- **net-c1**: IPv4 `192.0.2.0/24` (RFC 5737 TEST-NET-1) + IPv6 `fd00:1234:5678:1::/64` (radvd em r1)
- **net-transit** (r1↔r2): IPv4 `198.51.100.0/24` (TEST-NET-2) + IPv6 `fd00:1234:5678:ffff::/64`
- **net-c2**: IPv4 `203.0.113.0/24` (TEST-NET-3) + IPv6 `fd00:1234:5678:2::/64` (radvd em r2)
- Endereços fixos: c1 = `192.0.2.11`, r1 = `192.0.2.1` / `198.51.100.1`, r2 = `198.51.100.2` / `203.0.113.1`, c2 = `203.0.113.12`

## Por que dois roteadores em série (diferença da Atividade 03)

Na Atividade 03, c1 e c2 ficavam no mesmo segmento L2 (um único roteador só para anunciar prefixo via SLAAC, sem rotear tráfego entre eles). Um `ping -t 1` nesse cenário simplesmente funcionaria normal — hosts finais não decrementam TTL, só roteadores decrementam ao encaminhar. Como a Atividade 04 pede para provocar um `ICMP Time Exceeded` de verdade, a topologia precisou de pelo menos um salto real no meio; usamos dois (r1 e r2) para poder demonstrar o erro acontecendo em saltos diferentes (TTL=1 falha em r1, TTL=2 falha em r2, TTL=3 chega ao destino).

## Decisão de design mantida da Atividade 03: subnets IPv6 "decoy"

Cada rede Docker tem um subnet IPv6 próprio do IPAM do Docker (`fd00:dead:beef:N::/64`), deliberadamente **diferente** dos prefixos reais anunciados via `radvd` (`fd00:1234:5678:1::/64` e `fd00:1234:5678:2::/64`). Isso evita confundir "endereço atribuído pelo Docker" com "endereço obtido por SLAAC" — mesma lógica da Atividade 03, agora replicada em três redes em vez de uma.

## Pré-requisitos

- Docker Desktop (Windows/Mac, com backend WSL2) ou Docker Engine (Linux)
- Docker Compose v2 (`docker compose`, incluso no Docker Desktop)
- Um shell com Bash para rodar `run-lab.sh` (no Windows: Git Bash, incluso na instalação do Git)

## Como reproduzir (Cenário A)

```bash
cd lab
bash run-lab.sh
```

O script:
1. Sobe os quatro containers (`docker compose up -d --build`)
2. Caracteriza o ambiente (interfaces, IPv4/IPv6, MTU, rotas) — seção 1 do relatório
3. Configura r1 e r2 via `scripts/setup-router.sh` (detecta a interface certa pelo IP, não por nome — cada roteador tem duas interfaces e a ordem `eth0`/`eth1` não é assumida)
4. Corrige a rota padrão IPv4 de c1/c2 (o Docker aponta para o próprio gateway dele, não para o roteador real) e remove a rota padrão IPv6 "fantasma" do IPAM do Docker em c1/c2 (bug real encontrado — ver `devlog.md`)
5. Aguarda o SLAAC em c1/c2
6. Inicia a captura ICMP/ICMPv6 em background (`tcpdump -i any` em r1, pegando as duas interfaces dele de uma vez)
7. Gera tráfego do Cenário A (ping IPv4 e IPv6 entre c1 e c2)
8. Escalona TTL/Hop Limit (1, 2, 3) nos dois protocolos, para provocar e observar o erro
9. Encerra a captura e imprime um resumo

Todos os passos ficam logados em `logs/*.log`; a captura fica em `logs/icmp-capture.pcap` (abrir no Wireshark, filtro `icmp || icmpv6`).

## Cenário B (Internet real) — fora deste ambiente

Executado diretamente no Windows, fora do Docker, usando a interface de rede real do host (ver caracterização completa em `../relatorio.md`). Resumo: `ping -4`/`ping -6` contra `8.8.8.8` e `2606:4700:4700::1111`, com captura ao vivo no Wireshark (não no `tcpdump`, que não existe nativamente no Windows). O experimento de TTL usa `-i <valor>` no Windows (não `-t`, que tem outro significado). Captura salva em `logs/cenario-b-internet.pcapng`.

## Estrutura de arquivos

```
lab/
├── Dockerfile           # Ubuntu 24.04 + iproute2, radvd, tcpdump
├── docker-compose.yml   # serviços c1/r1/r2/c2 + redes net-c1/net-transit/net-c2
├── scripts/
│   └── setup-router.sh  # configura r1 ou r2 (detecta o papel pelo hostname)
├── run-lab.sh            # orquestra o Cenário A completo e gera os logs
└── logs/                  # gerado pela execução: *.log, icmp-capture.pcap (Cenário A),
                            # cenario-b-internet.pcapng (Cenário B, capturado à parte)
```

## Limpeza do ambiente

```bash
docker compose down
```

## Observação sobre sysctls em containers

O Docker só permite alterar em runtime (`sysctl -w`) os parâmetros que já foram declarados em `sysctls:` no `docker-compose.yml` na subida do container; qualquer outro retorna erro de sistema de arquivos somente leitura. Por isso, `net.ipv4.ip_forward` e `net.ipv6.conf.all.forwarding` (em r1/r2) e `accept_ra` (em todos os serviços) são declarados antecipadamente no `docker-compose.yml`.

## Relatório completo

A análise técnica completa (endereços observados, capturas dos dois cenários, respostas justificadas às 10 perguntas do roteiro, tabela comparativa ICMPv4 vs ICMPv6 e análise crítica) está em `../relatorio.md`. O processo cronológico de decisões e erros está em `../devlog.md`.
