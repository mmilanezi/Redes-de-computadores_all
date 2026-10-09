# Atividade 06 – RIP, OSPF e BGP (planejamento / roteiro de execução)

> Enunciado: `Atividade_05_RIP_OSPF_BGP.pdf` (o professor manteve o nome "Atividade 05" no PDF, mas no Moodle é a **Atividade prática 06**, prazo **21/09/2026 19:30**).
> Ferramenta: Cisco Packet Tracer 9.0.1.
> Tudo marcado como **previsão** é o que a teoria indica pra esta topologia. **Não vai pro relatório sem confirmar no PT**: o enunciado exige que as respostas saiam do experimento.

---

## 0. Decisões

- **Topologia RIP/OSPF = a mesma da Atividade 05.** Reaproveitada a partir de uma cópia: `atividade_06_rip_ospf.pkt` (o `atividade_05.pkt` original fica intacto). Mesmos modelos (2911 em A/B/E, 1941 em C/D), mesmo endereçamento e mesmos Server1/Laptop1 no lugar de PC3/PC2 (já justificado na Atividade 05).
- **Par de teste: PC0 → Server1 (192.168.3.10)**, o mesmo da Atividade 05. Assim dá pra comparar estático × RIP × OSPF no mesmo caminho.
- **Salvar um arquivo por etapa** (`Save As`), pra poder voltar e tirar prints de novo:
  `atividade_06_rip.pkt` → `atividade_06_ospf.pkt` → `atividade_06_ospf_custo.pkt` → `atividade_06_bgp.pkt`
- **BGP em arquivo novo**, com roteadores 2811 como na figura. O R2 precisa de 3 interfaces e o 2811 só tem 2, então vai um módulo `NM-1FE-TX` (vira `FastEthernet1/0`).
- Em todo roteador, rodar `no ip domain-lookup` (evita travar ~30 s quando errar a digitação de um comando).

---

## 1. Preparação da topologia RIP/OSPF

### Endereçamento (herdado da Atividade 05)

> **Correção no B:** os cabos do B estavam em portas diferentes das documentadas na Atividade 05 (erro que já existia lá e não apareceu porque o teste PC0 → Server1 não passa pelo B). Os IPs foram trocados de interface pra acompanhar o cabeamento real (`scripts/0b-corrigir-interfaces-B.txt`). A tabela abaixo já mostra o estado corrigido.

| Roteador | Interface | IP | Liga em |
|---|---|---|---|
| A | Gi0/0 | 192.168.1.1/24 | PC0 |
| A | Gi0/1 | 192.168.7.1/24 | Switch0 (A-B-C) |
| A | Gi0/2 | 192.168.9.1/24 | Switch1 (A-D-E) |
| B | Gi0/0 | 192.168.7.2/24 | Switch0 |
| B | Gi0/1 | 192.100.0.1/24 | E |
| B | Gi0/2 | 192.168.2.1/24 | PC1 |
| C | Gi0/0 | 192.168.7.3/24 | Switch0 |
| C | Gi0/1 | 192.168.8.1/24 | D |
| D | Gi0/0 | 192.168.8.2/24 | C |
| D | Gi0/1 | 192.168.9.2/24 | Switch1 |
| E | Gi0/0 | 192.100.0.2/24 | B |
| E | Gi0/1 | 192.168.9.3/24 | Switch1 |
| E | Gi0/2 | 192.168.3.1/24 | Server1 |

Hosts: PC0 `192.168.1.10`, PC1 `192.168.2.10`, Server1 `192.168.3.10`, Laptop1 `192.168.9.10` (gateway = `.1` da rede de cada um).

### ⚠️ Pegadinha nº 1: remover as rotas estáticas da Atividade 05

Rota estática tem distância administrativa **1**, RIP tem **120** e OSPF tem **110**. Se as estáticas ficarem, elas ganham e as rotas `R`/`O` **nunca aparecem** na tabela, mesmo com o protocolo funcionando.

Primeiro, em cada roteador, confira o que existe:

