# Roteiro do vídeo — demonstração do roteamento

**Duração alvo: 6 a 7 minutos.** O vídeo comprova que os três protocolos funcionam
e que escolhem caminhos diferentes sobre a mesma topologia.

## Antes de gravar

1. Deixe o Docker Desktop já iniciado (a subida dele não deve entrar no vídeo).
2. Abra **dois terminais** lado a lado no Git Bash, ambos em `Trabalho 1/repo`.
   O terminal da direita é usado só no bloco da falha.
3. **Obrigatório:** rode `./scripts/lab.sh preparar-host` antes de gravar. O Docker
   volta o `bridge-nf-call-iptables` para 1 toda vez que reinicia, e aí OSPF e RIP
   não formam vizinhança. (A imagem `trabalho1-frr:8.4.1` já está construída.)
4. Aumente a fonte do terminal (o avaliador precisa ler a saída).
5. Deixe este roteiro aberto numa terceira janela, fora da captura.

Tempos medidos no ensaio de 27/09: OSPF fica todo em Full em ~60 s, RIP instala
as rotas em ~35 s, BGP abre as sessões em ~3 s.

> Se algum comando demorar mais que o esperado, **não corte** — comente em voz alta
> o que está acontecendo. Convergência é o objeto do trabalho; esperá-la é conteúdo.

---

## Bloco 0 — Abertura (20 s)

> "Trabalho I de Redes de Computadores. Matheus Milanezi. O laboratório tem cinco
> roteadores FRRouting em três Sistemas Autônomos, e eu vou configurar RIP, OSPF e
> BGP sobre a mesma topologia física, um de cada vez."

---

## Bloco 1 — A topologia (40 s)

Mostre o diagrama do `readme.md` na tela e narre:

> "Os cinco roteadores formam um anel. Entre quaisquer dois pontos existem dois
> caminhos, o que permite observar reconvergência. O R2–R3 é o enlace mais curto
> em saltos entre o AS 65001 e o AS 65002, mas eu dei a ele custo OSPF 200 contra
> 10 dos demais. É daí que vem a comparação: RIP olha saltos, OSPF olha custo."

---

## Bloco 2 — OSPF (2 min)

```bash
./scripts/lab.sh up ospf
```

> "Um único daemon sobe por container — o enunciado exige que os protocolos não
> sejam simultâneos, e isso é garantido no entrypoint."

Aguarde ~60 s (comente o *wait timer* de 40 s do OSPF enquanto espera) e mostre as
adjacências:

```bash
./scripts/lab.sh vizinhos
```

> "Todas as adjacências em estado Full."

```bash
docker exec r1 vtysh -c "show ip route ospf"
```

> "R1 aprendeu as LANs dos outros quatro roteadores, os loopbacks e os enlaces de
> trânsito."

**O ponto-chave** — o caminho escolhido:

```bash
docker exec r1 vtysh -c "show ip route 10.3.0.0/24"
./scripts/lab.sh caminho h1 10.3.0.10
```

> "Para chegar na LAN do R3, o OSPF **não** usa o caminho direto por R2. Ele dá a
> volta: R1, R5, R4, R3 — quatro roteadores, custo 40. Pelo R2 seriam só três
> roteadores, mas custo 220. Guardem esse caminho, porque o RIP vai escolher outro."

**Falha de enlace.** No terminal da esquerda, deixe o ping rodando (60 pacotes, um
por segundo; ele termina sozinho e imprime a estatística de perda):

```bash
docker exec h1 ping -n -c 60 10.5.0.10
```

No terminal da direita:

```bash
./scripts/lab.sh falha r1 to-r5
```

> "Derrubei o enlace R1–R5, que era o caminho em uso para a LAN do R5. O ping não
> parou."

```bash
docker exec r1 vtysh -c "show ip route 10.5.0.0/24"
./scripts/lab.sh caminho h1 10.5.0.10
```

> "A rota migrou para métrica 240 pelo R2, e o traceroute mostra a volta completa
> pelo anel. Repare num detalhe: eu derrubei só o lado do R1. A interface do R5
> continua ativa, ele não tem como saber da falha. Mesmo assim o OSPF desviou,
> porque o R1 inundou um novo LSA sem esse enlace, e o SPF do R5 descarta uma
> ligação que só um dos lados anuncia. Na medição, a 50 pacotes por segundo, o
> OSPF não perdeu um único pacote."

```bash
./scripts/lab.sh recupera r1 to-r5
```

Espere o ping terminar e mostre a linha de estatísticas (`0% packet loss`). Não use
`Ctrl+C`: no Git Bash ele encerra só o cliente do Docker, o ping continua dentro
do container e a estatística não aparece.

---

## Bloco 3 — RIP (1 min 30 s)

```bash
./scripts/lab.sh up rip
```

Aguarde ~35 s. (O `vizinhos` do RIP imprime o status dos cinco roteadores e rola
bastante; se preferir, mostre só o R1 com `docker exec r1 vtysh -c "show ip rip"`,
que traz as métricas em saltos.)

