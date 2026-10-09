# Atividade 06 – Testes com RIP, OSPF e BGP

**Nome:** Matheus Milanezi
**Disciplina:** Redes de Computadores: Internetworking, Roteamento e Transmissão
**Ferramenta:** Cisco Packet Tracer 9.0.1

> **Escopo desta entrega:** por motivo de saúde, não foi possível concluir todas as etapas do roteiro dentro do prazo. Foi executado integralmente o **teste com RIP** (seção 3), incluindo tabela de rotas, análise da métrica, ping e traceroute, além de um problema de cabeamento identificado e corrigido durante o experimento (seções 2 e 8). Os testes com **OSPF**, **alteração de custo** e **BGP** **não foram executados**; as seções 4, 5 e 6 registram o que ficou preparado para eles, e estão explicitamente marcadas como não executadas. Nenhum resultado não obtido foi apresentado como se tivesse sido.

---

## 1. Objetivo

Investigar na prática o funcionamento dos protocolos de roteamento RIP, OSPF e BGP no Cisco Packet Tracer, comparando a formação das tabelas de roteamento, as métricas ou atributos usados por cada protocolo e o caminho fim-a-fim escolhido em cada caso.

---

## 2. Ambiente e topologia

Para os testes com RIP e OSPF foi reaproveitada a topologia da Atividade 05 (mesma figura do enunciado): 5 roteadores (A, B, C, D e E), 2 switches e 7 redes IPv4. Modelos: 2911 em A, B e E (3 interfaces Gigabit) e 1941 em C e D (2 interfaces). Como na Atividade 05, um Server1 e um Laptop1 ocupam as posições de PC3 e PC2 da figura original, dentro das mesmas redes.

### Endereçamento

| Dispositivo / Interface | Endereço | Máscara | Liga em |
|---|---|---|---|
| A – Gi0/0 | 192.168.1.1 | 255.255.255.0 | PC0 |
| A – Gi0/1 | 192.168.7.1 | 255.255.255.0 | Switch0 (rede A-B-C) |
| A – Gi0/2 | 192.168.9.1 | 255.255.255.0 | Switch1 (rede A-D-E) |
| B – Gi0/0 | 192.168.7.2 | 255.255.255.0 | Switch0 |
| B – Gi0/1 | 192.100.0.1 | 255.255.255.0 | E |
| B – Gi0/2 | 192.168.2.1 | 255.255.255.0 | PC1 |
| C – Gi0/0 | 192.168.7.3 | 255.255.255.0 | Switch0 |
| C – Gi0/1 | 192.168.8.1 | 255.255.255.0 | D |
| D – Gi0/0 | 192.168.8.2 | 255.255.255.0 | C |
| D – Gi0/1 | 192.168.9.2 | 255.255.255.0 | Switch1 |
| E – Gi0/0 | 192.100.0.2 | 255.255.255.0 | B |
| E – Gi0/1 | 192.168.9.3 | 255.255.255.0 | Switch1 |
| E – Gi0/2 | 192.168.3.1 | 255.255.255.0 | Server1 |
| PC0 | 192.168.1.10 | 255.255.255.0 | gateway 192.168.1.1 |
| PC1 | 192.168.2.10 | 255.255.255.0 | gateway 192.168.2.1 |
| Server1 | 192.168.3.10 | 255.255.255.0 | gateway 192.168.3.1 |
| Laptop1 | 192.168.9.10 | 255.255.255.0 | gateway 192.168.9.1 |

### Correção de cabeamento identificada no roteador B

Durante a configuração do RIP foi descoberto que, no roteador B, os cabos estavam conectados em portas diferentes daquelas que haviam recebido os endereços IP na Atividade 05:

| Porta do B | Cabo fisicamente conectado a | IP que estava configurado | IP correto para aquela porta |
|---|---|---|---|
| Gi0/0 | Switch0 | 192.168.2.1 | 192.168.7.2 |
| Gi0/1 | E | 192.168.7.2 | 192.100.0.1 |
| Gi0/2 | PC1 | 192.100.0.1 | 192.168.2.1 |

As três interfaces apareciam como *up/up* (havia cabo conectado em todas), mas cada uma estava anunciando e recebendo tráfego na rede errada. O problema foi corrigido reatribuindo os endereços às portas corretas. O diagnóstico completo está na seção 8.