```
enable
show running-config | include ip route
```

As linhas abaixo foram deduzidas da tabela de encaminhamento do relatório da Atividade 05. **Se o `show` mostrar algo diferente, vale o `show`**: é só colocar `no` na frente de cada linha que aparecer.

**A**
```
configure terminal
no ip domain-lookup
no ip route 192.168.2.0 255.255.255.0 192.168.7.2
no ip route 192.168.3.0 255.255.255.0 192.168.9.3
no ip route 192.100.0.0 255.255.255.0 192.168.7.2
no ip route 192.168.8.0 255.255.255.0 192.168.7.3
end
```

**B**
```
configure terminal
no ip domain-lookup
no ip route 192.168.1.0 255.255.255.0 192.168.7.1
no ip route 192.168.3.0 255.255.255.0 192.100.0.2
no ip route 192.168.8.0 255.255.255.0 192.168.7.3
no ip route 192.168.9.0 255.255.255.0 192.100.0.2
end
```

**C**
```
configure terminal
no ip domain-lookup
no ip route 192.168.1.0 255.255.255.0 192.168.7.1
no ip route 192.168.2.0 255.255.255.0 192.168.7.2
no ip route 192.168.3.0 255.255.255.0 192.168.8.2
no ip route 192.100.0.0 255.255.255.0 192.168.7.2
no ip route 192.168.9.0 255.255.255.0 192.168.8.2
end
```

**D**
```
configure terminal
no ip domain-lookup
no ip route 192.168.1.0 255.255.255.0 192.168.9.1
no ip route 192.168.2.0 255.255.255.0 192.168.9.3
no ip route 192.168.3.0 255.255.255.0 192.168.9.3
no ip route 192.100.0.0 255.255.255.0 192.168.9.3
no ip route 192.168.7.0 255.255.255.0 192.168.8.1
end
```

**E**
```
configure terminal
no ip domain-lookup
no ip route 192.168.1.0 255.255.255.0 192.168.9.1
no ip route 192.168.2.0 255.255.255.0 192.100.0.1
no ip route 192.168.7.0 255.255.255.0 192.100.0.1
no ip route 192.168.8.0 255.255.255.0 192.168.9.2
end
```

**Checagem:** `show ip route` em cada roteador deve mostrar **só linhas `C` e `L`**, sem nenhum `S`. Um ping de PC0 → Server1 agora deve **falhar**. Isso é bom: prova que, daqui pra frente, quem faz a rede funcionar é o protocolo dinâmico.

---

## 2. RIP (RIPv2)

### Configuração

`version 2` + `no auto-summary` em todos. O `network` do RIP é classful, então basta a rede "cheia".

**A**
```
configure terminal
router rip
 version 2
 no auto-summary
 network 192.168.1.0
 network 192.168.7.0
 network 192.168.9.0
end
```

**B**
```
configure terminal
router rip
 version 2
 no auto-summary
 network 192.168.2.0
 network 192.168.7.0
 network 192.100.0.0
end
```

**C**
```
configure terminal
router rip
 version 2
 no auto-summary
 network 192.168.7.0
 network 192.168.8.0
end
```

**D**
```
configure terminal
router rip
 version 2
 no auto-summary
 network 192.168.8.0
 network 192.168.9.0
end
```

**E**
```
configure terminal
router rip
 version 2
 no auto-summary
 network 192.100.0.0
 network 192.168.9.0
 network 192.168.3.0
end
```

Esperar ~30–60 s (o RIP anuncia a cada 30 s).

### Verificação (rodar e guardar a saída)

- Em **A**: `show ip route rip`, `show ip route`, `show ip protocols`
- Em **C**: `show ip route rip` (tem uma coisa legal pra observar lá, ver previsão)
- No **PC0** (Desktop → Command Prompt): `ping 192.168.3.10` e `tracert 192.168.3.10`

### Previsão

