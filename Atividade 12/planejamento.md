# Atividade 12 – Quantização de Sinais – Planejamento

Entrega: PDF único no Moodle (data: conferir no Moodle). Última atividade semanal do semestre.
Material: aula 14 (`Material/aula_14.pdf`), slides 8 a 15 (amostragem, quantização e codificação).

## Decisões
- Linguagem: **Python** (arquivo único `quantizacao.py`), com matplotlib, no mesmo estilo das Atividades 10 e 11.
- Os cálculos usam **frações exatas** (`fractions.Fraction`). Em ponto flutuante, um valor que cai exatamente
  sobre um limite (ex.: 0,85 V) pode ir para o intervalo errado por arredondamento; com frações, não.
- Relatório: `relatorio.md` → **`Atividade 12 - Matheus Milanezi.docx`** gerado por script, todo o texto em
  preto. O PDF fica com o Matheus.

## Parâmetros
| Parâmetro | Valor | Origem |
|---|---|---|
| Amostras | 2,7; 0,3; −2,2; 1,3; 3,3 V | enunciado |
| Faixa | −3,4 V a +3,4 V (A = 3,4 V) | enunciado |
| Bits por amostra | b = 3 → N = 2³ = 8 intervalos | enunciado |
| Passo | Δ = 2A/N = 6,8/8 = **0,85 V** | aula 14, slide 10 |
| Nível de reconstrução | ponto médio do intervalo | enunciado |
| Período de amostragem | **Ts = 1 ms adotado** (o enunciado não informa) | exemplo do slide 9 (f = 1000 Hz) |

## Convenções (o enunciado pede que fiquem explícitas)
- **Intervalo k** (k = 0 … 7): [−A + k·Δ, −A + (k+1)·Δ). Fechado à esquerda e aberto à direita; só o último
  é fechado nos dois lados, para que +3,4 V pertença ao intervalo 7.
  - Uma amostra exatamente sobre um limite interno vai para o **intervalo de cima** (ex.: 0 V → código 100).
  - Fórmula: k = ⌊(x + A)/Δ⌋, limitado a 0 … N−1.
  - Fora da faixa: **saturação** (vai para o intervalo da ponta) e o programa avisa.
- **Código:** k em **binário natural** de 3 bits, do intervalo mais negativo (000) ao mais positivo (111).
  É a mesma ordem do slide 13 (−3,5…−1,75 → 00, …, 1,75…3,5 → 11).
- **Erro de quantização:** e = x_q − x (nível quantizado menos tensão original). Sem saturação, |e| ≤ Δ/2.
- Os slides 12 e 13 escrevem os intervalos com colchetes dos dois lados ([3,5; 1,75]) e não dizem a regra dos
  limites. No exemplo nenhuma amostra cai num limite interno, só a de 3,5 V, que é o topo da faixa. A regra
  acima reproduz a tabela do slide, inclusive 3,5 → 11 (verificado no `validar`).

## Tabela dos intervalos (prevista)
| k | Intervalo (V) | Nível (V) | Código |
|---|---|---|---|
| 0 | [−3,40; −2,55) | −2,975 | 000 |
| 1 | [−2,55; −1,70) | −2,125 | 001 |
| 2 | [−1,70; −0,85) | −1,275 | 010 |
| 3 | [−0,85; 0,00) | −0,425 | 011 |
| 4 | [0,00; 0,85) | 0,425 | 100 |
| 5 | [0,85; 1,70) | 1,275 | 101 |
| 6 | [1,70; 2,55) | 2,125 | 110 |
| 7 | [2,55; 3,40] | 2,975 | 111 |

## Previsões (feitas pela IA antes de rodar, a confirmar com o programa)
| n | t (ms) | x (V) | k | Nível (V) | e = x_q − x (V) | Código |
|---|---|---|---|---|---|---|
| 1 | 0 | 2,7 | 7 | 2,975 | +0,275 | 111 |
| 2 | 1 | 0,3 | 4 | 0,425 | +0,125 | 100 |
| 3 | 2 | −2,2 | 1 | −2,125 | +0,075 | 001 |
| 4 | 3 | 1,3 | 5 | 1,275 | −0,025 | 101 |
| 5 | 4 | 3,3 | 7 | 2,975 | −0,325 | 111 |

- Sequência transmitida: **111 100 001 101 111 → `111100001101111`** (5 × 3 = 15 bits).
- Maior erro absoluto: **amostra 5 (3,3 V), |e| = 0,325 V**, abaixo do limite Δ/2 = 0,425 V.
- Nenhuma amostra cai sobre um limite (os limites são múltiplos de 0,85 V).
- As amostras 1 e 5 (2,7 V e 3,3 V, 0,6 V de diferença) viram o **mesmo código 111**: o receptor não consegue
  distingui-las. É a perda de informação da quantização.
