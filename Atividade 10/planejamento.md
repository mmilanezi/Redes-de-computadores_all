# Atividade 10 – Capacidade de Canais (Nyquist e Shannon) – Planejamento

## Decisões
- Linguagem: **Python 3.14** (arquivo único `capacidade.py`).
  Núcleo com `math` (fórmulas legíveis, sem dependência); gráficos com **matplotlib 3.11** (já instalado).
- Fórmulas (enunciado + aula 12):
  - Nyquist: `C = 2B·log2(N)` – canal ideal, sem ruído.
  - Shannon: `C = B·log2(1 + SNR)` – SNR em escala **linear**.
  - Conversão: `SNR = 10^(SNR_dB/10)` e `SNR_dB = 10·log10(SNR)`.
  - Ligação entre as duas (aula 12, slides 18–20): `N_max = √(1 + S/R)`;
    substituindo em Nyquist, `2B·log2√(1+SNR) = B·log2(1+SNR)`.
- Unidades: B em Hz (aceita sufixo `k`/`M`: `3k` = 3000 Hz); C mostrado em bit/s e na
  unidade mais legível (kbit/s, Mbit/s); SNR mostrada nas duas escalas (linear e dB).
- Validação de entrada: B > 0; N inteiro ≥ 2; SNR linear ≥ 0 (SNR em dB pode ser qualquer real).
- Relatório: `relatorio.md` → **`Atividade 10 - Matheus Milanezi.docx`** gerado por script
  (python-docx 1.x já instalado), com tabelas, gráficos e o código no apêndice. O PDF fica com o Matheus.

## Interface do programa
```
python capacidade.py                                   roda os 4 experimentos (tabelas + gráficos)
python capacidade.py experimentos [--sem-graficos]     idem, explícito
python capacidade.py nyquist --B 3k --N 8              capacidade de Nyquist com unidades
python capacidade.py shannon --B 3k --snr 1000         Shannon com SNR linear
python capacidade.py shannon --B 3k --snr-db 30        Shannon com SNR em dB
python capacidade.py comparar --B 3k --snr-db 30 --N 32   Nyquist × Shannon (+ N_max)
python capacidade.py validar                           confere o programa contra os exemplos da aula
```
Gráficos salvos em `graficos/` (`exp1_nyquist.png`, `exp2_shannon.png`, `exp3_ruido.png`,
`exp4_nyquist_x_shannon.png`). Saída de texto salva em `saida_experimentos.txt`.

## Validação (casos independentes do enunciado)
Exemplos da própria aula 12 (o programa precisa reproduzir):
- Slide 14 – Nyquist, B = 20 Hz, N = 4 → **80 bit/s**.
- Slides 23–24 – 30 dB → SNR = 1000; telefonia B = 3000 Hz → slide dá **30.000 bit/s**.
  O slide arredonda log10(1001) ≈ 3 e log10(2) ≈ 0,3 (log2(1001) ≈ 10). O valor exato é
  3000 × 9,9672 ≈ **29.901,7 bit/s**. O programa deve mostrar o exato e a diferença (~0,33 %).
Conferências internas:
- Shannon com `--snr-db 30` deve dar o mesmo que `--snr 1000`.
- `2B·log2(N_max)` com `N_max = √(1+SNR)` deve coincidir com Shannon (identidade da aula).
- Nyquist com N = 2^m deve ser exatamente `2B·m`.

## Roteiro de execução
Rodar no PowerShell, dentro de `Atividade 10/`:
1. `python capacidade.py validar` → 9/9 verificações OK.
2. `python capacidade.py` → 4 tabelas no terminal + 4 PNGs em `graficos/`; o próprio programa
   grava a saída em `saida_experimentos.txt` (UTF-8; não usar `Tee-Object`, que grava UTF-16).
3. Exemplos do modo parâmetro (prints para a seção 2 do relatório):
   `python capacidade.py nyquist --B 20 --N 4`
   `python capacidade.py shannon --B 3k --snr-db 30`
   `python capacidade.py comparar --B 3k --snr-db 30 --N 32`
