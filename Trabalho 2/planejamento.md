# Trabalho 2 – Sistema de transmissão digital – Planejamento

Entrega: apresentação de 15 min em 30/11/2026; GitHub informado no Moodle até 19h do mesmo dia.
O professor ainda vai explicar o conteúdo e o trabalho em aula: as decisões abaixo são provisórias, e o
código é modular para acomodar mudanças.

## Decisões
- **Python + numpy + matplotlib**, código em `repo/` (submódulo `Redes-de-computadores_Trab-2`).
  Planejamento e materiais de trabalho ficam fora do repo de entrega.
- **Modulações:** BPSK (simples e robusta) e 16-QAM (usada em Wi-Fi/4G/5G; liga com N = 16 da Atividade 10).
- **Códigos de linha:** NRZ (referência) e Manchester (Ethernet 10 Mbit/s, liga com a Atividade 9).
  AMI ficou de fora: tem 3 níveis e não entra direto nas modulações escolhidas. Pode voltar se o professor pedir.
- **Canal:** AWGN. Ruído em rajada só se sobrar tempo.
- **Eixo dos gráficos:** Eb/N0 em dB para comparar esquemas de forma justa; a SNR (Es/N0) é mostrada junto,
  porque o enunciado fala em SNR. SNR(dB) = Eb/N0(dB) + 10·log10(bits por símbolo).
- **Simulação em banda base equivalente:** cada símbolo é um número complexo, sem gerar a portadora.
  A forma de onda no tempo entra só como figura explicativa, se o professor pedir.
- **Manchester decodificado por comparação das duas metades do bit** (decisão suave), para aproveitar a energia dos 2 chips.

## Núcleo (pronto em 07/11)
| Arquivo | Etapa |
|---|---|
| `fonte.py` | ASCII ↔ bits, bits aleatórios |
| `codigo_linha.py` | NRZ e Manchester, com detecção de pares inválidos |
| `modulacao.py` | BPSK e 16-QAM (Gray, Es = 1), demodulação com valores suaves |
| `canal.py` | AWGN, conversão Eb/N0 ↔ SNR |
| `metricas.py` | BER medida e teórica, eficiência, limite de Shannon |
| `sistema.py` | Cadeia completa e demonstração com mensagem |
| `validar.py` | 27 verificações, incluindo simulação × teoria |

## Previsões da IA e o que a execução mostrou
- Confirmado: Eb/N0 para BER = 10⁻⁵ de ~9,6 dB na BPSK (9,59) e ~13,4 dB na 16-QAM (13,43).
- Confirmado: BPSK + Manchester tem a mesma BER de BPSK + NRZ em Eb/N0, e custa o dobro de banda.
- **Corrigido:** a IA tinha chamado as 4 combinações de "limpas". Em 16-QAM + Manchester, os 2 chips de cada bit
  caem no mesmo eixo e só aparecem os pares 01 e 10 (níveis −1 e +3), então **só 4 dos 16 pontos são usados**.
  O esquema carrega 2 bits/símbolo, com BER Q(√(1,6·Eb/N0)) e 10,56 dB para 10⁻⁵. Vira análise, não defeito.
- Limitação: na 16-QAM + Manchester, a contagem de pares inválidos usa os limiares da grade completa e acusa
  bem mais pares que erros reais (57 pares para 9 bits errados a 2 dB). Não usar esse número como medida de erro.

## Próximos passos (cronograma adiantado)
- [x] Planejamento e núcleo validado
- [ ] Até 08/11: curvas BER × Eb/N0 (simulada + teórica), constelações com ruído, eficiência × limite de Shannon, logs
- [ ] Até 15/11: README ("como outra pessoa usa"), relatório técnico, slides (modelo Unisinos em `Trabalho 1/`)
- [ ] Até 22/11: vídeo de até 5 min e ensaio de 15 min
- [ ] 23 a 30/11: folga para encaixar o que o professor explicar em aula

## Checklist da avaliação (10 itens, 1 ponto cada)
- [ ] Apresentação oral
- [x] Geração de dados (`fonte.py`)
- [x] Codificação de canal (`codigo_linha.py`)
- [x] Modulação e demodulação (`modulacao.py`)
- [x] Canal AWGN e controle da SNR (`canal.py`)
- [x] Decodificação e cálculo da BER (`codigo_linha.py`, `metricas.py`)
- [ ] Comparação entre modulações e análise
- [ ] Impacto da BER e eficiência do sistema
- [ ] Clareza do código e relatório técnico
- [ ] Demonstração prática e vídeo
