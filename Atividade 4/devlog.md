# Devlog — Atividade 04 (ICMPv4/ICMPv6)

> Notas cronológicas de decisões, testes e problemas, pra virar base da seção de relatório
> (análise crítica + uso de IA) quando formos redigir o `relatorio.md` final.

## Decisões de planejamento

- **Reaproveitamento da Atividade 03**: em vez de mexer na pasta `Atividade 3/`, ela foi mantida intacta como arquivo (devlogs, README, scripts como estavam na entrega). Os arquivos reutilizáveis (`Dockerfile`, `docker-compose.yml`, `radvd.conf`, `scripts/`, `run-lab.sh`, `README.md`) foram **copiados** para `Atividade 4/lab/` e evoluídos lá.
- **Roteador dual-stack em cadeia, não roteadores separados por protocolo**: decisão de usar `c1 -- r1 -- r2 -- c2` com r1 e r2 roteando IPv4 e IPv6 ao mesmo tempo, em vez de um roteador só-v4 e outro só-v6. Motivo: mais realista (roteadores reais fazem isso), menos containers, e permite comparar TTL/Hop Limit dos dois protocolos na mesma rota física.
- **Sem DNS ou serviços extras**: decidido manter o escopo estritamente no que o roteiro da Atividade 04 pede (ICMP/ICMPv6, 2 cenários, 10 perguntas, tabela comparativa). DNS não é mencionado no roteiro.
- **Por que precisávamos de 2 roteadores em série, não 1**: o roteiro pede provocar um `ICMP Time Exceeded` via TTL baixo. Isso só acontece quando um pacote passa por um roteador que precisa decrementar o TTL e descartar — hosts no mesmo segmento L2 (como c1/c2 estavam na Atividade 03) não geram esse erro, porque o host de destino não decrementa TTL. Por isso a topologia precisou de sub-redes diferentes conectadas por roteadores reais.

## Topologia final

```
[c1] --net-c1-- [r1] --net-transit-- [r2] --net-c2-- [c2]
```

- **net-c1**: IPv4 `192.0.2.0/24` (RFC 5737 TEST-NET-1) + IPv6 `fd00:1234:5678:1::/64` (radvd em r1)
- **net-transit** (r1↔r2): IPv4 `198.51.100.0/24` (TEST-NET-2) + IPv6 `fd00:1234:5678:ffff::/64`
- **net-c2**: IPv4 `203.0.113.0/24` (TEST-NET-3) + IPv6 `fd00:1234:5678:2::/64` (radvd em r2)
- Endereços fixos: c1=192.0.2.11, r1=192.0.2.1/198.51.100.1, r2=198.51.100.2/203.0.113.1, c2=203.0.113.12.
- Cada rede Docker também tem um subnet IPv6 "decoy" (`fd00:dead:beef:N::/64`) pro IPAM do Docker, mesmo padrão da Atividade 03, pra nunca confundir endereço do Docker com endereço via SLAAC/radvd.
- `scripts/setup-router.sh` detecta automaticamente qual interface é qual (por IP, não por nome tipo eth0/eth1) e configura endereço IPv6 real, rota estática pra sub-rede remota, e radvd — tudo baseado no hostname (r1 ou r2).

## Bug encontrado e corrigido: IPv6 quebrado entre c1 e c2

**Sintoma:** IPv4 atravessou os dois roteadores de primeira (funcionou), mas IPv6 dava 100% de perda entre c1 e c2.

**Causa:** `c1` tinha duas rotas padrão IPv6 com a **mesma métrica** (1024): uma real, aprendida via RA do r1 (`proto ra`), e uma "fantasma" adicionada automaticamente pelo próprio Docker (apontando pro subnet decoy `fd00:dead:beef:1::1`, que não leva a lugar nenhum). O kernel escolheu a rota errada para destinos fora do link local.

**Correção:** remover manualmente a rota padrão do Docker em c1 e c2 (`ip -6 route del default via fd00:dead:beef:X::1`), deixando só a rota real aprendida via RA.

