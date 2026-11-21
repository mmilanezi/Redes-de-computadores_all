"""
Atividade 12 - Quantização de Sinais
Redes de Computadores - UNISINOS 2026/2 - Matheus Milanezi

Quantizador uniforme de b bits na faixa de -A a +A (aula 14, slides 10 a 13):
  N = 2^b intervalos de largura Δ = 2A/N; cada intervalo é representado pelo seu ponto médio.

Convenções:
  Intervalo k (k = 0 .. N-1): [-A + k·Δ, -A + (k+1)·Δ), fechado à esquerda e aberto à direita.
    Só o último é fechado nos dois lados, para que +A pertença ao intervalo mais alto.
    Uma amostra exatamente sobre um limite interno vai para o intervalo de cima: k = ⌊(x + A)/Δ⌋.
    Amostras fora da faixa são saturadas (vão para o intervalo da ponta) e o programa avisa.
  Código: k em binário natural de b bits; o intervalo mais negativo é 000 e o mais positivo 111
    (mesma ordem do slide 13: [-3,5; -1,75] -> 00 ... [1,75; 3,5] -> 11).
  Erro de quantização: e = x_q - x (nível quantizado menos tensão original).

Os cálculos usam frações exatas (fractions.Fraction): um valor sobre um limite, como 0,85 V,
não cai no intervalo errado por arredondamento de ponto flutuante.

Uso:
  python quantizacao.py                                    todos os experimentos
  python quantizacao.py experimentos [--pasta DIR] [--saida ARQ]
  python quantizacao.py quantizar --amostras "2,7; 0,3" [--bits 3] [--faixa 3,4] [--pasta DIR]
  python quantizacao.py validar
"""

import argparse
import math
import sys
from contextlib import ExitStack, redirect_stdout
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path

PASTA = Path(__file__).resolve().parent

# Parâmetros do enunciado
AMOSTRAS = "2,7; 0,3; -2,2; 1,3; 3,3"   # V
FAIXA = "3,4"                           # A: faixa de -A a +A (V)
BITS = 3                                # bits por amostra (N = 8 intervalos)
TS_MS = 1                               # período de amostragem adotado (ms); o enunciado não informa
BITS_PASSO = range(1, 9)                # resoluções comparadas no experimento do passo
MAX_AMOSTRAS = 64

# Exemplo da aula 14, slides 11 a 13 (A = 3,5 V, 2 bits)
SLIDE_AMOSTRAS = "3,5; -1,0437; 0,8238; -2,2014; -0,1305"
SLIDE_FAIXA = "3,5"
SLIDE_NIVEIS = ["2,625", "-0,875", "0,875", "-2,625", "-0,875"]
SLIDE_CODIGOS = ["11", "01", "10", "00", "01"]

# Cores: séries em ordem fixa (paleta validada para daltonismo) e tintas neutras
CORES = ["#2a78d6", "#eb6834"]
TINTA, TINTA2, MUDA, GRADE, EIXO, FAIXA_CLARA = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7", "#f4f3ee"


# ----------------------------------------------------------------------------
# Quantizador
# ----------------------------------------------------------------------------

@dataclass(frozen=True)
class Quantizador:
    a: Fraction     # faixa de -a a +a (V)
    bits: int       # bits por amostra

    def __post_init__(self):
        if self.a <= 0:
            raise ValueError(f"a faixa deve ser positiva: A = {br(self.a)} V")
        if not 1 <= self.bits <= 16:
            raise ValueError(f"bits por amostra fora de 1 a 16: {self.bits}")

    @property
    def n(self) -> int:
        return 2 ** self.bits

    @property
    def delta(self) -> Fraction:
        return 2 * self.a / self.n

    def limites(self, k: int) -> tuple[Fraction, Fraction]:
        inferior = -self.a + k * self.delta
        return inferior, inferior + self.delta

    def nivel(self, k: int) -> Fraction:
        """Ponto médio do intervalo k."""
        return -self.a + (k + Fraction(1, 2)) * self.delta

    def codigo(self, k: int) -> str:
        return format(k, f"0{self.bits}b")

    def intervalo(self, x: Fraction) -> tuple[int, bool]:
        """Índice k do intervalo de x e se houve saturação."""
        if x < -self.a:
            return 0, True
        if x > self.a:
            return self.n - 1, True
        return min(math.floor((x + self.a) / self.delta), self.n - 1), False   # x = +A fica no último

    @property
    def casas_limite(self) -> int:
        return max(decimais(self.a), decimais(self.delta), 2)

    @property
    def casas_nivel(self) -> int:
        return max(decimais(self.a), decimais(self.delta / 2), 3)

    def texto_intervalo(self, k: int) -> str:
        inferior, superior = self.limites(k)
        c = self.casas_limite
        return f"[{br(inferior, c)}; {br(superior, c)}{']' if k == self.n - 1 else ')'}"