- Efeito do passo: cada bit a mais divide Δ por 2 e, com ele, o erro máximo (Δ/2). Com 4 bits, Δ = 0,425 V;
  com 8 bits, Δ ≈ 0,027 V. O preço é a taxa de bits: R = b · fs (slide 15).

## Interface do programa
```
python quantizacao.py                                       roda tudo (tabelas, sequência, gráficos, efeito de Δ)
python quantizacao.py quantizar --amostras "2,7; 0,3" [--bits 3] [--faixa 3,4]
python quantizacao.py validar                               verificações automáticas
```
Figuras em `graficos/`; saída de texto em `saida_experimentos.txt`.

## Experimentos
1. **Quantizador:** Δ, os 8 intervalos com nível e código, e a regra dos limites.
2. **Quantização das amostras:** tabela pedida (índice, tensão, intervalo, nível, erro, código) e a sequência.
3. **Gráficos:** (1) amostras originais e (2) valores quantizados, com os instantes de amostragem no eixo x e
   os níveis de tensão no eixo y; (3) extra: os dois juntos, com o erro de cada amostra marcado.
4. **Efeito do passo:** as mesmas 5 amostras com b = 1 … 8 bits: Δ, maior |e|, erro RMS, Δ/√12 e taxa de bits.

## Validação
- Exemplo dos slides 11 a 13 (A = 3,5 V, 2 bits): Δ = 1,75 V e os mesmos níveis e códigos da tabela do slide.
- |e| ≤ Δ/2 numa varredura densa da faixa.
- Limites: 0 → 100, 0,85 → 101, −0,85 → 011, −3,4 → 000, +3,4 → 111.
- Fora da faixa satura e avisa (−5 V → 000, +5 V → 111).
- Códigos em ordem crescente com a tensão, todos diferentes.
- Decodificar a sequência de bits devolve os níveis quantizados.
- Entradas inválidas são rejeitadas (texto, faixa ≤ 0, bits fora de 1 … 16, lista vazia).

## Teste da IA (19/11, em pasta temporária; a execução oficial é a do Matheus)
- `validar`: 9/9 OK, incluindo a tabela dos slides 11 a 13 (níveis e códigos, com 3,5 V → 11).
- Tabela das 5 amostras, sequência `111100001101111` e maior erro (amostra 5, 0,325 V): iguais às previsões.
- Erro RMS das 5 amostras: 0,202 V (referência Δ/√12 = 0,245 V).
- Efeito do passo: maior |e| cai de 1,60 V (1 bit) para 0,325 V (3 bits) e 0,012 V (8 bits), sempre ≤ Δ/2.
  Com 3 bits só 4 dos 5 códigos são distintos; a partir de 4 bits as 5 amostras ficam distinguíveis.
- **Achado da validação:** em ponto flutuante, (2,55 + 3,4)/0,85 = 6,999999999999999, e 2,55 V cairia no
  intervalo 6 (110) em vez do 7 (111). Foi o único dos 6.801 valores da varredura que mudaria; com frações
  exatas ele fica no intervalo certo. Confirma a decisão de usar `Fraction`.
- Gráfico de comparação refeito: na 1ª versão original e quantizado se cobriam; agora ficam lado a lado.

## Roteiro de execução (Matheus, PowerShell, dentro de `Atividade 12/`)
1. `python quantizacao.py validar` → todas as verificações OK.
2. `python quantizacao.py` → tabelas no terminal, figuras em `graficos/`, `saida_experimentos.txt`.
3. Exemplo extra para print: `python quantizacao.py quantizar --amostras "2,7; 0,3; -2,2; 1,3; 3,3" --bits 4`.
4. Entrada inválida: `python quantizacao.py quantizar --amostras "2,7; abc"` → mensagem de erro.

## Checklist do relatório (DOCX → PDF único)
Execução oficial do Matheus em 21/11: validar 9/9, saída idêntica ao teste da IA; exemplo de 4 bits e entrada
inválida também rodados. Relatório e docx gerados em 21/11.

- [x] Código-fonte completo e parâmetros adotados (apêndice + tabela de parâmetros)
- [x] Parte 1: Δ, os 8 intervalos e níveis, regra dos limites e ordem dos códigos
- [x] Parte 2: tabela das amostras e sequência binária
- [x] Parte 3: os dois gráficos + respostas (efeito do passo; amostra com maior erro)
- [x] Uso de IA (ferramenta, etapas, verificação, sugestão confirmada/corrigida)
- [ ] Matheus: revisar o docx, converter para PDF e enviar no Moodle