**Por que isso não apareceu na Atividade 03:** lá só existia uma rede (sem múltiplos roteadores/sub-redes), então mesmo com a rota decoy presente, não havia ambiguidade prática — o tráfego era só local, nunca precisou de rota padrão de verdade. Esse problema só surgiu porque agora existe tráfego genuinamente roteado entre sub-redes diferentes.

## Testes validados

- Ping IPv4 c1→c2 (TTL padrão): sucesso, TTL chega em 62 (64 - 2 saltos).
- Ping IPv6 c1→c2 (Hop Limit padrão): sucesso, mesmo comportamento, hop limit 62.
- SLAAC continua funcionando em c1/c2 via radvd em r1/r2 (herdado da Atividade 03).
- **Escalonamento de TTL/Hop Limit (IPv4):**
  - TTL=1 → `Time to live exceeded` vindo de `192.0.2.1` (r1, interface do lado de c1)
  - TTL=2 → `Time to live exceeded` vindo de `198.51.100.2` (r2, interface do lado do trânsito)
  - TTL=3 → sucesso, chega em c2
- **Escalonamento de Hop Limit (IPv6):**
  - Hop Limit=1 → `Time exceeded: Hop limit` vindo de `fd00:1234:5678:1::1` (r1)
  - Hop Limit=2 → `Time exceeded: Hop limit` vindo de `fd00:1234:5678:ffff::2` (r2)
  - Hop Limit=3 → sucesso, chega em c2
- Detalhe interessante para a análise: em ambos os casos, o roteador responde com o endereço da interface relevante àquele salto (não sempre a mesma) — vale explorar isso na resposta da pergunta 7 do roteiro.

## `run-lab.sh` adaptado e validado (rodada completa, do zero)

O script foi reescrito para a nova topologia (`docker compose down` + `run-lab.sh` inteiro rodado do zero, sem nenhuma configuração manual prévia) e funcionou sem erros na primeira tentativa completa — já incorporando a correção do bug de rota IPv6 (seção "2.1" do script).

Sequência automatizada: sobe os 4 containers -> caracteriza ambiente (seção 1 do roteiro) -> configura r1/r2 -> corrige rotas -> aguarda SLAAC -> inicia captura (`tcpdump -i any` em r1, pega as duas interfaces dele de uma vez) -> gera tráfego do Cenário A (ping v4 e v6) -> escalona TTL/Hop Limit (1, 2, 3) -> encerra captura e mostra resumo.

**Detalhe técnico interessante da captura `-i any`:** usa o link-type `LINUX_SLL2` em vez de Ethernet puro — perde o MAC de verdade nos frames, mas em compensação anota **qual interface** e a **direção** (`In`/`Out`) de cada pacote. Isso deu uma visualização ótima do TTL expirando:

- TTL=1 (IPv4): só aparece em `eth0` (lado de c1), `Out`, resposta gerada localmente por r1 — o pacote nunca saiu pro `eth1` (lado do trânsito).
- TTL=2 (IPv4): aparece `eth1 In` (chegando de r2) e `eth0 Out` (saindo pra c1) — visualmente mostra o erro sendo *encaminhado de volta* por r1, não gerado por ele.
- Mesmo padrão se repete identico em IPv6 (Hop Limit 1 e 2), com os respectivos endereços `fd00:1234:5678:1::1` (r1) e `fd00:1234:5678:ffff::2` (r2) como origem do erro.

Essa distinção (erro gerado localmente vs. relayado) é material direto pra pergunta 7 do roteiro ("qual equipamento gerou a mensagem de erro? como você verificou isso?").

## Pendente

- [ ] Cenário B (Internet) — precisa rodar fora do Docker, direto no Windows host. Ainda não desenhado/testado.
- [ ] Tirar prints de tela de todas as evidências (dados já reais e capturados).
- [ ] Abrir o `.pcap` no Wireshark pra conferir Type/Code/Checksum/Identifier/Sequence Number pedidos nas perguntas 3 e 4.
- [ ] Responder as 10 perguntas da seção 5 e montar a tabela comparativa da seção 6 do roteiro.
- [ ] Escrever a seção de uso de IA (mesmo formato da Atividade 03: pergunta feita à IA antes do experimento, e como validada).
- Nota sobre endereçamento: usamos `192.0.2.11` pra c1 (igual à sugestão do roteiro) e `203.0.113.12` pra c2 (roteiro sugeria `192.0.2.12`, mas c2 agora fica em outra sub-rede por causa do redesenho com 2 roteadores) — adaptação justificável, vale documentar isso explicitamente no relatório.