**Evidência:** print do `show ip interface brief` no roteador B após a correção e dos pings para 192.168.7.1 (A) e 192.100.0.2 (E), com 100% de sucesso

### Preparação comum aos testes

Antes de configurar os protocolos dinâmicos, todas as rotas estáticas da Atividade 05 foram removidas dos cinco roteadores. Isso é necessário porque a rota estática tem distância administrativa 1, contra 120 do RIP e 110 do OSPF: se ela permanecer, continua sendo a rota escolhida e as rotas aprendidas dinamicamente não aparecem na tabela, mesmo com o protocolo funcionando corretamente. Após a remoção, `show ip route` passou a exibir apenas rotas `C` (conectadas) e `L` (locais) em todos os roteadores.

---

## 3. Teste do protocolo RIP

### Configuração

RIPv2 com `no auto-summary` nos cinco roteadores, anunciando todas as redes diretamente conectadas. Exemplo do roteador A:

```
router rip
 version 2
 no auto-summary
 network 192.168.1.0
 network 192.168.7.0
 network 192.168.9.0
```

### Redes aprendidas e próximo salto

`show ip route` no roteador A:

```
R    192.100.0.0/24 [120/1] via 192.168.9.3, GigabitEthernet0/2
                    [120/1] via 192.168.7.2, GigabitEthernet0/1
     192.168.1.0/24 is variably subnetted, 2 subnets, 2 masks
C       192.168.1.0/24 is directly connected, GigabitEthernet0/0
L       192.168.1.1/32 is directly connected, GigabitEthernet0/0
R    192.168.2.0/24 [120/1] via 192.168.7.2, GigabitEthernet0/1
R    192.168.3.0/24 [120/1] via 192.168.9.3, GigabitEthernet0/2
     192.168.7.0/24 is variably subnetted, 2 subnets, 2 masks
C       192.168.7.0/24 is directly connected, GigabitEthernet0/1
L       192.168.7.1/32 is directly connected, GigabitEthernet0/1
R    192.168.8.0/24 [120/1] via 192.168.9.2, GigabitEthernet0/2
                    [120/1] via 192.168.7.3, GigabitEthernet0/1
     192.168.9.0/24 is variably subnetted, 2 subnets, 2 masks
C       192.168.9.0/24 is directly connected, GigabitEthernet0/2
L       192.168.9.1/32 is directly connected, GigabitEthernet0/2
```

**Evidência:** print do `show ip route` no roteador A.

Todas as quatro redes não conectadas diretamente ao A foram aprendidas via RIP (código `R`), cada uma apontando para a interface do roteador vizinho usado como próximo salto: 192.168.2.0/24 via 192.168.7.2 (B), 192.168.3.0/24 via 192.168.9.3 (E), e as redes 192.100.0.0/24 e 192.168.8.0/24 com **dois próximos saltos cada** (balanceamento de carga entre caminhos de mesmo custo).

### Métrica e número de saltos

Todas as rotas acima aparecem como `[120/1]`: 120 é a distância administrativa do RIP e 1 é a métrica, ou seja, **1 salto**. Isso corresponde exatamente à topologia: a partir do A, todas essas redes estão atrás de um único roteador vizinho (B, C, D ou E). O `show ip protocols` confirmou a configuração: RIP versão 2 no envio e na recepção, `Automatic network summarization is not in effect` e `Maximum path: 4`.

A relação direta entre métrica e número de saltos fica mais visível no roteador C, que está mais distante da rede do Server1 (`show ip route rip`):

```
R    192.100.0.0/24 [120/1] via 192.168.7.2, GigabitEthernet0/0
R    192.168.1.0/24 [120/1] via 192.168.7.1, GigabitEthernet0/0
R    192.168.2.0/24 [120/1] via 192.168.7.2, GigabitEthernet0/0
R    192.168.3.0/24 [120/2] via 192.168.8.2, GigabitEthernet0/1
                    [120/2] via 192.168.7.1, GigabitEthernet0/0
                    [120/2] via 192.168.7.2, GigabitEthernet0/0
R    192.168.9.0/24 [120/1] via 192.168.8.2, GigabitEthernet0/1
                    [120/1] via 192.168.7.1, GigabitEthernet0/0
```

**Evidência:** print do `show ip route rip` no roteador C

