"""
Atividade 08 - Hamming (31, 26)
Redes de Computadores - UNISINOS 2026/2 - Matheus Milanezi

Convenções adotadas:
  - posições numeradas de 1 a 31 da ESQUERDA para a DIREITA
    (o 1º caractere da palavra é a posição 1);
  - bits de paridade nas posições 1, 2, 4, 8 e 16 (potências de 2);
  - bits de dados D1..D26 ocupam as demais posições, em ordem crescente;
  - paridade PAR: cada grupo (paridade + posições que ela verifica)
    deve ter uma quantidade par de bits 1.

Uso:
  python hamming.py                          demonstração completa (3 testes + erro)
  python hamming.py -e BITS26 -e BITS26 ...  demonstração com suas próprias entradas
  python hamming.py --detalhar 2 --teste-erro 1 --erro 7
  python hamming.py --codificar BITS26       só codifica uma entrada
  python hamming.py --verificar BITS31       calcula a síndrome e corrige uma palavra recebida
  python hamming.py --interativo             lê a entrada pelo teclado
"""

import argparse
import random
import sys

N = 31                                   # bits da palavra codificada
K = 26                                   # bits de dados
PARIDADES = [1, 2, 4, 8, 16]             # posições dos bits de paridade
POS_DADOS = [i for i in range(1, N + 1) if i not in PARIDADES]

ENTRADAS_PADRAO = [
    "10101010101010101010101010",
    "11111111111111111111111111",
    "11010011100101110001011010",
]


# ----------------------------------------------------------------------------
# Núcleo: validação, codificação, síndrome e correção
# ----------------------------------------------------------------------------

def validar(bits: str, tamanho: int) -> str:
    """Remove espaços e confere se a entrada tem exatamente `tamanho` bits 0/1."""
    s = "".join(bits.split())
    invalidos = sorted({c for c in s if c not in "01"})
    if invalidos:
        raise ValueError(f"a entrada deve conter apenas 0 e 1 (encontrado: {' '.join(invalidos)})")
    if len(s) != tamanho:
        raise ValueError(f"esperados {tamanho} bits, recebidos {len(s)}")
    return s


def cobertas(p: int) -> list[int]:
    """Posições verificadas pela paridade p: todas cujo índice binário tem o bit p ligado."""
    return [i for i in range(1, N + 1) if i & p]


def codificar(dados: str) -> str:
    """Gera a palavra Hamming (31, 26) a partir de 26 bits de dados."""
    dados = validar(dados, K)
    palavra = [0] * (N + 1)              # índice 0 não é usado: palavra[i] = posição i
    for pos, bit in zip(POS_DADOS, dados):
        palavra[pos] = int(bit)
    for p in PARIDADES:
        palavra[p] = sum(palavra[i] for i in cobertas(p) if i != p) % 2
    return "".join(str(b) for b in palavra[1:])


def sindrome(palavra: str) -> int:
    """Recalcula cada grupo de paridade; os grupos que falham formam a síndrome."""
    palavra = validar(palavra, N)
    s = 0
    for p in PARIDADES:
        if sum(int(palavra[i - 1]) for i in cobertas(p)) % 2 == 1:
            s |= p
    return s


def inverter_bit(palavra: str, pos: int) -> str:
    """Inverte o bit da posição `pos` (1..31)."""
    if not 1 <= pos <= N:
        raise ValueError(f"posição deve estar entre 1 e {N}")
    i = pos - 1
    return palavra[:i] + ("1" if palavra[i] == "0" else "0") + palavra[i + 1:]


def corrigir(palavra: str) -> tuple[str, int]:
    """Retorna (palavra corrigida, síndrome). Síndrome 0 = nenhum erro detectado."""
    s = sindrome(palavra)
    if s == 0:
        return palavra, 0
    return inverter_bit(palavra, s), s


def extrair_dados(palavra: str) -> str:
    return "".join(palavra[p - 1] for p in POS_DADOS)


# ----------------------------------------------------------------------------
# Exibição
# ----------------------------------------------------------------------------

def agrupar(bits: str, n: int = 4) -> str:
    return " ".join(bits[i:i + n] for i in range(0, len(bits), n))


def nome(pos: int) -> str:
    return f"P{pos}" if pos in PARIDADES else f"D{POS_DADOS.index(pos) + 1}"