## Cenário B (Internet real) — investigação do ambiente

**Ambiente identificado (via `ipconfig /all` no Windows host, fora do Docker):** entre vários adaptadores virtuais (Docker/WSL, VirtualBox, Radmin VPN, Teredo), a interface que carrega o tráfego de Internet de verdade é a **`vEthernet (Hyper-V) 2`** — nome estranho porque é um **Hyper-V External Switch em modo bridge**, criado pelo usuário pra poder dar IP fixo a VMs no Hyper-V. Esse tipo de switch tira a pilha IP da placa física (que passa a aparecer como "Não Conectado" no Windows, mesmo trafegando bilhões de bytes de verdade) e transfere pra um adaptador virtual, que é quem efetivamente tem o IP/DHCP/SLAAC. Detalhe curioso: o "2" no nome é porque a primeira tentativa de criar essa ponte falhou.

**Conectividade IPv6 nativa confirmada** (não é Teredo/túnel): endereço global `2804:d51:4764:7c00:.../64` (prefixo alocado pelo LACNIC, ISP brasileiro), mais um endereço temporário (privacidade, RFC 4941), gateway link-local real (`fe80::1`) e servidores DNS em IPv6 nativos. Existe também um adaptador Teredo (`2001:0:14c9:...`) como "pista falsa" — é o fallback automático do Windows quando não há IPv6 nativo, mas como há nativo, o Teredo fica sem uso real.

**Testes realizados (via PowerShell, fora do Docker):**
- `Test-NetConnection 8.8.8.8`: sucesso, RTT 20ms, via `vEthernet (Hyper-V) 2`, origem `192.168.1.2`.
- `Test-NetConnection 2606:4700:4700::1111` (Cloudflare): sucesso, RTT 17ms, origem `2804:d51:4764:7c00:65b:4891:a198:f7bf` (endereço global real, não Teredo).
- `ping -4 -n 5 8.8.8.8`: 5/5, média 22ms, TTL de resposta 113.
- `ping -6 -n 5 2606:4700:4700::1111`: 5/5, média 14ms. **Nota**: destinos diferentes (Google vs Cloudflare), então a diferença de latência não pode ser atribuída só ao protocolo — cuidado ao comparar no relatório.
- **Achado importante**: o `ping` do Windows não mostra Hop Limit na resposta IPv6 (diferente do IPv4, que mostra TTL) — só aparece na captura do Wireshark.

**Experimento de TTL/Hop Limit contra a Internet real (`ping -i N`, flag correta no Windows, não `-t`):**
- IPv4 TTL=1: erro de `192.168.1.254` (roteador de casa) — bate com o texto do comando.
- IPv4 TTL=2: erro de `177.2.165.1` (primeiro salto real do provedor, IP público de verdade) — bate com o texto do comando.
- IPv6 Hop Limit=1 e =2: **o texto do `ping.exe` mostrou incorretamente o próprio destino (Cloudflare) como remetente do erro** nos dois casos — isso é logicamente impossível (um pacote que expirou em 1-2 saltos não pode ter chegado ao destino final). Suspeita de bug de exibição do Windows para IPv6.

**Validação via Wireshark (não confiar no texto do comando, confiar na captura):** filtrando `icmpv6.type == 3` na captura ao vivo da interface `vEthernet (Hyper-V) 2`, os pacotes reais de `Time Exceeded` mostraram origens completamente diferentes do que o `ping.exe` exibiu:
- Hop Limit=1 → origem real `2804:d51:4764:7c00::1` (roteador de casa, mesmo prefixo /64 do host)
- Hop Limit=2 → origem real `2804:d50:1:3000::1` (prefixo diferente, roteador seguinte do provedor)

Confirmado: bug de exibição do `ping.exe` do Windows para mensagens de erro IPv6 (mostra o destino em vez do remetente real do erro). Ótimo exemplo prático pra pergunta 10 do roteiro ("resultado diferente da hipótese inicial") e pra reforçar, de novo, a lição de sempre validar contra a captura real, não confiar no texto de uma ferramenta.