A rede 192.168.3.0/24 aparece com métrica 2 por **três caminhos diferentes** (via D, via A e via B), todos com o mesmo número de saltos. Como o RIP considera apenas a contagem de saltos, ele não tem nenhum critério para preferir um desses caminhos aos outros e instala os três simultaneamente.

### Ping e traceroute entre PCs de redes diferentes

Teste entre **PC0** (192.168.1.10, rede 192.168.1.0/24) e **Server1** (192.168.3.10, rede 192.168.3.0/24), o mesmo par usado na Atividade 05.

`tracert 192.168.3.10` no PC0:

```
1   0 ms   0 ms   0 ms   192.168.1.1
2   *      0 ms   0 ms   192.168.9.3
3   *      0 ms   0 ms   192.168.3.10
```

`ping 192.168.3.10` no PC0: 4 pacotes enviados, 4 recebidos, 0% de perda, **TTL=126**.

**Evidência:** prints do traceroute e do ping no PC0.

### Caminho fim-a-fim e comparação com a tabela

O caminho observado foi **PC0 → A → E → Server1**. Ele corresponde exatamente à tabela de roteamento do A, onde a rede 192.168.3.0/24 aparece com próximo salto 192.168.9.3, que é a interface do roteador E voltada para o Switch1. O TTL=126 do ping confirma o mesmo resultado por outra via: partindo de 128, foram decrementadas 2 unidades, ou seja, o pacote atravessou exatamente 2 roteadores (A e E). Os `*` que aparecem na primeira sonda dos saltos 2 e 3 do traceroute são consumidos pela resolução ARP, comportamento normal do Packet Tracer.

---

## 4. Teste do protocolo OSPF — **não executado**

Esta etapa não foi executada dentro do prazo de entrega, por motivo de saúde. Não há, portanto, adjacências, tabela de rotas, custo ou traceroute a apresentar.

O que ficou preparado: um arquivo `.pkt` derivado do teste com RIP já corrigido, e a configuração de OSPF em área única para os cinco roteadores, com router-id fixo por roteador (A = 1.1.1.1, B = 2.2.2.2, C = 3.3.3.3, D = 4.4.4.4, E = 5.5.5.5) para facilitar a identificação de cada vizinho. Exemplo do roteador A:

```
no router rip
router ospf 1
 router-id 1.1.1.1
 network 192.168.1.0 0.0.0.255 area 0
 network 192.168.7.0 0.0.0.255 area 0
 network 192.168.9.0 0.0.0.255 area 0
```

Verificações previstas: `show ip ospf neighbor`, `show ip route ospf`, `show ip ospf interface GigabitEthernet0/2` (para registrar o custo) e `tracert` a partir do PC0 para o mesmo destino usado no teste com RIP.

---

## 5. Alteração do custo de uma rota OSPF — **não executado**

Etapa dependente da anterior, também não executada. A interface escolhida seria a **GigabitEthernet0/2 do roteador A**, que é a saída do A em direção ao roteador E e pertence ao caminho observado no teste com RIP:

```
interface GigabitEthernet0/2
 ip ospf cost 100
```

---

## 6. Teste do protocolo BGP — **não executado**

Esta etapa exigia a montagem de uma segunda topologia, com três Sistemas Autônomos, e não foi realizada. O planejamento de endereçamento e de configuração ficou pronto e é apresentado abaixo apenas como registro do que estava preparado.

| Dispositivo / Interface | Endereço | Liga em |
|---|---|---|
| R1 (AS100) – Fa0/0 | 12.12.12.1/24 | R2 |
| R1 – Fa0/1 | 10.0.0.1/24 | PC1 |
| R1 – Loopback0 | 1.1.1.1/32 | — |
| R2 (AS200) – Fa0/0 | 12.12.12.2/24 | R1 |
| R2 – Fa0/1 | 172.16.0.1/24 | PC2 |
| R2 – Fa1/0 | 23.23.23.2/24 | R3 |
| R2 – Loopback0 | 2.2.2.2/32 | — |
| R3 (AS300) – Fa0/0 | 23.23.23.3/24 | R2 |
| R3 – Fa0/1 | 192.168.0.1/24 | PC3 |
| R3 – Loopback0 | 3.3.3.3/32 | — |

Configuração prevista para o R1 (AS100), com as sessões eBGP e o anúncio das redes internas:

```
router bgp 100
 neighbor 12.12.12.2 remote-as 200
 network 10.0.0.0 mask 255.255.255.0
 network 1.1.1.1 mask 255.255.255.255
```