Tabela RIP de **A** (métrica = nº de saltos até o roteador que tem a rede):
```
R  192.168.2.0/24  [120/1] via 192.168.7.2  (B)
R  192.168.3.0/24  [120/1] via 192.168.9.3  (E)
R  192.168.8.0/24  [120/1] via 192.168.7.3  (C)
                   [120/1] via 192.168.9.2  (D)      <- dois caminhos de 1 salto (ECMP)
R  192.100.0.0/24  [120/1] via 192.168.7.2  (B)
                   [120/1] via 192.168.9.3  (E)      <- ECMP
```

Tabela RIP de **C**: a rede do Server1 fica a **2 saltos por três caminhos diferentes**:
```
R  192.168.3.0/24  [120/2] via 192.168.7.1  (A → E)
                   [120/2] via 192.168.7.2  (B → E)
                   [120/2] via 192.168.8.2  (D → E)
```
É um bom exemplo de que o RIP só conta saltos e não diferencia os caminhos entre si.

Tracert PC0 → Server1:
```
1  192.168.1.1    (A)
2  192.168.9.3    (E)
3  192.168.3.10   (Server1)
```
Ping com **TTL=126** (128 − 2 roteadores). É o mesmo caminho das rotas estáticas da Atividade 05.

💾 `Save As` → `atividade_06_rip.pkt`

---

## 3. OSPF

### Remover o RIP + configurar OSPF (área 0)

Router-ID fixo e fácil de reconhecer: A=1.1.1.1, B=2.2.2.2, C=3.3.3.3, D=4.4.4.4, E=5.5.5.5.

**A**
```
configure terminal
no router rip
router ospf 1
 router-id 1.1.1.1
 network 192.168.1.0 0.0.0.255 area 0
 network 192.168.7.0 0.0.0.255 area 0
 network 192.168.9.0 0.0.0.255 area 0
end
```

**B**
```
configure terminal
no router rip
router ospf 1
 router-id 2.2.2.2
 network 192.168.2.0 0.0.0.255 area 0
 network 192.168.7.0 0.0.0.255 area 0
 network 192.100.0.0 0.0.0.255 area 0
end
```

**C**
```
configure terminal
no router rip
router ospf 1
 router-id 3.3.3.3
 network 192.168.7.0 0.0.0.255 area 0
 network 192.168.8.0 0.0.0.255 area 0
end
```

**D**
```
configure terminal
no router rip
router ospf 1
 router-id 4.4.4.4
 network 192.168.8.0 0.0.0.255 area 0
 network 192.168.9.0 0.0.0.255 area 0
end
```

**E**
```
configure terminal
no router rip
router ospf 1
 router-id 5.5.5.5
 network 192.100.0.0 0.0.0.255 area 0
 network 192.168.9.0 0.0.0.255 area 0
 network 192.168.3.0 0.0.0.255 area 0
end
```

> Se o router-id não "pegar" (o processo já tinha subido com outro ID): `clear ip ospf process` → `yes`.

### Verificação

- Em **A**: `show ip ospf neighbor`, `show ip route ospf`, `show ip protocols`, `show ip ospf interface GigabitEthernet0/2` (anotar a linha **Cost**)
- Confirmar em `show ip route` que **não sobrou nenhum `R`**
- No **PC0**: `ping 192.168.3.10` e `tracert 192.168.3.10`

### Previsão

Vizinhos de **A**: 4 adjacências, todas `FULL`:
```
Neighbor ID   State        Address        Interface
2.2.2.2       FULL/BDR     192.168.7.2    Gi0/1
3.3.3.3       FULL/DR      192.168.7.3    Gi0/1
4.4.4.4       FULL/BDR     192.168.9.2    Gi0/2
5.5.5.5       FULL/DR      192.168.9.3    Gi0/2
```
Os papéis DR/BDR **podem variar**: vence o maior router-id, mas a eleição não é preemptiva, então quem sobe primeiro pode ficar com o papel. A anota o que aparecer, sem problema.

