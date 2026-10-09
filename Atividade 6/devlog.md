# Devlog — Atividade 06 (RIP, OSPF e BGP)

> Anotações em ordem cronológica: decisões, resultados reais e diferenças em relação ao previsto no `planejamento.md`. Servem de base pro `relatorio.md`, principalmente pra seção de uso de IA.

## Preparação

- Topologia RIP/OSPF reaproveitada da Atividade 05: `atividade_05.pkt` copiado para `atividade_06_rip_ospf.pkt`.
- `show running-config | include ip route` nos 5 roteadores: as rotas estáticas **bateram 100%** com a lista deduzida da tabela de encaminhamento do relatório da Atividade 05.
- Tropeço de CLI: tentei rodar `show` dentro do `(config-if)#` e do `(config)#` e deu "Invalid input". O `show` só funciona no modo privilegiado (`A#`). A saída é usar `end` ou `do show ...`.
- Tropeço de arquivo: configurei, salvei com **Save As** como `atividade_06_rip.pkt` e depois reabri o arquivo base. A configuração "sumiu" porque o arquivo base continuava do jeito que estava antes. O Save As grava o estado num arquivo novo, e o arquivo original não muda.

## RIP (1ª coleta, arquivo `atividade_06_rip.pkt`)

- Ping PC0 → 192.168.3.10 depois do script 0: **funcionou** (2 timeouts de ARP, depois `TTL=126`). O previsto era falhar, mas o arquivo aberto já tinha o RIP salvo. Então quem fez a rede funcionar foi o RIP, não sobrou nenhuma rota estática (nenhum `S` na tabela de A). TTL 126 = 128 − 2 roteadores (A e E).
- `show ip route rip` em A:
  ```
  R  192.100.0.0/24 [120/1] via 192.168.9.3, Gi0/2
  R  192.168.3.0/24 [120/1] via 192.168.9.3, Gi0/2
  R  192.168.8.0/24 [120/1] via 192.168.9.2, Gi0/2
                    [120/1] via 192.168.7.3, Gi0/1
  ```
  - Bateu com a previsão: 192.168.3.0 via E com métrica 1, e 192.168.8.0 com **ECMP** via D e C.
  - `show ip protocols`: RIPv2 (send 2 / receive 2), "Automatic network summarization is not in effect", "Maximum path: 4", AD 120.
  - **Diferente do previsto:** a rota **192.168.2.0/24 (rede do PC1, atrás do B) não apareceu**, e 192.100.0.0 veio só via E (o previsto era ECMP via B e E). Ou seja, **nenhuma rota aprendida de 192.168.7.2 (B)**: o B não está anunciando RIP. Hipótese: o script do RIP não foi aplicado no B antes do Save As. Verificar com `show ip protocols` no B.
- Script RIP aplicado no B e esperei mais de 30 min: a rota **continuou sem aparecer**. Hipótese inicial (faltava configurar o B) **descartada**.
- Diagnóstico no B:
  - `show ip protocols`: RIP configurado certo (v2, redes 192.100.0.0 / 192.168.2.0 / 192.168.7.0), mas **"Routing Information Sources" vazio**. O B não recebe anúncio de ninguém.
  - `show ip route`: só rotas C e L, nenhum S (então não era rota estática sobrando).
  - `ping 192.168.7.1` (A) e `ping 192.100.0.2` (E): **0/5 nos dois**. Mesmo sendo vizinhos diretos.
  - A tabela do E também não tinha nada vindo do B (se o link B-E funcionasse, o E repassaria a 192.168.2.0 pro A com métrica 2).
- **Causa real:** ativando *Options → Preferences → Always Show Port Labels*, o desenho mostrou que os cabos do B estão em portas diferentes das que receberam os IPs:
  | Porta | Cabo vai pra | IP que estava | IP correto |
  |---|---|---|---|
  | Gi0/0 | Switch0 | 192.168.2.1 | 192.168.7.2 |
  | Gi0/1 | E | 192.168.7.2 | 192.100.0.1 |
  | Gi0/2 | PC1 | 192.100.0.1 | 192.168.2.1 |
  As interfaces ficavam up/up (cabo conectado), mas cada uma estava na rede errada.