---

## 7. Comparação entre RIP, OSPF e BGP

A tabela abaixo distingue o que foi **observado no experimento** do que é apenas **expectativa teórica**, já que apenas o RIP foi executado.

| Protocolo | Tipo | Como escolhe a rota | Código na tabela | Caminho observado |
|---|---|---|---|---|
| **RIP** | IGP, vetor de distância | Menor número de saltos; em caso de empate, instala todos os caminhos empatados | `R`, distância administrativa 120 — *observado* | PC0 → A → E → Server1 — *observado* |
| **OSPF** | IGP, estado de enlace (cálculo SPF sobre a topologia completa) | Menor custo acumulado, derivado da largura de banda das interfaces de saída | `O`, distância administrativa 110 — *não verificado* | *não executado* |
| **BGP** | EGP, vetor de caminho | Atributos e políticas entre Sistemas Autônomos, entre eles o AS_PATH | `B`, distância administrativa 20 no eBGP — *não verificado* | *não executado* |

### Qual diferença você observou entre a métrica usada pelo RIP e o custo usado pelo OSPF?

No RIP, a métrica observada foi a contagem de saltos: a partir do roteador A, todas as redes remotas apareceram com métrica 1, porque estão a um roteador de distância, e no roteador C a rede 192.168.3.0/24 apareceu com métrica 2, por estar a dois roteadores. É um número que depende apenas de **quantos** roteadores o pacote atravessa, e não das características dos enlaces.

A consequência prática disso apareceu no experimento: no roteador C, a rede 192.168.3.0/24 foi instalada com três próximos saltos diferentes, todos com métrica 2. Como o RIP não tem nenhuma informação além da contagem de saltos, ele não consegue distinguir esses caminhos entre si.

Não é possível completar a comparação com o custo do OSPF, porque esse teste não foi executado.

### Ao alterar o custo OSPF, o caminho mudou? Explique com base na tabela de roteamento e no traceroute.

Não é possível responder: a alteração de custo não foi executada, e responder com base em expectativa teórica não atenderia ao que o roteiro pede (resultados do próprio experimento).

### No BGP, qual informação do AS_PATH permite identificar por quais Sistemas Autônomos a rota passa?

O teste com BGP não foi executado, então não há saída de `show ip bgp` a analisar. Conceitualmente, o AS_PATH é a lista dos números de Sistema Autônomo registrada em cada rota, lida da esquerda para a direita: começa no AS vizinho que repassou o anúncio e termina no AS que originou a rota. É essa lista que permite saber por quais AS a rota passou, e é também o mecanismo de prevenção de loops, já que um roteador descarta qualquer anúncio cujo AS_PATH já contenha o número do seu próprio AS. Esta resposta é conceitual e **não foi validada** no experimento.

### Em uma frase, explique por que RIP/OSPF e BGP são usados em contextos diferentes.

RIP e OSPF são protocolos de roteamento interno (IGP), usados dentro de uma rede administrada por uma única organização, onde o objetivo é escolher automaticamente o caminho tecnicamente mais eficiente; já o BGP é um protocolo externo (EGP), usado entre Sistemas Autônomos diferentes, onde a escolha da rota depende de políticas e acordos entre organizações, e não apenas de distância ou velocidade de enlace.

---

## 8. Uso de Inteligência Artificial

**Ferramenta utilizada:** Claude (Anthropic), via Claude Code.

**Etapas em que ajudou:** planejamento da sequência de testes; preparação dos comandos de configuração de RIP, OSPF e BGP; previsão dos resultados esperados antes de cada execução, para comparação com o que realmente apareceu na tela; e diagnóstico de um problema de conectividade encontrado durante o experimento.

**Hipótese sugerida pela IA antes da execução:** a de que, na tabela do roteador A, a rede 192.168.3.0/24 apareceria via 192.168.9.3 (roteador E) com métrica 1, e as redes 192.100.0.0/24 e 192.168.8.0/24 apareceriam com dois próximos saltos cada, por empate de saltos. Essa previsão foi **confirmada integralmente** pelo `show ip route` do roteador A e pelo traceroute do PC0, que mostrou o caminho PC0 → A → E → Server1.

A IA também previu que RIP e OSPF escolheriam o mesmo caminho nesta topologia, por todos os enlaces serem Gigabit Ethernet, e que a diferença entre os dois só ficaria visível ao alterar manualmente o custo de uma interface. Essa hipótese **não pôde ser verificada**, porque o teste com OSPF não foi executado.