@dataclass(frozen=True)
class Amostra:
    n: int              # índice (1, 2, ...)
    t_ms: Fraction      # instante de amostragem
    x: Fraction         # tensão original
    k: int              # intervalo
    xq: Fraction        # nível quantizado
    codigo: str
    saturou: bool

    @property
    def erro(self) -> Fraction:
        return self.xq - self.x


def quantizar(q: Quantizador, amostras: list[Fraction]) -> list[Amostra]:
    resultado = []
    for i, x in enumerate(amostras):
        k, saturou = q.intervalo(x)
        resultado.append(Amostra(i + 1, Fraction(i * TS_MS), x, k, q.nivel(k), q.codigo(k), saturou))
    return resultado


def decodificar(q: Quantizador, sequencia: str) -> list[Fraction]:
    """Receptor: corta a sequência em grupos de b bits e devolve o nível de cada grupo."""
    if len(sequencia) % q.bits:
        raise ValueError(f"a sequência tem {len(sequencia)} bits, que não é múltiplo de {q.bits}")
    return [q.nivel(int(sequencia[i:i + q.bits], 2)) for i in range(0, len(sequencia), q.bits)]


def erro_rms(resultado: list[Amostra]) -> float:
    return math.sqrt(sum(float(a.erro) ** 2 for a in resultado) / len(resultado))


# ----------------------------------------------------------------------------
# Entrada e formatação
# ----------------------------------------------------------------------------

def ler_numero(texto: str, nome: str) -> Fraction:
    """Lê '2,7' ou '2.7' como fração exata (27/10)."""
    try:
        return Fraction(texto.strip().replace(",", "."))
    except (ValueError, ZeroDivisionError):
        raise ValueError(f"{nome} inválido: '{texto.strip()}'") from None


def ler_amostras(texto: str) -> list[Fraction]:
    """Amostras separadas por ';' (a vírgula é o separador decimal), como no enunciado."""
    itens = [s for s in texto.strip().strip("[]").split(";") if s.strip()]
    if not itens:
        raise ValueError("nenhuma amostra informada")
    if len(itens) > MAX_AMOSTRAS:
        raise ValueError(f"no máximo {MAX_AMOSTRAS} amostras (recebidas {len(itens)})")
    return [ler_numero(s, "amostra") for s in itens]


def ler_bits(texto: str) -> int:
    try:
        return int(texto)
    except ValueError:
        raise ValueError(f"número de bits inválido: '{texto}'") from None


def decimais(x: Fraction, maximo: int = 6) -> int:
    """Menor número de casas que escreve x sem arredondar (até o máximo)."""
    for d in range(maximo + 1):
        if (x * 10 ** d).denominator == 1:
            return d
    return maximo


def br(x, casas: int = 2) -> str:
    if isinstance(x, Fraction):     # arredonda a fração exata, sem passar por float (0,2125 -> 0,2125)
        x = round(x, casas)
    return f"{float(x):,.{casas}f}".replace(",", "_").replace(".", ",").replace("_", ".")


def br_sinal(x, casas: int = 3) -> str:
    return ("+" if x > 0 else "") + br(x, casas)


def texto_tensao(x: Fraction) -> str:
    """Tensão com as casas que ela tem (2,7 -> '2,7'; -1,0437 -> '-1,0437')."""
    return br(x, max(1, decimais(x)))


def linha(titulo: str) -> None:
    print("=" * 78)
    print(titulo)
    print("=" * 78)


def mostrar_caminho(caminho: Path) -> str:
    try:
        return str(caminho.resolve().relative_to(Path.cwd()))
    except ValueError:
        return str(caminho)


