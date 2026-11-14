# Atividade 11 – Codificação de Banda Base e Modulação Digital – Planejamento

Entrega: PDF único no Moodle até 16/11/2026. O PDF do professor se chama "Atividade 13", mas é esta atividade.
Faz parte do Trabalho 2: as figuras de forma de onda entram no relatório e nos slides do trabalho.

## Decisões
- Linguagem: **Python** (arquivo único `codificacao_modulacao.py`), com numpy e matplotlib, como no Trabalho 2.
  Aqui os sinais são **formas de onda reais no tempo** (amostradas), e não a banda base complexa do Trabalho 2.
- Sequência padrão de 16 bits: **`1011000001101001`**, a mesma dos slides 13 e 14 da aula 13 (14 bits),
  completada com `01`. Assim dá para comparar as figuras com as do slide, e o trecho de cinco zeros mostra o
  problema de sincronismo do NRZ. O programa aceita outra sequência (`--bits`) ou um texto ASCII (`--texto`).
- Relatório: `relatorio.md` → **`Atividade 11 - Matheus Milanezi.docx`** gerado por script, com **todo o texto
  em preto** (inclusive os títulos, que o Word deixa azul por padrão). O PDF fica com o Matheus.

## Convenções (o enunciado pede que fiquem explícitas)
| Técnica | Bit 0 | Bit 1 | Fonte |
|---|---|---|---|
| NRZ unipolar | 0 V | +V | aula 13, slide 13 |
| NRZ polar | −V | +V | aula 13, slides 12 e 13 |
| Manchester | descida no meio do bit (+V → −V) | subida no meio do bit (−V → +V) | slide 14, IEEE 802.3 |
| ASK | amplitude 0 | amplitude A | slide 20 |
| FSK | frequência f0 = fc | frequência f1 = 2fc | slide 20 |
| BPSK | fase 180° (−A) | fase 0° (+A) | slides 23 e 26 |

- V = 1 V. Existe a convenção oposta de Manchester (G. E. Thomas): o relatório cita, mas usa a do slide.
- **Os slides discordam no BPSK:** a tabela do slide 20 diz 0 → 0° e 1 → 180°; a figura do slide 23 e a
  constelação do slide 26 dizem 0 → 180° (−A) e 1 → 0° (+A). Uso a segunda, que é a mesma do Trabalho 2.
  As duas funcionam, desde que transmissor e receptor combinem.

## Parâmetros da modulação
| Parâmetro | Valor | Observação |
|---|---|---|
| Taxa de bits Rb | 1 kbit/s | Tb = 1 ms |
| Portadora fc | 2 kHz | 2 ciclos por bit |
| FSK | f0 = 2 kHz, f1 = 4 kHz | 2 e 4 ciclos por bit: as duas são ortogonais e a fase não "pula" na troca |
| Amplitude A | 1 V | |
| Amostragem fs | 100 kHz | 100 amostras por bit, 25 por ciclo na frequência mais alta (4 kHz) |

Portadora: e(t) = A·sen(2π·f·t + θ), como no slide 18 (Vp, ω, θ).

**Receptor (para os testes com ruído):** correlação com a forma de onda esperada em cada intervalo de bit.
- ASK: correlação com a portadora e limiar na metade da energia do bit 1.
- FSK: correlação com f0 e com f1; ganha a maior.
- BPSK: correlação com a portadora; o sinal do resultado decide o bit.
- Códigos de linha: média do nível em cada bit (NRZ) e comparação das duas metades (Manchester).

## Interface do programa
```
python codificacao_modulacao.py                          roda tudo (figuras, tabelas, ruído, BER)
python codificacao_modulacao.py codificar --bits 1011…   figura dos 3 códigos de linha para uma sequência
python codificacao_modulacao.py codificar --texto "Re"   idem, a partir de texto ASCII
python codificacao_modulacao.py modular --bits 1011…     figura de ASK, FSK e BPSK
python codificacao_modulacao.py ruido --ebn0 6           sinais com ruído e bits errados
python codificacao_modulacao.py validar                  verificações automáticas
```
Figuras em `graficos/`; saída de texto em `saida_experimentos.txt`.

## Experimentos
1. **Códigos de linha:** relógio (cadência), sequência, NRZ unipolar, NRZ polar e Manchester empilhados,
   com linhas tracejadas nos limites de bit e setas nas transições do meio do bit (como no slide 14).
   Tabela: transições, maior trecho sem transição e nível médio (componente DC).
2. **Modulações:** sequência (NRZ), portadora de referência, ASK, FSK e BPSK empilhados, com os bits
   escritos em cada intervalo. Tabela dos parâmetros.
3. **Ruído visível:** os 16 bits com ruído em Eb/N0 = 12, 6 e 0 dB, com a decisão do receptor e os bits
   errados marcados em vermelho.
4. **BER × Eb/N0:** simulação com muitos bits (formas de onda completas) para ASK, FSK e BPSK e para os
   3 códigos de linha, com as curvas teóricas por cima.
5. *(Se couber)* **Espectro:** densidade espectral dos sinais, para mostrar a "banda = 2× banda original"
   do ASK (slide 21), as duas frequências do FSK (slide 22) e a banda maior do Manchester.