```bash
./scripts/lab.sh vizinhos
docker exec r1 vtysh -c "show ip route rip"
```

**O contraste** — repita exatamente o comando do bloco anterior:

```bash
docker exec r1 vtysh -c "show ip route 10.3.0.0/24"
./scripts/lab.sh caminho h1 10.3.0.10
```

> "Mesma topologia, mesmo destino, caminho diferente. O RIP vai direto pelo R2:
> três roteadores em vez de quatro. Ele conta saltos e não enxerga que aquele
> enlace é o mais caro. O OSPF, que enxerga o custo, preferiu dar a volta. É a
> diferença entre vetor de distância e estado de enlace, visível na tabela."

> "Não vou repetir aqui a falha de só um lado, porque no RIP ela leva minutos: o
> R5 continua usando a rota pelo R1 até o timeout de 180 segundos vencer. Isso
> está medido nos gráficos no final."

---

## Bloco 4 — BGP (2 min)

```bash
./scripts/lab.sh up bgp
```

Pode seguir quase direto: as sessões abrem em ~3 s.

```bash
docker exec r1 vtysh -c "show ip bgp summary"
```

> "Repare que aqui não houve espera: o BGP abriu as sessões em poucos segundos,
> contra quase um minuto do OSPF."

> "Duas sessões no R1: uma iBGP com o R2, dentro do AS 65001, e uma eBGP com o R5,
> que é o AS 65003."

**O ponto-chave** — seleção por AS_PATH:

```bash
docker exec r1 vtysh -c "show ip bgp 10.3.0.0/24"
```

> "O R1 conhece dois caminhos para a LAN do R3. Um tem AS_PATH `65003 65002` — passa
> pelo AS do R5. O outro tem AS_PATH `65002`, direto. O BGP escolhe o AS_PATH mais
> curto: está marcado como `best`, e o próprio FRR escreve o motivo entre
> parênteses, `(AS Path)`. Repare que ele **não** está olhando
> saltos nem custo de enlace: a decisão é por política entre Sistemas Autônomos."

```bash
./scripts/lab.sh caminho h1 10.3.0.10
```

**Reconvergência entre ASes.** Corte o enlace R2–R3 nas duas pontas, como um cabo
rompido:

```bash
./scripts/lab.sh corta r2 r3
docker exec r1 vtysh -c "show ip bgp 10.3.0.0/24"
./scripts/lab.sh caminho h1 10.3.0.10
```

> "Com o enlace entre o AS 65001 e o AS 65002 fora, a rota direta some e o BGP passa
> a usar o AS_PATH mais longo, pelo AS 65003. A conectividade se mantém, agora por
> outro Sistema Autônomo."

> "Usei o corte nas duas pontas de propósito. Se só um lado caísse, o outro
> roteador manteria a sessão BGP aberta até o hold timer de 180 segundos vencer,
> e o tráfego de volta ficaria preso nesse tempo todo."

```bash
./scripts/lab.sh religa r2 r3
docker exec r1 vtysh -c "show ip bgp 10.3.0.0/24"
```

> "Religado, a sessão volta em poucos segundos e o caminho `65002` é de novo o
> melhor." (No ensaio voltou em ~4 s; se ainda aparecer só um caminho, espere e
> repita o comando.)

---

## Bloco 5 — Resultados (40 s)

Abra `resultados/graficos/` e passe pelos gráficos, comentando:

- **Tráfego de controle:** o OSPF é o mais caro (hellos a cada 10 s em cada
  enlace), o BGP o mais barato (um keepalive por minuto por sessão).
- **Tamanho da tabela:** o BGP tem a menor tabela porque só anuncia LANs e
  loopbacks; RIP e OSPF anunciam também os enlaces de trânsito.
- **Convergência a frio:** o BGP é o mais rápido; o OSPF espera os 40 s do
  *wait timer* antes de eleger o DR.
- **Reconvergência:** o gráfico da linha do tempo, falha unilateral × bilateral.
  É o resultado mais interessante do trabalho.
- **Latência:** diferenças abaixo de 0,1 ms, dentro do ruído. Os enlaces são
  virtuais e não têm atraso, então o RTT não separa os protocolos.

> "Todos os números vêm de `resultados/metricas.json`, coletado pelo script de
> medição, com três repetições no teste de falha."

## Encerramento (10 s)

```bash
./scripts/lab.sh down
```

> "Código, configurações, scripts de coleta e resultados estão no repositório."

---

## Checklist antes de publicar

- [ ] Os três protocolos aparecem funcionando (adjacência/sessão + tabela + tráfego)
- [ ] A divergência de caminho RIP × OSPF aparece explicitamente
- [ ] O AS_PATH do BGP aparece na tela
- [ ] Falha unilateral no OSPF e corte bilateral no BGP, ambos com recuperação
- [ ] Áudio audível e terminal legível
- [ ] Vídeo no YouTube como **não listado**, link na seção 8 do `readme.md`
      (substituindo `[adicionar o link do vídeo]`), commit e push