- **Esse erro já existia na Atividade 05** e passou despercebido porque o único teste lá foi PC0 → Server1 (caminho A → E, que não passa pelo B). As rotas estáticas não "reclamam": ficam na tabela mesmo sem o próximo salto funcionar. Já o RIP depende de troca real de mensagens com o vizinho, e por isso expôs o problema na hora. Bom ponto pro relatório (protocolo dinâmico × estático).
- Correção: IPs trocados de interface pra acompanhar o cabeamento (`scripts/0b-corrigir-interfaces-B.txt`). O `no ip address` vem antes porque o IOS não deixa duas interfaces na mesma sub-rede nem por um instante ("overlaps with...").
- **Validado:** `show ip interface brief` no B → Gi0/0 192.168.7.2, Gi0/1 192.100.0.1, Gi0/2 192.168.2.1, todas up/up. `ping 192.168.7.1` (A) e `ping 192.100.0.2` (E) a partir do B: **5/5 nos dois** (antes 0/5).

## RIP (coleta final, depois da correção do B)

- `show ip route` em A (**bateu 100% com a previsão**):
  ```
  R  192.100.0.0/24 [120/1] via 192.168.9.3, Gi0/2
                    [120/1] via 192.168.7.2, Gi0/1     <- ECMP (E e B)
  R  192.168.2.0/24 [120/1] via 192.168.7.2, Gi0/1     <- apareceu depois da correção
  R  192.168.3.0/24 [120/1] via 192.168.9.3, Gi0/2
  R  192.168.8.0/24 [120/1] via 192.168.9.2, Gi0/2
                    [120/1] via 192.168.7.3, Gi0/1     <- ECMP (D e C)
  ```
  Nenhum `S`; só `C`, `L` e `R`.
- `show ip route rip` em C (extra, ECMP triplo **confirmado**):
  ```
  R  192.100.0.0/24 [120/1] via 192.168.7.2, Gi0/0
  R  192.168.1.0/24 [120/1] via 192.168.7.1, Gi0/0
  R  192.168.2.0/24 [120/1] via 192.168.7.2, Gi0/0
  R  192.168.3.0/24 [120/2] via 192.168.8.2, Gi0/1     (D → E)
                    [120/2] via 192.168.7.1, Gi0/0     (A → E)
                    [120/2] via 192.168.7.2, Gi0/0     (B → E)
  R  192.168.9.0/24 [120/1] via 192.168.8.2, Gi0/1
                    [120/1] via 192.168.7.1, Gi0/0
  ```
- `tracert 192.168.3.10` no PC0: `192.168.1.1` (A) → `192.168.9.3` (E) → `192.168.3.10`. Alguns `*` na 1ª sonda dos saltos 2 e 3 (ARP).
- `ping 192.168.3.10` no PC0: 4/4, **TTL=126** (2 roteadores).
- Caminho RIP = PC0 → A → E → Server1, o mesmo das rotas estáticas da Atividade 05.

## OSPF

- Arquivo: `atividade_06_ospf.pkt` (Save As a partir do RIP já corrigido).
- **Não executado.** Scripts prontos em `scripts/2-ospf/` e `scripts/3-custo-ospf/`, mas os comandos não chegaram a ser aplicados.

## BGP

- **Não executado.** Topologia nova não foi montada. Endereçamento e configurações planejadas em `planejamento.md` (seção 5) e scripts em `scripts/4-bgp/`.

## Fechamento da entrega (21/09/2026)

- Entrega parcial por motivo de saúde: só o RIP foi executado.
- `relatorio.md` fechado declarando explicitamente o que foi e o que não foi executado, sem apresentar previsão como resultado.
- Se houver prazo extra, a retomada é rápida: abrir `atividade_06_ospf.pkt`, colar `scripts/2-ospf/*` nos 5 roteadores, esperar ~1 min, coletar `show ip ospf neighbor`, `show ip route`, `show ip ospf interface Gi0/2` e o tracert do PC0. Depois `scripts/3-custo-ospf/A.txt` e repetir as duas últimas coletas. O BGP é a única parte que exige montar topologia nova.
