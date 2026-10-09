# Laboratório IPv6 — Atividade 03 (Redes de Computadores, UNISINOS)

Ambiente reprodutível para a Atividade 03 (SLAAC, NDP, ICMPv6), implementado com Docker Compose no lugar do script de referência baseado em `ip netns` do roteiro. Este documento explica as decisões de design e como reproduzir o experimento.

OBS: Em /lab/logs há os logs usados para construir o relatório, caso o professor queira analisar, ao rodar run-lab.sh esses registros são substituídos, deixei para caso o professor queira dar uma olhada. 

## Topologia

```
[c1] ----\
          eth0 -- [r1 / lab-net bridge]
[c2] ----/
```

Três containers Ubuntu 24.04 (r1, c1, c2) conectados a uma única rede Docker (`lab-net`), simulando o mesmo segmento L2 do ambiente de referência (bridge `br-lab` + namespaces). r1 atua como roteador IPv6, anunciando o prefixo do laboratório via `radvd`.

## Decisão de design: por que dois prefixos IPv6 diferentes

A rede Docker (`lab-net`) é criada com `enable_ipv6: true` e IPAM próprio no subnet `fd00:dead:beef::/64`. O prefixo efetivamente testado no laboratório é outro: `fd00:1234:5678::/64`, anunciado por `radvd` em r1.

Isso é proposital. Se a rede Docker usasse o mesmo prefixo do laboratório, o endereço IPv6 atribuído automaticamente pelo IPAM do Docker a cada container seria indistinguível de um endereço obtido por SLAAC — o que invalidaria a evidência pedida pelo roteiro (que exige comprovar que o endereço veio de *Router Advertisement*, não de atribuição estática/IPAM). Usando um subnet diferente para cada mecanismo, cada container termina com dois endereços globais visivelmente distintos:

- `fd00:dead:beef::x` — atribuído pelo IPAM do Docker (flag `nodad`, sem indicação de origem dinâmica)
- `fd00:1234:5678:...` — obtido via SLAAC (flags `dynamic mngtmpaddr` no `ip -6 addr show`, marcação do próprio kernel Linux para endereço autoconfigurado)

## Pré-requisitos

- Docker Desktop (Windows/Mac, com backend WSL2) ou Docker Engine (Linux)
- Docker Compose v2 (`docker compose`, incluso no Docker Desktop)
- Um shell com Bash para rodar `run-lab.sh` (no Windows: Git Bash, incluso na instalação do Git)

## Como reproduzir

```bash
cd lab
bash run-lab.sh
```

O script:
1. Sobe os três containers (`docker compose up -d --build`)
2. Mostra o ambiente (interfaces, MTU) — seção 1 do relatório
3. Mostra os endereços link-local de c1/c2 antes de qualquer RA — seção 2.2
4. Configura r1 (endereço ULA + `radvd`) e aguarda o SLAAC em c1/c2 — seção 2.3
5. Inicia captura de ICMPv6 em background (`tcpdump`, salvo em `.pcap`) — seção 2.4
6. Executa ping (link-local e ULA), tabela de vizinhança (NDP) e teste de vazão com `iperf3` — seção 2.5
7. Encerra a captura e imprime um resumo

Todos os passos são logados em `logs/*.log`; a captura de pacotes fica em `logs/icmpv6-capture.pcap` (abrir no Wireshark, filtro `icmpv6.type == 134 || icmpv6.type == 135 || icmpv6.type == 136`).

## Estrutura de arquivos

```
lab/
├── Dockerfile          # Ubuntu 24.04 + iproute2, radvd, tcpdump, iperf3
├── docker-compose.yml  # serviços r1/c1/c2 + rede lab-net
├── radvd.conf           # anuncia o prefixo fd00:1234:5678::/64 (SLAAC)
├── scripts/
│   └── setup-router.sh # configura endereço ULA e inicia radvd em r1
├── run-lab.sh           # orquestra todo o experimento e gera os logs
└── logs/                 # gerado pela execução: *.log + icmpv6-capture.pcap
```

## Limpeza do ambiente

```bash
docker compose down
```

## Observação sobre sysctls em containers

O Docker só permite alterar em runtime (`sysctl -w`) os parâmetros que já foram declarados em `sysctls:` no `docker-compose.yml` na subida do container; qualquer outro retorna erro de sistema de arquivos somente leitura. Por isso, `forwarding` (em r1) e `accept_ra` (em todos os serviços) são declarados antecipadamente no `docker-compose.yml`, não configurados via comando manual depois.