Tabela OSPF de **A**:
```
O  192.168.2.0/24  [110/2] via 192.168.7.2
O  192.168.3.0/24  [110/2] via 192.168.9.3
O  192.168.8.0/24  [110/2] via 192.168.7.3
                   [110/2] via 192.168.9.2
O  192.100.0.0/24  [110/2] via 192.168.7.2
                   [110/2] via 192.168.9.3
```
- `show ip ospf interface Gi0/2` → **Cost: 1** (referência padrão 100 Mbps; o Gigabit arredonda pra 1).
- **Mesmo caminho do RIP** (A → E), mas o número muda: RIP = **1** e OSPF = **2**. O RIP conta roteadores no meio do caminho, já o OSPF soma o custo de cada interface de saída, **incluindo a interface do E que entra na rede do Server1**.
- Como todo link é Gigabit (custo 1), aqui o OSPF acaba se comportando como contagem de saltos. É por isso que o caminho coincide com o do RIP. Isso responde direto a 1ª pergunta da seção 6.

Tracert: igual ao do RIP (`192.168.1.1` → `192.168.9.3` → `192.168.3.10`).

💾 `Save As` → `atividade_06_ospf.pkt`

---

## 4. Alterar o custo OSPF

Interface escolhida: **A Gi0/2**, a saída de A para o E, que está exatamente no caminho observado.

**Antes** (já coletado na etapa 3): `show ip ospf interface GigabitEthernet0/2` (Cost 1), `show ip route ospf` e o tracert.

**Mudança:**
```
configure terminal
interface GigabitEthernet0/2
 ip ospf cost 100
end
```

**Depois:** repetir `show ip ospf interface GigabitEthernet0/2`, `show ip route ospf` e, no PC0, `tracert 192.168.3.10` + `ping 192.168.3.10`.

### Previsão

Custos de A até 192.168.3.0/24 depois da mudança:
| Caminho | Soma | |
|---|---|---|
| A →(Gi0/2) E → rede | 100 + 1 = **101** | perdeu |
| A →(Gi0/1) B → E → rede | 1 + 1 + 1 = **3** | **vence** |
| A →(Gi0/1) C → D → E → rede | 1 + 1 + 1 + 1 = 4 | |

Tabela de **A**:
```
O  192.168.2.0/24  [110/2] via 192.168.7.2          (igual)
O  192.168.3.0/24  [110/3] via 192.168.7.2          <- mudou: era 2 via E, agora 3 via B
O  192.168.8.0/24  [110/2] via 192.168.7.3          <- perdeu o ECMP via D
O  192.100.0.0/24  [110/2] via 192.168.7.2          <- perdeu o ECMP via E
```

Tracert PC0 → Server1:
```
1  192.168.1.1    (A)
2  192.168.7.2    (B)
3  192.100.0.2    (E)   <- ou 192.168.9.3, ver abaixo
4  192.168.3.10   (Server1)
```

### 🔍 Detalhes pra observar (bom material pra análise)

1. **O custo OSPF só vale na saída.** Mudamos o custo de *A saindo* por Gi0/2. A volta (E → PC0) continua `E → A` direto pela rede 192.168.9.0 (custo 2), então a **rota fica assimétrica**: ida por A-B-E, volta por E-A.
   - Evidência: o **ping deve continuar com TTL=126** (2 roteadores na volta), mesmo o tracert mostrando 3 roteadores na ida.
   - Pra confirmar: `show ip route 192.168.1.0` no **E**, que deve continuar via `192.168.9.1`.
2. **Salto 3 do tracert:** por causa da assimetria, o E recebe a sonda por Gi0/0 (`192.100.0.2`), mas responde pela Gi0/1 (`192.168.9.3`). Dependendo de qual interface o PT usa como origem do ICMP Time Exceeded, o salto 3 pode aparecer como um ou outro. **Hipótese a verificar**, anotar o que aparecer.
3. A rede 192.168.9.0 continua `C` (conectada) em A. Custo OSPF não afeta rede diretamente conectada, então o Laptop1 continua sendo alcançado direto pela Gi0/2.

💾 `Save As` → `atividade_06_ospf_custo.pkt`

---