4. Entradas inválidas → mensagens de erro:
   `python capacidade.py nyquist --B 3k --N 1`
   `python capacidade.py shannon --B 3k --snr 1.000`   (separador de milhar: ambíguo)
5. Prints do terminal + conferir os 4 gráficos.

## Previsões (feitas pela IA à mão, antes de rodar – a confirmar com o programa)

**Exp. 1 – Nyquist** (C = 2B·log2 N → cresce linear com B e com log2 N, isto é, com os bits/símbolo)

| B \ N | 2 | 4 | 8 | 16 |
|---|---|---|---|---|
| 1 kHz | 2 kbit/s | 4 | 6 | 8 |
| 5 kHz | 10 | 20 | 30 | 40 |
| 10 kHz | 20 | 40 | 60 | 80 |

Dobrar N (de 2 para 4, 4 para 8…) soma só 1 bit/símbolo → +2B bit/s; o gráfico C × N fica "achatado" (log).

**Exp. 2 – Shannon** (eficiência C/B fixa para cada SNR → retas em função de B)

| SNR | log2(1+SNR) | B = 1 kHz | B = 10 kHz |
|---|---|---|---|
| 1.000 | 9,967 | 9,97 kbit/s (**menor**) | 99,7 kbit/s |
| 5.000 | 12,288 | 12,29 | 122,9 |
| 10.000 | 13,288 | 13,29 | 132,9 |
| 50.000 | 15,610 | 15,61 | 156,1 kbit/s (**maior**) |

SNR × 5 (1.000 → 5.000) multiplica C por só ≈ **1,23** (soma log2 5 ≈ 2,32 bit/s/Hz);
10.000 → 50.000: ≈ 1,17.

**Exp. 3 – Ruído** (B = 5 kHz)

| SNR (dB) | 0 | 5 | 10 | 15 | 20 | 25 | 30 | 35 | 40 |
|---|---|---|---|---|---|---|---|---|---|
| C (kbit/s) | 5,00 | 10,29 | 17,30 | 25,14 | 33,29 | 41,55 | 49,84 | 58,14 | 66,44 |

Em SNR alta, cada +10 dB soma ≈ B·log2 10 ≈ **16,6 kbit/s** (não multiplica): a curva C × dB vira
quase uma reta, porque o dB já é logarítmico. Em 0 dB (S = R), C = B.

**Exp. 4 – Nyquist × Shannon** (B = 3 kHz, 30 dB → SNR = 1000)
- Shannon ≈ **29.901,7 bit/s**; N_max = √1001 ≈ **31,64 níveis** (≈ 4,98 bits/símbolo).
- Nyquist: N = 2 → 6 k, 4 → 12 k, 8 → 18 k, 16 → 24 k, **32 → 30 k**, **64 → 36 k** bit/s.
- Ultrapassam o limite: **N = 32** (por só ~98 bit/s, 0,33 %) e **N = 64** (+20 %).
- Ponto sutil: com o valor arredondado do slide (30.000 bit/s), N = 32 daria **exatamente igual**
  ao limite. É o cálculo exato (N_max = 31,64 < 32) que mostra que N = 32 já passa.

## Checklist do relatório (DOCX → PDF único)
- [ ] Código-fonte completo (apêndice)
- [ ] Implementação: fórmulas, unidades, modos do programa, validação com os exemplos da aula
- [ ] Exp. 1: tabela + gráfico C × N + 3 respostas
- [ ] Exp. 2: tabela + gráfico C × B (4 curvas) + maior/menor + 3 respostas
- [ ] Exp. 3: tabela + gráfico C × SNR(dB) + comparação 10/20/30/40 dB + 3 respostas
- [ ] Exp. 4: tabela + gráfico conjunto + configurações acima do limite + 3 respostas
- [ ] Uso de IA (ferramenta, etapas, validação, exemplo confirmado/corrigido/adaptado)
