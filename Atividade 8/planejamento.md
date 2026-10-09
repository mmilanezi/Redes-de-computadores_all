# Atividade 08 – Hamming (31, 26) – Planejamento

## Decisões
- Linguagem: **Python 3** (arquivo único `hamming.py`, sem dependências externas).
- Convenção: posição 1 = **primeiro caractere à esquerda**; paridades em 1, 2, 4, 8, 16; dados D1..D26 nas demais posições em ordem crescente; **paridade par**.
- Paridade `Pp` verifica toda posição `i` com `i & p != 0` (bit `p` ligado no índice binário).
- Síndrome = valor binário `C16 C8 C4 C2 C1` das verificações que falharam = posição do bit errado (0 = sem erro).

## Roteiro de execução
1. `python hamming.py` → 3 testes, detalhamento das paridades do Teste 3, erro na posição 13 (D9) do Teste 3, autoteste.
2. (Opcional) trocar o Teste 3 pela matrícula em binário (26 bits):
   `python hamming.py -e 1010...(t1) -e 1111...(t2) -e <matrícula>`
3. (Opcional) erro em bit de paridade: `python hamming.py --erro 16` → síndrome deve dar 16.
4. Validação de entrada: `python hamming.py --codificar 1010` e com caractere inválido → mensagens de erro.
5. Salvar a saída: `python hamming.py > saida.txt` + prints do terminal para o relatório.

## Previsões (a confirmar com a execução)
- Teste 2 (26 bits em 1): cada grupo tem 15 bits de dados em 1 (ímpar) → todas as paridades = 1 → palavra = 31 bits em 1.
- Erro na posição 13 = 01101b → devem falhar C1, C4 e C8 (síndrome 13).
- Erro na posição 16 (P16) → só C16 falha → síndrome 16, e os dados recuperados não mudam.

## Checklist do relatório (PDF único)
- [ ] Código-fonte completo
- [ ] 3 testes (entrada 26 bits → palavra 31 bits)
- [ ] Detalhamento das 5 paridades + posições verificadas por cada uma
- [ ] Teste de erro: palavra correta, com erro, síndrome, corrigida
- [ ] Análise (4 perguntas)
- [ ] Uso de IA (ferramenta, etapas, validação, exemplo de sugestão confirmada/corrigida)