## 5. BGP (arquivo novo)

### Montagem

- 3× **2811** (R1, R2, R3) e 3× PC. Se o 2811 perguntar "initial configuration dialog?", responder `no`.
- **R2:** desligar (botão na aba Physical), arrastar **NM-1FE-TX** pro slot vazio e ligar de novo. Aparece a `FastEthernet1/0`.
- Cabos: roteador↔roteador e roteador↔PC = **cross-over** (tracejado na figura).

| Dispositivo | Interface | IP | Liga em |
|---|---|---|---|
| R1 (AS100) | Fa0/0 | 12.12.12.1/24 | R2 |
| R1 | Fa0/1 | 10.0.0.1/24 | PC1 |
| R1 | Loopback0 | 1.1.1.1/32 | |
| R2 (AS200) | Fa0/0 | 12.12.12.2/24 | R1 |
| R2 | Fa0/1 | 172.16.0.1/24 | PC2 |
| R2 | Fa1/0 | 23.23.23.2/24 | R3 |
| R2 | Loopback0 | 2.2.2.2/32 | |
| R3 (AS300) | Fa0/0 | 23.23.23.3/24 | R2 |
| R3 | Fa0/1 | 192.168.0.1/24 | PC3 |
| R3 | Loopback0 | 3.3.3.3/32 | |
| PC1 | | 10.0.0.2/24, gw 10.0.0.1 | |
| PC2 | | 172.16.0.2/24, gw 172.16.0.1 | |
| PC3 | | 192.168.0.2/24, gw 192.168.0.1 | |

### Configuração

**R1**
```
enable
configure terminal
hostname R1
no ip domain-lookup
interface FastEthernet0/0
 ip address 12.12.12.1 255.255.255.0
 no shutdown
interface FastEthernet0/1
 ip address 10.0.0.1 255.255.255.0
 no shutdown
interface Loopback0
 ip address 1.1.1.1 255.255.255.255
exit
router bgp 100
 neighbor 12.12.12.2 remote-as 200
 network 10.0.0.0 mask 255.255.255.0
 network 1.1.1.1 mask 255.255.255.255
end
write memory
```

**R2**
```
enable
configure terminal
hostname R2
no ip domain-lookup
interface FastEthernet0/0
 ip address 12.12.12.2 255.255.255.0
 no shutdown
interface FastEthernet0/1
 ip address 172.16.0.1 255.255.255.0
 no shutdown
interface FastEthernet1/0
 ip address 23.23.23.2 255.255.255.0
 no shutdown
interface Loopback0
 ip address 2.2.2.2 255.255.255.255
exit
router bgp 200
 neighbor 12.12.12.1 remote-as 100
 neighbor 23.23.23.3 remote-as 300
 network 172.16.0.0 mask 255.255.255.0
 network 2.2.2.2 mask 255.255.255.255
end
write memory
```

**R3**
```
enable
configure terminal
hostname R3
no ip domain-lookup
interface FastEthernet0/0
 ip address 23.23.23.3 255.255.255.0
 no shutdown
interface FastEthernet0/1
 ip address 192.168.0.1 255.255.255.0
 no shutdown
interface Loopback0
 ip address 3.3.3.3 255.255.255.255
exit
router bgp 300
 neighbor 23.23.23.2 remote-as 200
 network 192.168.0.0 mask 255.255.255.0
 network 3.3.3.3 mask 255.255.255.255
end
write memory
```

> No BGP, o `network ... mask` só anuncia a rota se ela **existir exatamente igual na tabela de roteamento** (por isso as interfaces vêm antes). O BGP do PT é lento: pode levar 1–2 min pra tudo aparecer. Se travar, `clear ip bgp *`.

### Verificação

- `show ip bgp summary` nos **3** roteadores (sessões estabelecidas)
- `show ip bgp` em **R1** e **R3** (tabela BGP + AS_PATH)
- `show ip route bgp` em R1
- `show ip bgp neighbors` em R2 (opcional, é longo; dá pra printar só o topo com "BGP state = Established")
- **PC1:** `ping 192.168.0.2` e `tracert 192.168.0.2`