# ----------------------------------------------------------------------------
# Tabelas no terminal
# ----------------------------------------------------------------------------

def tabela_quantizador(q: Quantizador) -> None:
    print(f"  Faixa: {br(-q.a)} V a +{br(q.a)} V (A = {br(q.a, 1)} V)")
    print(f"  Bits por amostra: b = {q.bits}  ->  N = 2^{q.bits} = {q.n} intervalos")
    print(f"  Passo: Δ = 2A/N = 2·{br(q.a, 1)}/{q.n} = {br(q.delta, 4)} V   (erro máximo Δ/2 = {br(q.delta / 2, 4)} V)")
    print()
    print("  Regra nos limites: intervalo [inferior; superior), fechado à esquerda e aberto à direita;")
    print(f"  só o último é fechado ([...; +{br(q.a)}]). Valor sobre um limite interno vai para o intervalo")
    print("  de cima: k = ⌊(x + A)/Δ⌋. Fora da faixa: saturação no intervalo da ponta.")
    print(f"  Códigos: k em binário natural, do mais negativo ({q.codigo(0)}) ao mais positivo ({q.codigo(q.n - 1)}).")
    print(f"  Nível de reconstrução: ponto médio do intervalo, -A + (k + 1/2)·Δ.")
    if q.n > 32:
        return
    print()
    print(f"  {'k':>3}   {'intervalo (V)':<22}{'nível (V)':>10}   {'código':<8}")
    for k in range(q.n):
        print(f"  {k:>3}   {q.texto_intervalo(k):<22}{br(q.nivel(k), q.casas_nivel):>10}   {q.codigo(k):<8}")


def tabela_amostras(q: Quantizador, resultado: list[Amostra]) -> None:
    print(f"  Instantes de amostragem: t = (n - 1)·Ts, com Ts = {TS_MS} ms adotado")
    print(f"  Erro de quantização: e = x_q - x\n")
    ce = max(q.casas_nivel, *(decimais(a.x) for a in resultado))
    print(f"  {'n':>3}{'t (ms)':>8}{'x (V)':>9}{'k':>4}   {'intervalo (V)':<20}{'x_q (V)':>9}"
          f"{'e (V)':>10}{'|e| (V)':>9}   código")
    for a in resultado:
        print(f"  {a.n:>3}{br(a.t_ms, 0):>8}{texto_tensao(a.x):>9}{a.k:>4}   "
              f"{q.texto_intervalo(a.k):<20}{br(a.xq, q.casas_nivel):>9}{br_sinal(a.erro, ce):>10}"
              f"{br(abs(a.erro), ce):>9}   {a.codigo}{'  (saturou)' if a.saturou else ''}")
    print()
    sequencia = "".join(a.codigo for a in resultado)
    print(f"  Códigos na ordem das amostras: {' '.join(a.codigo for a in resultado)}")
    print(f"  Sequência binária transmitida: {sequencia}  ({len(resultado)} × {q.bits} = {len(sequencia)} bits)")
    print()
    pior = max(resultado, key=lambda a: abs(a.erro))
    print(f"  Maior erro absoluto: amostra {pior.n} ({texto_tensao(pior.x)} V -> {br(pior.xq, q.casas_nivel)} V), "
          f"|e| = {br(abs(pior.erro), ce)} V")
    print(f"  Erro RMS das amostras: {br(erro_rms(resultado), 3)} V   "
          f"(referência para erro uniforme: Δ/√12 = {br(float(q.delta) / math.sqrt(12), 3)} V)")
    validas = [a for a in resultado if not a.saturou]
    if validas:
        dentro = all(abs(a.erro) <= q.delta / 2 for a in validas)
        print(f"  |e| ≤ Δ/2 = {br(q.delta / 2, q.casas_nivel)} V em todas as amostras dentro da faixa: "
              f"{'sim' if dentro else 'NÃO'}")
    saturadas = [a.n for a in resultado if a.saturou]
    if saturadas:
        print(f"  Aviso: amostra(s) {', '.join(map(str, saturadas))} fora da faixa; saturadas no intervalo da ponta.")
    repetidos = {}
    for a in resultado:
        repetidos.setdefault(a.codigo, []).append(a)
    for codigo, grupo in repetidos.items():
        if len(grupo) > 1:
            print(f"  Mesmo código {codigo}: amostras {' e '.join(str(a.n) for a in grupo)} "
                  f"({' e '.join(texto_tensao(a.x) + ' V' for a in grupo)}) ficam indistinguíveis no receptor.")
    recebidos = decodificar(q, sequencia)
    print(f"  Receptor (decodifica a sequência): {'; '.join(br(v, q.casas_nivel) for v in recebidos)} V")