def tabela(palavra: str, marcar: int | None = None, rotulo: str = "palavra") -> None:
    """Mostra a palavra alinhada com o número de cada posição e o tipo do bit (P/D)."""
    ini = f"  {'':<10}"
    print(ini + "".join(str(i // 10) for i in range(1, N + 1)))
    print(f"  {'posição':<10}" + "".join(str(i % 10) for i in range(1, N + 1)))
    print(f"  {'tipo':<10}" + "".join("P" if i in PARIDADES else "d" for i in range(1, N + 1)))
    print(f"  {rotulo:<10}" + palavra)
    if marcar:
        print(ini + " " * (marcar - 1) + f"^ posição {marcar} ({nome(marcar)})")


def mostrar_mapeamento() -> None:
    print("Mapeamento dos bits de dados nas posições da palavra:")
    pares = [f"D{k + 1}->{p}" for k, p in enumerate(POS_DADOS)]
    for i in range(0, len(pares), 9):
        print("  " + " ".join(f"{x:<7}" for x in pares[i:i + 9]))
    print()


def detalhar_paridades(palavra: str) -> None:
    """Mostra como cada paridade foi obtida a partir dos bits de dados que ela verifica."""
    for p in PARIDADES:
        outras = [i for i in cobertas(p) if i != p]
        uns = sum(int(palavra[i - 1]) for i in outras)
        print(f"  P{p:<2} (posição {p:>2}, bit {p.bit_length() - 1} do índice) verifica as posições:")
        print(f"       {' '.join(str(i) for i in cobertas(p))}")
        print(f"       bits de dados verificados: "
              + " ".join(f"{i}={palavra[i - 1]}" for i in outras))
        print(f"       quantidade de 1s = {uns} ({'par' if uns % 2 == 0 else 'ímpar'})"
              f" -> P{p} = {uns % 2}")
    print()


def detalhar_sindrome(palavra: str) -> int:
    """Mostra cada verificação de paridade na palavra recebida e monta a síndrome."""
    bits_s = {}
    for p in PARIDADES:
        uns = sum(int(palavra[i - 1]) for i in cobertas(p))
        bits_s[p] = uns % 2
        estado = "FALHOU" if uns % 2 else "ok"
        print(f"  C{p:<2} = XOR das posições {{{','.join(str(i) for i in cobertas(p))}}}")
        print(f"        quantidade de 1s = {uns} -> C{p} = {uns % 2}  [{estado}]")
    s = sum(p for p in PARIDADES if bits_s[p])
    binario = "".join(str(bits_s[p]) for p in reversed(PARIDADES))
    print(f"  síndrome (C16 C8 C4 C2 C1) = {binario}b = {s}")
    return s


# ----------------------------------------------------------------------------
# Roteiros da atividade
# ----------------------------------------------------------------------------

def linha(titulo: str) -> None:
    print("=" * 72)
    print(titulo)
    print("=" * 72)


def parte_codificacao(entradas: list[str], detalhar: int) -> list[str]:
    linha("PARTES 1 e 2 - Codificação Hamming (31, 26)")
    mostrar_mapeamento()
    palavras = []
    for n, dados in enumerate(entradas, 1):
        palavra = codificar(dados)
        palavras.append(palavra)
        print(f"Teste {n}")
        print(f"  entrada  (26 bits): {dados}")
        print(f"  Hamming  (31 bits): {palavra}")
        print(f"  agrupado de 4 em 4: {agrupar(palavra)}")
        print(f"  paridades P1 P2 P4 P8 P16 = "
              + " ".join(palavra[p - 1] for p in PARIDADES))
        tabela(palavra)
        print()
    print(f"Como os 5 bits de paridade foram obtidos no Teste {detalhar}:")
    detalhar_paridades(palavras[detalhar - 1])
    return palavras


def parte_erro(palavra: str, pos: int, n_teste: int) -> None:
    linha(f"PARTE 3 - Erro de um único bit (palavra do Teste {n_teste})")
    recebida = inverter_bit(palavra, pos)
    print(f"Palavra correta     : {palavra}")
    print(f"Bit invertido       : posição {pos} ({nome(pos)}), "
          f"{palavra[pos - 1]} -> {recebida[pos - 1]}")
    print(f"Palavra com erro    : {recebida}")
    print()
    tabela(palavra, rotulo="correta")
    tabela(recebida, marcar=pos, rotulo="com erro")
    print()
    print("Verificação da palavra recebida:")
    s = detalhar_sindrome(recebida)
    print()
    corrigida, _ = corrigir(recebida)
    print(f"Posição identificada: {s} ({nome(s)})" if s else "Nenhum erro detectado")
    print(f"Palavra corrigida   : {corrigida}")
    print(f"Igual à original?   : {'SIM' if corrigida == palavra else 'NÃO'}")
    print(f"Síndrome após correção: {sindrome(corrigida)}")
    print(f"Dados recuperados   : {extrair_dados(corrigida)}")
    print()


def autoteste(palavras: list[str], aleatorios: int = 1000) -> None:
    linha("AUTOTESTE - todas as posições de erro possíveis")
    for n, palavra in enumerate(palavras, 1):
        acertos = sum(
            corrigir(inverter_bit(palavra, pos)) == (palavra, pos) for pos in range(1, N + 1)
        )
        print(f"  Teste {n}: síndrome da palavra sem erro = {sindrome(palavra)}; "
              f"erros de 1 bit localizados e corrigidos: {acertos}/{N}")
    rng = random.Random(2026)
    ok = xor_ok = 0
    for _ in range(aleatorios):
        dados = "".join(rng.choice("01") for _ in range(K))
        palavra = codificar(dados)
        pos = rng.randint(1, N)
        recebida = inverter_bit(palavra, pos)
        corrigida, s = corrigir(recebida)
        ok += (s == pos and corrigida == palavra and extrair_dados(corrigida) == dados)
        # conferência independente: a síndrome é o XOR dos índices das posições com bit 1
        xor_indices = 0
        for i, b in enumerate(recebida, 1):
            if b == "1":
                xor_indices ^= i
        xor_ok += (xor_indices == s)
    print(f"  {aleatorios} entradas aleatórias com 1 bit invertido: {ok}/{aleatorios} corrigidas")
    print(f"  síndrome == XOR dos índices dos bits 1: {xor_ok}/{aleatorios}")
    print()


def modo_verificar(palavra: str) -> None:
    palavra = validar(palavra, N)
    linha("Verificação de palavra recebida")
    tabela(palavra, rotulo="recebida")
    print()
    s = detalhar_sindrome(palavra)
    corrigida, _ = corrigir(palavra)
    if s:
        print(f"Erro na posição {s} ({nome(s)})")
        print(f"Palavra corrigida: {corrigida}")
    else:
        print("Síndrome 0: nenhum erro de bit único detectado")
    print(f"Dados: {extrair_dados(corrigida)}")


def ler_teclado() -> str:
    while True:
        try:
            return validar(input(f"Digite {K} bits de dados: "), K)
        except ValueError as e:
            print(f"  entrada inválida: {e}")


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

    ap = argparse.ArgumentParser(description="Codificador/decodificador Hamming (31, 26)")
    ap.add_argument("-e", "--entrada", action="append", metavar="BITS26",
                    help="entrada de 26 bits (repita para vários testes)")
    ap.add_argument("--detalhar", type=int, default=3,
                    help="teste cujas paridades serão detalhadas (padrão: 3)")
    ap.add_argument("--teste-erro", type=int, default=3,
                    help="teste usado na injeção de erro (padrão: 3)")
    ap.add_argument("--erro", type=int, default=13,
                    help="posição (1..31) do bit a inverter (padrão: 13)")
    ap.add_argument("--codificar", metavar="BITS26", help="apenas codifica a entrada")
    ap.add_argument("--verificar", metavar="BITS31", help="verifica/corrige uma palavra recebida")
    ap.add_argument("--interativo", action="store_true", help="lê a entrada pelo teclado")
    args = ap.parse_args()

    try:
        if args.codificar:
            dados = validar(args.codificar, K)
            palavra = codificar(dados)
            print(f"entrada  (26 bits): {dados}")
            print(f"Hamming  (31 bits): {palavra}")
            tabela(palavra)
            print()
            detalhar_paridades(palavra)
            return
        if args.verificar:
            modo_verificar(args.verificar)
            return

        entradas = [ler_teclado()] if args.interativo else (args.entrada or ENTRADAS_PADRAO)
        entradas = [validar(e, K) for e in entradas]
        detalhar = min(args.detalhar, len(entradas))
        teste_erro = min(args.teste_erro, len(entradas))

        palavras = parte_codificacao(entradas, detalhar)
        parte_erro(palavras[teste_erro - 1], args.erro, teste_erro)
        autoteste(palavras)
    except ValueError as e:
        print(f"Erro: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