### Previsão

`show ip bgp summary` em **R2**: dois vizinhos, e a coluna `State/PfxRcd` mostra um **número** (não `Idle`/`Active`):
```
Neighbor      V   AS   ...  State/PfxRcd
12.12.12.1    4   100  ...  2
23.23.23.3    4   300  ...  2
```

`show ip bgp` em **R1**:
```
   Network          Next Hop       Metric LocPrf Weight Path
*> 1.1.1.1/32       0.0.0.0             0         32768 i
*> 2.2.2.2/32       12.12.12.2          0             0 200 i
*> 3.3.3.3/32       12.12.12.2                        0 200 300 i
*> 10.0.0.0/24      0.0.0.0             0         32768 i
*> 172.16.0.0/24    12.12.12.2          0             0 200 i
*> 192.168.0.0/24   12.12.12.2                        0 200 300 i
```
- **Leitura do AS_PATH** `200 300 i`: da esquerda pra direita, o AS vizinho (200) até o AS de origem (300). O `i` é a origem IGP (anunciada por `network`). É isso que responde a 3ª pergunta.
- Next hop sempre `12.12.12.2`: o eBGP troca o next hop pelo IP do vizinho.
- Em `show ip route`: `B 192.168.0.0/24 [20/0] via 12.12.12.2` (distância administrativa do eBGP = **20**).
- Em R3, espelhado: `10.0.0.0/24 ... 200 100 i`.

Tracert PC1 → PC3:
```
1  10.0.0.1       (R1, AS100)
2  12.12.12.2     (R2, AS200)
3  23.23.23.3     (R3, AS300)
4  192.168.0.2    (PC3)
```
Ping com TTL=125 (3 roteadores).

> ⚠️ **Pegadinha nº 2:** as redes de trânsito (12.12.12.0 e 23.23.23.0) **não** são anunciadas. Por isso, `ping 23.23.23.3` a partir do PC1 **falha** (R1 não tem rota pra ela), e um ping direto do *roteador* R1 pro PC3 também falha (origem 12.12.12.1, que o R3 não conhece). Não é erro: é só testar sempre **de PC pra PC**. O tracert funciona porque o R3 responde pra 10.0.0.2, que ele conhece.

💾 `Save As` → `atividade_06_bgp.pkt`

---

## 6. Checklist de evidências (prints pro PDF)

**RIP**
- [ ] `show ip route` (ou `show ip route rip`) em A, com as rotas `R` e as métricas
- [ ] `show ip route rip` em C (ECMP triplo), extra
- [ ] `tracert 192.168.3.10` no PC0
- [ ] `ping` no PC0 (opcional, pra mostrar o TTL)

**OSPF**
- [ ] `show ip ospf neighbor` em A
- [ ] `show ip route ospf` em A, **antes** do custo
- [ ] `show ip ospf interface Gi0/2`, **antes** (Cost 1)
- [ ] `tracert` no PC0, **antes**
- [ ] `show ip ospf interface Gi0/2`, **depois** (Cost 100)
- [ ] `show ip route ospf` em A, **depois**
- [ ] `tracert` no PC0, **depois**
- [ ] `ping` depois (TTL) + `show ip route 192.168.1.0` em E (assimetria), extra

**BGP**
- [ ] `show ip bgp summary` (R2 mostra as duas sessões)
- [ ] `show ip bgp` em R1 (AS_PATH)
- [ ] `show ip route` em R1 (código `B`)
- [ ] `tracert 192.168.0.2` no PC1

---

## 7. Próximo passo

Executar no PT e me mandar as **saídas em texto** dos comandos acima: dá pra selecionar e copiar no CLI do PT e colar no chat, ou salvar em `Atividade 6/logs/*.txt`. Com isso eu escrevo o `relatorio.md` (tabela comparativa, as 4 respostas e a seção de IA) com base nos resultados reais, principalmente onde a previsão errar. Os prints vão direto pro Word.