def tabela_passo(a: Fraction, amostras: list[Fraction]) -> None:
    print(f"  Mesmas {len(amostras)} amostras, faixa ±{br(a, 1)} V, variando os bits por amostra.")
    print(f"  Taxa de bits R = b · fs, com fs = 1/Ts = {br(1000 / TS_MS, 0)} amostras/s.\n")
    print(f"  {'b':>3}{'N':>6}{'Δ (V)':>10}{'Δ/2 (V)':>10}{'maior |e|':>11}{'erro RMS':>10}{'Δ/√12':>9}"
          f"{'códigos distintos':>19}{'R (bit/s)':>11}")
    for b in BITS_PASSO:
        q = Quantizador(a, b)
        r = quantizar(q, amostras)
        print(f"  {b:>3}{q.n:>6}{br(q.delta, 4):>10}{br(q.delta / 2, 4):>10}"
              f"{br(max(abs(x.erro) for x in r), 4):>11}{br(erro_rms(r), 4):>10}"
              f"{br(float(q.delta) / math.sqrt(12), 4):>9}"
              f"{len({x.codigo for x in r}):>12} de {len(r):<4}{br(b * 1000 / TS_MS, 0):>11}")


# ----------------------------------------------------------------------------
# Gráficos
# ----------------------------------------------------------------------------

def preparar_matplotlib():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib import font_manager

    instaladas = {f.name for f in font_manager.fontManager.ttflist}
    fontes = [f for f in ("Segoe UI", "DejaVu Sans") if f in instaladas] or ["sans-serif"]
    plt.rcParams.update({
        "font.family": fontes, "font.size": 10,
        "figure.facecolor": "white", "axes.facecolor": "white",
        "axes.edgecolor": EIXO, "axes.labelcolor": TINTA2, "axes.titlecolor": TINTA,
        "axes.titlesize": 12, "axes.titleweight": "bold", "axes.titlelocation": "left",
        "axes.titlepad": 12, "axes.spines.top": False, "axes.spines.right": False,
        "axes.grid": False, "axes.axisbelow": True, "grid.color": GRADE, "grid.linewidth": 0.8,
        "xtick.color": EIXO, "ytick.color": EIXO, "xtick.labelcolor": TINTA2,
        "ytick.labelcolor": TINTA2, "legend.frameon": False, "legend.fontsize": 9,
        "savefig.dpi": 200,
    })
    return plt


def salvar(plt, fig, pasta: Path, arquivo: str) -> None:
    pasta.mkdir(parents=True, exist_ok=True)
    fig.savefig(pasta / arquivo, bbox_inches="tight", pad_inches=0.2)
    plt.close(fig)
    print(f"  figura salva: {mostrar_caminho(pasta / arquivo)}")