**Bônus para a pergunta 8 do roteiro:** no painel de detalhes do Wireshark, o pacote de `Time Exceeded` mostra claramente o cabeçalho IPv6 original embutido (Hop Limit: 1, destino `2606:4700:4700::1111`) mais o ICMPv6 echo request original dentro do erro — evidência direta de que o host de origem consegue associar o erro ao tráfego que ele mesmo enviou.

## Sessão de retomada — Cenário B refeito e fechado

Ambiente recriado do zero com `run-lab.sh` (Cenário A revalidado, resultados idênticos aos de antes). Cenário B refeito com captura ao vivo no Wireshark, dessa vez **salva** em `Atividade 4/lab/logs/cenario-b-internet.pcapng` (~72MB, captura completa da sessão, não só o trecho filtrado).

**TTL=3 / Hop Limit=3 confirmado como silêncio real (não é bug nem atraso):** filtrando a captura em `ip.addr == 8.8.8.8 || ipv6.addr == 2606:4700:4700::1111 || icmp.type == 11 || icmpv6.type == 3`, os pacotes de request com TTL=3 (seq 48, 49, 50) e Hop Limit=3 (seq 98, 99, 100) aparecem marcados pelo próprio Wireshark como "(no response found!)" — ou seja, mesmo capturando tudo que passou pela interface, **nenhuma resposta chegou de volta** nos dois protocolos. Não é timeout do `ping`, é ausência real de qualquer pacote de retorno. Explicação provável: algum equipamento no terceiro salto tem política de não gerar (ou não deixar passar) erro ICMP — prática comum de rate-limiting/segurança em redes de backbone. Padrão idêntico em IPv4 e IPv6, ótima evidência simétrica pra comparação.

**Confirmado de novo (com números de frame reais) o bug de exibição do `ping.exe` em IPv6:**
- Hop Limit=1 (seq 92-94): origem real dos erros = `2804:d51:4764:7c00::1` (frames 24365, 24451, 24587)
- Hop Limit=2 (seq 95-97): origem real dos erros = `2804:d50:1:3000::1` (frames 24595, 24650, 24707)
- O `ping.exe` mostrou "Resposta de 2606:4700:4700::1111" (o destino) nos dois casos — errado, confirmado contra a captura duas vezes (ontem e hoje).

**Frames de referência para as perguntas 3 e 4 do roteiro (Echo Request/Reply "normal"):**
- IPv4: frame 7627 (request) / 7629 (reply) — `192.168.1.2 -> 8.8.8.8`, id=0x0001, seq=37.
- IPv6: frame 8239 (request) / 8243 (reply) — `2804:d51:4764:7c00:e8e7:7e4:4464:a0f -> 2606:4700:4700::1111`, id=0x0001, seq=91. Reply chega com hop limit=57 (o request saiu com 128, então o Cloudflare está a ~71 saltos "equivalentes" nesse cálculo — na real o hop limit de resposta é decidido pelo valor inicial do lado do Cloudflare, não dá pra inferir saltos direto daí sem saber o valor inicial deles; anotar isso com cuidado no relatório em vez de fazer conta errada).

**IPv4 TTL=1/2 confirmados de novo, mesmos endereços de ontem** (`192.168.1.254`, depois `177.2.165.1`) — infraestrutura real do provedor, estável entre sessões.

## Pendente (atualizado)

- [x] Recriar ambiente e refazer captura do Cenário B
- [x] Testar TTL=3/Hop Limit=3 e confirmar contra a captura (não é bug, é silêncio real)
- [x] Salvar o `.pcapng` do Cenário B
- [x] Identificar frames de Echo Request/Reply "limpos" para as perguntas 3 e 4
- [ ] Prints de tela de tudo (Cenário A e B) — dados já reais e confirmados, falta só o registro visual final pro relatório
- [ ] Responder as 10 perguntas + tabela comparativa da seção 6
- [ ] Seção de uso de IA (mesmo formato da Atividade 03: pergunta feita à IA antes do experimento, hipótese, validação)