## Validação
- Decodificar o código de linha sem ruído devolve a sequência original (3 códigos).
- Manchester tem exatamente uma transição no meio de cada bit, no sentido da convenção.
- A sequência do slide 13/14 (14 bits) gera os mesmos níveis do slide, conferidos bit a bit.
- Demodular ASK, FSK e BPSK sem ruído devolve a sequência original.
- f0 e f1 são ortogonais: a correlação entre elas em um bit é ≈ 0.
- Energia por bit medida nas amostras = A²·Tb/2 (bit 1 do ASK, qualquer bit do FSK e do BPSK).
- BER simulada dentro de 4 desvios padrão da teórica em alguns pontos.

## Previsões (feitas pela IA antes de rodar, a confirmar com o programa)
**Sequência `1011000001101001`:** 7 uns e 9 zeros.
| Código | Transições em 16 bits | Maior trecho sem transição | Nível médio |
|---|---|---|---|
| NRZ unipolar | 8 | 5 bits (os cinco zeros) | +0,44 V |
| NRZ polar | 8 | 5 bits | −0,125 V |
| Manchester | 23 (16 no meio do bit + 7 entre bits iguais) | 1 bit | 0 V em todo bit |

**BER teórica (receptor por correlação, canal AWGN):**
- BPSK e NRZ polar: Q(√(2·Eb/N0)). Manchester também, porque cada bit usa as duas polaridades.
- ASK, FSK e NRZ unipolar: Q(√(Eb/N0)), com Eb = energia **média** por bit.

| Eb/N0 | 0 dB | 6 dB | 10 dB | 12 dB |
|---|---|---|---|---|
| BPSK / polar / Manchester | 7,9·10⁻² | 2,4·10⁻³ | 3,9·10⁻⁶ | 9,0·10⁻⁹ |
| ASK / FSK / unipolar | 1,6·10⁻¹ | 2,3·10⁻² | 7,8·10⁻⁴ | 3,4·10⁻⁵ |

- Para BER = 10⁻⁵: **9,59 dB** no BPSK e **12,60 dB** no ASK e no FSK. O BPSK ganha por 3 dB.
- Em 16 bits a 0 dB, o esperado é ≈ 1,3 bit errado no BPSK e ≈ 2,5 no ASK e no FSK.
- **Ponto a conferir contra o slide 22** ("FSK é mais tolerante a ruído do que a ASK"): pela energia média,
  ASK e FSK empatam. A vantagem do FSK aparece quando se compara pela **amplitude de pico** (o ASK só
  transmite em metade dos bits, então com o mesmo pico ele tem metade da energia média: 3 dB pior) e na
  prática, porque o limiar do ASK depende de saber a amplitude recebida, e o do FSK não.
- **Ligação banda base × modulação:** o ASK é o NRZ unipolar multiplicado pela portadora, e o BPSK é o NRZ
  polar multiplicado pela portadora. Por isso as curvas de BER coincidem duas a duas.

## Teste da IA (14/11, em pasta temporária; a execução oficial é a do Matheus)
- `validar`: 11/11 OK, incluindo os níveis do slide 13 e as setas do slide 14 conferidos bit a bit.
- Tabela de transições e DC: igual à prevista (8 / 8 / 23 transições; 0,438 / −0,125 / 0 V).
- BER simulada sobre a teoria nas 6 técnicas, de 0 a 12 dB; as curvas coincidem duas a duas, como previsto
  (unipolar = ASK = FSK; polar = Manchester = BPSK), com 3,01 dB de diferença em BER = 10⁻⁵.
- 16 bits a 0 dB: BPSK 0 erros, ASK 2, FSK 3; unipolar 3, polar 2, Manchester 2 (semente 2026).
- Espectro: potência no lobo principal de 90 % (polar), 92 % (BPSK), 95–96 % (unipolar e ASK, por causa da
  raia em 0 Hz / fc) e 86 % no Manchester, que precisa de 2 kHz contra 1 kHz do NRZ.
- Execução completa: cerca de 1 minuto.

## Roteiro de execução (Matheus, PowerShell, dentro de `Atividade 11/`)
1. `python codificacao_modulacao.py validar` → todas as verificações OK.
2. `python codificacao_modulacao.py` → tabelas no terminal, figuras em `graficos/`, `saida_experimentos.txt`.
3. Exemplos para os prints: `codificar --texto "Re"`, `ruido --ebn0 0`.
4. Entrada inválida: `codificar --bits 10102` → mensagem de erro.

## Checklist do relatório (DOCX → PDF único)
- [ ] Código-fonte completo e parâmetros (apêndice + tabela de parâmetros)
- [ ] Parte 1: figura dos 3 códigos, convenções, tabela de transições e DC
- [ ] Parte 2: figura das 3 modulações, parâmetros, qual parâmetro da portadora carrega o bit
- [ ] Evidências com ruído: figura dos 16 bits com ruído + curvas de BER
- [ ] Parte 3: as 3 respostas breves, apoiadas nas figuras
- [ ] Uso de IA (ferramenta, etapas, validação, exemplo confirmado/corrigido/adaptado)