def eixos_amostras(plt, q: Quantizador, resultado: list[Amostra], titulo: str):
    """Eixo x nos instantes de amostragem, faixa de tensão do quantizador no eixo y."""
    fig, ax = plt.subplots(figsize=(8.4, 5.2))
    t = [float(a.t_ms) for a in resultado]
    topo = max([float(q.a)] + [abs(float(a.x)) for a in resultado]) * 1.08
    ax.set_ylim(-topo, topo)
    ax.set_xlim(t[0] - 0.6 * TS_MS, t[-1] + 0.6 * TS_MS)
    passo = max(1, len(resultado) // 16)
    ax.set_xticks(t[::passo])
    ax.set_xticklabels([f"{br(a.t_ms, 0)}\nn = {a.n}" for a in resultado[::passo]])
    ax.set_xlabel("Instante de amostragem t (ms)")
    ax.set_ylabel("Tensão (V)")
    ax.axhline(0, color=TINTA2, linewidth=0.9, zorder=1)
    ax.set_title(titulo)
    return fig, ax, t


def marcar_limites(ax, q: Quantizador) -> list[float]:
    """Linhas tracejadas nos limites dos intervalos (múltiplos de Δ); devolve as posições."""
    limites = [float(q.limites(k)[0]) for k in range(q.n)] + [float(q.a)]
    if q.n <= 16:
        for y in limites:
            ax.axhline(y, color=EIXO, linewidth=0.8, linestyle=(0, (4, 3)), zorder=0)
        ax.set_yticks(limites)
        ax.set_yticklabels([br(y, q.casas_limite) for y in limites])
    return limites


def faixas_intervalos(ax, q: Quantizador) -> None:
    """Intervalos alternados em cinza claro, com o código de cada um à direita."""
    if q.n > 16:
        return
    for k in range(q.n):
        inferior, superior = (float(v) for v in q.limites(k))
        if k % 2 == 0:
            ax.axhspan(inferior, superior, color=FAIXA_CLARA, zorder=0, linewidth=0)
        ax.text(1.01, float(q.nivel(k)), q.codigo(k), transform=ax.get_yaxis_transform(),
                ha="left", va="center", fontsize=9, color=TINTA2, family="monospace")
    ax.text(1.01, 1.0, "código", transform=ax.transAxes, ha="left", va="bottom", fontsize=8.5, color=MUDA)


def rotular_ponto(ax, t: float, y: float, texto: str, cor: str = TINTA, deslocamento: float = 9) -> None:
    ax.annotate(texto, (t, y), xytext=(0, deslocamento if y >= 0 else -deslocamento),
                textcoords="offset points", ha="center", va="bottom" if y >= 0 else "top",
                fontsize=9, color=cor, bbox=dict(boxstyle="square,pad=0.15", facecolor="white", edgecolor="none"))


def figura_originais(plt, q: Quantizador, resultado: list[Amostra], pasta: Path, arquivo: str) -> None:
    fig, ax, t = eixos_amostras(plt, q, resultado, "Amostras originais")
    marcar_limites(ax, q)
    x = [float(a.x) for a in resultado]
    ax.vlines(t, 0, x, color=CORES[0], linewidth=2, zorder=2)
    ax.plot(t, x, "o", color=CORES[0], markersize=9, markeredgecolor="white", markeredgewidth=2, zorder=3,
            label="amostra x(t)")
    ax.plot([], [], color=EIXO, linewidth=0.8, linestyle=(0, (4, 3)),
            label=f"limites dos intervalos (passo Δ = {br(q.delta, q.casas_limite)} V)")
    if len(resultado) <= 16:
        for a in resultado:
            rotular_ponto(ax, float(a.t_ms), float(a.x), f"{texto_tensao(a.x)} V")
    ax.legend(loc="upper left", bbox_to_anchor=(0, -0.16), ncol=2)
    salvar(plt, fig, pasta, arquivo)


def figura_quantizadas(plt, q: Quantizador, resultado: list[Amostra], pasta: Path, arquivo: str) -> None:
    fig, ax, t = eixos_amostras(plt, q, resultado, "Valores quantizados")
    if q.n <= 16:
        niveis = [float(q.nivel(k)) for k in range(q.n)]
        for y in niveis:
            ax.axhline(y, color=EIXO, linewidth=0.8, linestyle=(0, (1, 2)), zorder=0)
        ax.set_yticks(niveis)
        ax.set_yticklabels([br(y, q.casas_nivel) for y in niveis])
        faixas_intervalos(ax, q)
    xq = [float(a.xq) for a in resultado]
    ax.vlines(t, 0, xq, color=CORES[1], linewidth=2, zorder=2)
    ax.plot(t, xq, "s", color=CORES[1], markersize=9, markeredgecolor="white", markeredgewidth=2, zorder=3,
            label="valor quantizado x_q")
    ax.plot([], [], color=EIXO, linewidth=0.8, linestyle=(0, (1, 2)),
            label=f"níveis de reconstrução (pontos médios, {q.n} níveis)")
    if len(resultado) <= 16:
        for a in resultado:
            rotular_ponto(ax, float(a.t_ms), float(a.xq), f"{br(a.xq, q.casas_nivel)} V · {a.codigo}")
    ax.legend(loc="upper left", bbox_to_anchor=(0, -0.16), ncol=2)
    salvar(plt, fig, pasta, arquivo)


def figura_comparacao(plt, q: Quantizador, resultado: list[Amostra], pasta: Path, arquivo: str) -> None:
    fig, ax, t = eixos_amostras(plt, q, resultado, "Original × quantizado, com o erro de cada amostra")
    marcar_limites(ax, q)
    faixas_intervalos(ax, q)
    # Original um pouco à esquerda do instante e quantizado um pouco à direita, para não se cobrirem;
    # a ligação entre os dois mostra o tamanho e o sentido do erro.
    dx = 0.12 * TS_MS
    x = [float(a.x) for a in resultado]
    xq = [float(a.xq) for a in resultado]
    for ti, xi, xqi in zip(t, x, xq):
        ax.plot([ti - dx, ti + dx], [xi, xqi], color=TINTA2, linewidth=1.4, zorder=2)
    ax.plot([ti - dx for ti in t], x, "o", markerfacecolor="white", markeredgecolor=CORES[0], markeredgewidth=2,
            markersize=9, zorder=4, label="original x")
    ax.plot([ti + dx for ti in t], xq, "s", color=CORES[1], markersize=9, markeredgecolor="white",
            markeredgewidth=2, zorder=3, label="quantizado x_q")
    ax.plot([], [], color=TINTA2, linewidth=1.4, label="erro e = x_q − x")
    if len(resultado) <= 16:
        pior = max(resultado, key=lambda a: abs(a.erro))
        ce = max(q.casas_nivel, *(decimais(a.x) for a in resultado))
        for a in resultado:
            ultimo = a is resultado[-1]     # o último rótulo vai à esquerda, longe dos códigos da margem
            ax.annotate(f"e = {br_sinal(a.erro, ce)} V",
                        (float(a.t_ms) + (-dx if ultimo else dx), float(a.x + a.xq) / 2),
                        xytext=(-12 if ultimo else 12, 0), textcoords="offset points",
                        ha="right" if ultimo else "left", va="center", fontsize=8.5, color=TINTA,
                        fontweight="bold" if a is pior else "normal")
    ax.legend(loc="upper left", bbox_to_anchor=(0, -0.16), ncol=3)
    salvar(plt, fig, pasta, arquivo)


def figuras(plt, q: Quantizador, resultado: list[Amostra], pasta: Path, prefixo: str) -> None:
    figura_originais(plt, q, resultado, pasta, f"{prefixo}amostras_originais.png")
    figura_quantizadas(plt, q, resultado, pasta, f"{prefixo}valores_quantizados.png")
    figura_comparacao(plt, q, resultado, pasta, f"{prefixo}comparacao.png")


# ----------------------------------------------------------------------------
# Experimentos
# ----------------------------------------------------------------------------

class Tee:
    """Escreve no terminal e num arquivo ao mesmo tempo."""

    def __init__(self, *fluxos):
        self.fluxos = fluxos

    def write(self, texto: str) -> int:
        for f in self.fluxos:
            f.write(texto)
        return len(texto)

    def flush(self) -> None:
        for f in self.fluxos:
            f.flush()


def rodar(q: Quantizador, amostras: list[Fraction], pasta: Path, prefixo: str) -> None:
    linha(f"1. QUANTIZADOR UNIFORME DE {q.bits} BITS")
    tabela_quantizador(q)
    print()
    linha("2. AMOSTRAS QUANTIZADAS E CODIFICADAS")
    resultado = quantizar(q, amostras)
    tabela_amostras(q, resultado)
    print()
    linha("3. GRÁFICOS")
    figuras(preparar_matplotlib(), q, resultado, pasta, prefixo)
    print()
    linha("4. EFEITO DO PASSO DE QUANTIZAÇÃO (b = 1 a 8 bits)")
    tabela_passo(q.a, amostras)
    print()


def modo_experimentos(pasta: Path, saida: str) -> None:
    q = Quantizador(ler_numero(FAIXA, "faixa"), BITS)
    amostras = ler_amostras(AMOSTRAS)
    with ExitStack() as pilha:
        if saida:
            Path(saida).parent.mkdir(parents=True, exist_ok=True)
            arq = pilha.enter_context(open(saida, "w", encoding="utf-8"))
            pilha.enter_context(redirect_stdout(Tee(sys.stdout, arq)))
        print(f"Amostras: [{AMOSTRAS}] V\n")
        rodar(q, amostras, pasta, "")
    if saida:
        print(f"Saída gravada em: {mostrar_caminho(Path(saida))}")


# ----------------------------------------------------------------------------
# Validação
# ----------------------------------------------------------------------------

def modo_validar() -> bool:
    linha("VALIDAÇÃO - exemplo da aula 14 e conferências internas")
    resultados = []

    def caso(descricao: str, ok: bool, detalhe: str) -> None:
        resultados.append(ok)
        print(f"  [{'OK' if ok else 'FALHOU'}] {descricao}")
        print(f"         {detalhe}")

    q = Quantizador(ler_numero(FAIXA, "faixa"), BITS)
    caso("Passo do enunciado: Δ = 2A/N = 2·3,4/8 = 0,85 V", q.delta == Fraction(85, 100),
         f"Δ = {q.delta} V (fração exata) = {br(q.delta)} V, N = {q.n}")

    slide = Quantizador(ler_numero(SLIDE_FAIXA, "faixa"), 2)
    r = quantizar(slide, ler_amostras(SLIDE_AMOSTRAS))
    niveis = [br(a.xq, 3) for a in r]
    codigos = [a.codigo for a in r]
    esperado = [br(ler_numero(v, "nível"), 3) for v in SLIDE_NIVEIS]
    caso("Aula 14, slides 11 a 13 (A = 3,5 V, 2 bits): Δ, níveis e códigos da tabela",
         slide.delta == Fraction(7, 4) and niveis == esperado and codigos == SLIDE_CODIGOS,
         f"Δ = {br(slide.delta)} V; níveis {'; '.join(niveis)}; códigos {' '.join(codigos)}\n"
         f"         (slide: Δ = 1,75; {'; '.join(esperado)}; {' '.join(SLIDE_CODIGOS)};"
         f" inclui 3,5 V = topo da faixa -> 11)")

    varredura = [Fraction(i, 1000) for i in range(-3400, 3401)]
    pior = max(abs(q.nivel(q.intervalo(x)[0]) - x) for x in varredura)
    caso("|e| ≤ Δ/2 em toda a faixa (varredura de -3,4 a +3,4 V em passos de 1 mV)", pior <= q.delta / 2,
         f"maior |e| = {br(pior, 3)} V, Δ/2 = {br(q.delta / 2, 3)} V ({len(varredura)} valores)")

    limites = {"0": "100", "0,85": "101", "-0,85": "011", "2,55": "111", "-3,4": "000", "3,4": "111"}
    obtidos = {v: q.codigo(q.intervalo(ler_numero(v, "x"))[0]) for v in limites}
    caso("Valores sobre os limites vão para o intervalo de cima; ±A ficam nas pontas", obtidos == limites,
         ", ".join(f"{v} V -> {c}" for v, c in obtidos.items()))

    fora = [q.intervalo(ler_numero(v, "x")) for v in ("-5", "5")]
    caso("Fora da faixa: saturação no intervalo da ponta, com aviso", fora == [(0, True), (q.n - 1, True)],
         f"-5 V -> {q.codigo(fora[0][0])} (saturou: {fora[0][1]}), +5 V -> {q.codigo(fora[1][0])} "
         f"(saturou: {fora[1][1]})")

    codigos = [q.codigo(k) for k in range(q.n)]
    niveis_k = [q.nivel(k) for k in range(q.n)]
    caso("Códigos crescem com a tensão, todos diferentes; níveis igualmente espaçados de Δ",
         codigos == sorted(set(codigos)) and len(codigos) == q.n
         and all(b - a == q.delta for a, b in zip(niveis_k, niveis_k[1:])),
         f"{' '.join(codigos)}; níveis de {br(niveis_k[0], 3)} a {br(niveis_k[-1], 3)} V")

    r = quantizar(q, ler_amostras(AMOSTRAS))
    sequencia = "".join(a.codigo for a in r)
    caso("Decodificar a sequência transmitida devolve os níveis quantizados",
         decodificar(q, sequencia) == [a.xq for a in r],
         f"{sequencia} -> {'; '.join(br(v, 3) for v in decodificar(q, sequencia))} V")

    def k_float(x: float) -> int:
        return min(math.floor((x + 3.4) / 0.85), 7)

    divergentes = [x for x in varredura if k_float(float(x)) != q.intervalo(x)[0]]
    exemplo = ", ".join(f"{br(x)} V: frações -> {q.codigo(q.intervalo(x)[0])}, float -> {q.codigo(k_float(float(x)))}"
                        f" ((x + 3,4)/0,85 = {(float(x) + 3.4) / 0.85!r})" for x in divergentes)
    caso("Frações exatas evitam erro de arredondamento nos limites (comparação com float)",
         all(q.intervalo(x)[0] == (x + q.a) / q.delta for x in divergentes),
         f"{len(divergentes)} dos {len(varredura)} valores mudariam de intervalo com float"
         + (f":\n         {exemplo}" if divergentes else ""))

    invalidas = [(ler_amostras, "2,7; abc"), (ler_amostras, ""), (ler_amostras, "; ;"),
                 (ler_amostras, "; ".join(["1"] * (MAX_AMOSTRAS + 1))), (ler_bits, "três"),
                 (lambda s: Quantizador(Fraction(s), 3), "0"), (lambda s: Quantizador(Fraction(1), int(s)), "0"),
                 (lambda s: Quantizador(Fraction(1), int(s)), "17"), (lambda s: decodificar(q, s), "1111")]
    rejeitadas = 0
    for funcao, entrada in invalidas:
        try:
            funcao(entrada)
        except ValueError:
            rejeitadas += 1
    caso("Entradas inválidas são rejeitadas", rejeitadas == len(invalidas),
         f"{rejeitadas}/{len(invalidas)}: amostra 'abc', lista vazia, '; ;', {MAX_AMOSTRAS + 1} amostras,\n"
         f"         bits 'três', faixa 0, 0 e 17 bits, sequência com bits sobrando")

    print()
    print(f"Resultado: {sum(resultados)}/{len(resultados)} verificações OK")
    return all(resultados)


# ----------------------------------------------------------------------------
# Linha de comando
# ----------------------------------------------------------------------------

def main() -> None:
    for fluxo in (sys.stdout, sys.stderr):
        try:
            fluxo.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass

    ap = argparse.ArgumentParser(description="Quantização uniforme com nível no ponto médio e código binário")
    sub = ap.add_subparsers(dest="modo", metavar="MODO")

    p = sub.add_parser("experimentos", help="roda todos os experimentos (padrão)")
    p.add_argument("--pasta", default=str(PASTA / "graficos"), help="pasta das figuras")
    p.add_argument("--saida", default=str(PASTA / "saida_experimentos.txt"),
                   help="arquivo onde a saída também é gravada ('' para não gravar)")

    p = sub.add_parser("quantizar", help="quantiza outras amostras")
    p.add_argument("--amostras", required=True, help=f'tensões separadas por ";" (ex.: "{AMOSTRAS}")')
    p.add_argument("--bits", default=str(BITS), help=f"bits por amostra (padrão: {BITS})")
    p.add_argument("--faixa", default=FAIXA, help=f"A, para a faixa de -A a +A em volts (padrão: {FAIXA})")
    p.add_argument("--pasta", default=str(PASTA / "graficos"), help="pasta das figuras")

    sub.add_parser("validar", help="confere o exemplo da aula 14 e o quantizador")
    args = ap.parse_args()

    try:
        if args.modo == "validar":
            sys.exit(0 if modo_validar() else 1)
        if args.modo == "quantizar":
            q = Quantizador(ler_numero(args.faixa, "faixa"), ler_bits(args.bits))
            rodar(q, ler_amostras(args.amostras), Path(args.pasta), "quantizar_")
        else:
            modo_experimentos(Path(getattr(args, "pasta", PASTA / "graficos")),
                              getattr(args, "saida", str(PASTA / "saida_experimentos.txt")))
    except (ValueError, OSError) as e:
        print(f"Erro: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