**Sugestão que precisou ser corrigida com base no experimento:** ao configurar o RIP, a rede 192.168.2.0/24 (atrás do roteador B) não apareceu na tabela do roteador A, e a rede 192.100.0.0/24 apareceu com apenas um caminho em vez de dois. A primeira hipótese levantada foi a mais simples — que o RIP não teria sido configurado no roteador B. Essa hipótese foi **descartada experimentalmente**: o `show ip protocols` no B mostrou o RIP corretamente configurado, com as três redes anunciadas, mas com a lista "Routing Information Sources" vazia, ou seja, o B não recebia anúncio de nenhum vizinho. Os testes seguintes confirmaram o isolamento: `ping 192.168.7.1` (roteador A) e `ping 192.100.0.2` (roteador E) a partir do B falharam com 0% de sucesso, mesmo sendo vizinhos diretos.

**Como o problema real foi identificado e validado:** ativando a opção *Options → Preferences → Always Show Port Labels* do Packet Tracer, foi possível ver no diagrama em qual porta cada cabo estava conectado e comparar com os endereços configurados. Ficou claro que os três cabos do roteador B estavam em portas trocadas em relação aos IPs (tabela da seção 2): a porta ligada ao Switch0 tinha o endereço da rede do PC1, a ligada ao roteador E tinha o endereço da rede do Switch0, e assim por diante. Todas apareciam como *up/up*, porque havia cabo conectado, o que mascarava o erro. Após reatribuir os endereços às portas corretas, os mesmos pings passaram de 0/5 para **5/5**, e a rede 192.168.2.0/24 apareceu na tabela do roteador A em menos de 30 segundos.

**Observação relevante para a disciplina:** esse erro de cabeamento já existia na Atividade 05 e passou despercebido porque o único teste realizado lá (PC0 → Server1) percorre o caminho A → E, que não passa pelo roteador B. Uma rota estática permanece na tabela de roteamento mesmo quando o próximo salto está inalcançável, pois não depende de nenhuma troca de mensagens para ser instalada. O RIP, ao contrário, só instala uma rota se receber efetivamente o anúncio do vizinho, e por isso expôs a falha imediatamente.

**Validação:** nenhuma sugestão da IA foi aceita sem verificação. Cada previsão foi comparada com a saída real dos comandos no Packet Tracer, e a hipótese inicial sobre o roteador B foi descartada justamente por não resistir a essa comparação.

---

## 9. Conclusão

O teste executado permitiu observar na prática o funcionamento do RIP: as redes remotas foram aprendidas automaticamente, sem nenhuma rota configurada manualmente, cada uma com o código `R`, distância administrativa 120 e métrica igual ao número de roteadores até o destino. O caminho fim-a-fim entre PC0 e Server1 (PC0 → A → E → Server1) foi confirmado por três evidências independentes: a tabela de roteamento do roteador A, o traceroute e o TTL de 126 no ping, que indica a passagem por exatamente dois roteadores. Esse é o mesmo caminho que havia sido configurado manualmente com rotas estáticas na Atividade 05, o que mostra que, nesta topologia, o protocolo dinâmico chegou sozinho ao resultado que antes precisou ser calculado e digitado roteador a roteador.

A limitação do critério do RIP também ficou evidente: no roteador C, a rede do Server1 foi instalada com três próximos saltos diferentes, todos com métrica 2, porque a contagem de saltos não oferece nenhum elemento para desempatar caminhos com o mesmo número de roteadores. É exatamente esse limite que o custo do OSPF, baseado na largura de banda, se propõe a resolver — comparação que ficou pendente, assim como o teste com BGP, por não terem sido executados dentro do prazo.

O resultado mais instrutivo do experimento foi involuntário. Um erro de cabeamento no roteador B, presente desde a Atividade 05, permaneceu invisível enquanto a rede funcionava com rotas estáticas, e apareceu imediatamente ao ser configurado o RIP. A rota estática é apenas uma instrução armazenada na tabela e continua lá mesmo que o vizinho indicado esteja inalcançável; já o protocolo dinâmico depende de troca real de mensagens com esse vizinho, e por isso só instala rotas que correspondem a caminhos que de fato existem. Na prática, o RIP funcionou como um teste de consistência da própria topologia física.
