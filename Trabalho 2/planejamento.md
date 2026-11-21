# Trabalho 2 – Sistema de transmissão digital – Planejamento

Entrega: apresentação de 15 min em 30/11/2026; GitHub informado no Moodle até 19h do mesmo dia.
A aula 13 (códigos de linha e modulação) confirmou as convenções do código: Manchester com subida no meio do
bit para 1 e descida para 0 (slide 14), BPSK com 0 em −A e 1 em +A (slide 26). A Atividade 11 faz parte do trabalho.

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

## Reta final (replanejado em 21/11; Atividades 11 e 12 entregues)
Formato da entrega (o enunciado diz que "toda a documentação deve estar disponível no GitHub"):
- `README.md` no repo: como outra pessoa instala, roda e lê os resultados (exigido pelo enunciado).
- `docs/relatorio.md` no repo: relatório técnico (rubrica, item 9), renderizado pelo próprio GitHub.
- Slides `.pptx` no modelo Unisinos, gerados por script como no Trabalho 1 (fora do repo).
- Vídeo ≤ 5 min no YouTube (não listado), com o link no README.

| Quando | O quê | Quem |
|---|---|---|
| 21/11 | Acabamento: formato brasileiro no log, nos gráficos e no terminal (`formato.py`); rótulo de Shannon | IA (feito) → Matheus roda de novo |
| 21–22/11 | README + relatório técnico | IA escreve, Matheus revisa |
| 23–24/11 | Slides (~13, para 15 min) + roteiro de fala | IA gera, Matheus revisa |
| 25–26/11 | Roteiro do vídeo; gravação e upload | IA roteiro, Matheus grava |
| 27–28/11 | Ensaio cronometrado de 15 min; ajustes | Matheus |
| 29–30/11 | Folga; push final; link no Moodle até 19h do dia 30 | Matheus |

21/11, tarde: README reescrito e `docs/relatorio.md` criado (análise: BPSK × 16-QAM = 3,84 dB por 4× eficiência;
Manchester não muda a BER em Eb/N0 e dobra a banda; 16-QAM + Manchester perde 0,97 dB para uma QPSK porque 20 % da
energia vai no deslocamento da constelação; BER → caractere/pacote; distância a Shannon 7,7–10,4 dB).
Achado: a contagem de pares Manchester inválidos superestima erros também no BPSK (41 pares para 5 bits a 2 dB),
porque é chip a chip e a decisão é suave. A saída do `sistema.py` agora avisa isso. `--help` com textos de ajuda;
"1 bit errado" no singular no log (exige rodar `experimentos.py` de novo).

Acabamento de 21/11: só formatação. Teste da IA: `validar` 27/27 e `ber.csv` idêntico ao da execução oficial
de 14/11 (semente fixa); execução completa em ~25 s. O `ber.csv` continua com ponto decimal (para programas).

## Próximos passos (cronograma antigo, até 14/11)
- [x] Planejamento e núcleo validado
- [x] Até 08/11 (feito em 13/11): `experimentos.py` – BER × Eb/N0 e × SNR (simulada + teórica), constelações
  com ruído, eficiência × limite de Shannon, mensagem de teste, `log_experimentos.txt` e `ber.csv` em `resultados/`.
  Execução oficial pelo Matheus em 14/11.
- [ ] Até 16/11: Atividade 11 (códigos de linha e ASK/FSK/BPSK com portadora); as figuras entram no relatório e nos slides
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
