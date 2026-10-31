"""
Atividade 10 - Capacidade de Canais de Comunicação (Nyquist e Shannon)
Redes de Computadores - UNISINOS 2026/2 - Matheus Milanezi

Modelos implementados:
  - Nyquist (canal ideal, sem ruído):  C = 2B·log2(N)
  - Shannon (canal com ruído):         C = B·log2(1 + SNR)
      C = capacidade (bit/s), B = largura de banda (Hz),
      N = número de níveis de sinalização, SNR = razão sinal-ruído em escala LINEAR.
  - Conversão da SNR:  SNR = 10^(SNR_dB/10)   e   SNR_dB = 10·log10(SNR)
  - Ligação entre os dois (aula 12): o ruído limita os níveis distinguíveis a
      N_max = sqrt(1 + SNR), e 2B·log2(N_max) = B·log2(1 + SNR).

Uso:
  python capacidade.py                                     os 4 experimentos (tabelas + gráficos)
  python capacidade.py experimentos [--sem-graficos] [--pasta DIR] [--saida ARQ]
  python capacidade.py nyquist  --B 3k --N 8               capacidade de Nyquist
  python capacidade.py shannon  --B 3k --snr 1000          Shannon com SNR linear
  python capacidade.py shannon  --B 3k --snr-db 30         Shannon com SNR em dB
  python capacidade.py comparar --B 3k --snr-db 30 --N 32  Nyquist x Shannon (+ N_max)
  python capacidade.py validar                             confere com os exemplos da aula 12

  B aceita os sufixos k, M e G e a unidade Hz: 3k = 3kHz = 3000 = 3000Hz.
  Números decimais podem usar ponto ou vírgula (1.5k ou 1,5k); não use separador de milhar.
"""

import argparse
import math
import re
import sys
from contextlib import ExitStack, redirect_stdout
from pathlib import Path

PASTA = Path(__file__).resolve().parent

# Parâmetros dos experimentos (enunciado da Atividade 10)
EXP1_B = [1e3, 5e3, 10e3]                      # Hz
EXP1_N = [2, 4, 8, 16]                         # níveis de sinalização
EXP2_SNR = [1_000, 5_000, 10_000, 50_000]      # escala linear
EXP2_B = [k * 1e3 for k in range(1, 11)]       # 1 a 10 kHz, passo de 1 kHz
EXP3_B = 5e3
EXP3_SNR_DB = list(range(0, 41, 5))            # 0 a 40 dB, passo de 5 dB
EXP3_COMPARAR = [10, 20, 30, 40]
EXP4_B = 3e3
EXP4_SNR_DB = 30
EXP4_N = [2, 4, 8, 16, 32, 64]

# Cores dos gráficos: séries em ordem fixa (paleta validada para daltonismo) e tintas neutras
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]
MARCADORES = ["o", "s", "^", "D"]
COR = {
    "fundo": "#ffffff",
    "tinta": "#0b0b0b",       # títulos
    "tinta2": "#52514e",      # rótulos e textos
    "muda": "#898781",        # elementos de apoio
    "grade": "#e1e0d9",
    "eixo": "#c3c2b7",
    "critico": "#d03b3b",     # acima do limite de Shannon
}
LINHA = dict(linewidth=2, markersize=7, markeredgecolor=COR["fundo"], markeredgewidth=1.5)


# ----------------------------------------------------------------------------
# Núcleo: os dois modelos e a conversão da SNR
# ----------------------------------------------------------------------------

def nyquist(B: float, N: float) -> float:
    """Capacidade de um canal ideal (sem ruído), em bit/s."""
    return 2 * B * math.log2(N)


def shannon(B: float, snr: float) -> float:
    """Capacidade máxima de um canal com ruído, em bit/s (SNR em escala linear)."""
    return B * math.log2(1 + snr)


def db_para_linear(snr_db: float) -> float:
    return 10 ** (snr_db / 10)


def linear_para_db(snr: float) -> float:
    return 10 * math.log10(snr) if snr > 0 else -math.inf


def n_max(snr: float) -> float:
    """Número máximo de níveis que o receptor ainda distingue com essa SNR (aula 12)."""
    return math.sqrt(1 + snr)


# ----------------------------------------------------------------------------
# Leitura e validação dos parâmetros
# ----------------------------------------------------------------------------

SUFIXOS = {"k": 1e3, "K": 1e3, "M": 1e6, "G": 1e9}


def ler_numero(texto: str, nome: str) -> float:
    s = texto.strip()
    if re.fullmatch(r"[+-]?\d{1,3}(\.\d{3})+", s):
        raise ValueError(f"{nome} = {texto!r} é ambíguo: escreva sem separador de milhar "
                         f"(ex.: {s.replace('.', '')})")
    try:
        v = float(s.replace(",", "."))
    except ValueError:
        raise ValueError(f"{nome} inválido: {texto!r} não é um número") from None
    if not math.isfinite(v):
        raise ValueError(f"{nome} deve ser um número finito")
    return v


def ler_frequencia(texto: str) -> float:
    """'3k', '3kHz', '3000' ou '1.5M' -> valor em Hz (deve ser > 0)."""
    s = texto.strip()
    if s.lower().endswith("hz"):
        s = s[:-2].strip()
    mult = 1.0
    if s and s[-1] in SUFIXOS:
        mult = SUFIXOS[s[-1]]
        s = s[:-1]
    B = ler_numero(s, "B") * mult
    if B <= 0:
        raise ValueError(f"a largura de banda B deve ser maior que 0 Hz (recebido: {texto})")
    return B


def ler_niveis(texto: str) -> int:
    N = ler_numero(texto, "N")
    if not N.is_integer() or N < 2:
        raise ValueError(f"o número de níveis N deve ser um inteiro >= 2 (recebido: {texto})")
    return int(N)


def ler_snr(texto: str) -> float:
    snr = ler_numero(texto, "SNR")
    if snr < 0:
        raise ValueError(f"a SNR linear deve ser >= 0 (recebido: {texto}); "
                         "para informar em dB use --snr-db")
    return snr


def ler_snr_db(texto: str) -> float:
    try:
        return db_para_linear(ler_numero(texto, "SNR (dB)"))
    except OverflowError:
        raise ValueError(f"SNR = {texto} dB é grande demais para a escala linear") from None


# ----------------------------------------------------------------------------
# Exibição com unidades (padrão brasileiro: 29.901,68)
# ----------------------------------------------------------------------------

def br(x: float, casas: int = 2) -> str:
    return f"{x:,.{casas}f}".replace(",", "_").replace(".", ",").replace("_", ".")


def br_curto(x: float, casas: int = 3) -> str:
    """Como br(), mas sem zeros à direita: 3000 -> '3.000', 1.5 -> '1,5'."""
    s = br(x, casas)
    return s.rstrip("0").rstrip(",") if "," in s else s


def br_cient(x: float, casas: int = 3) -> str:
    mant, exp = f"{x:.{casas}e}".split("e")
    return f"{mant.replace('.', ',')} × 10^{int(exp)}"


def taxa(c: float) -> str:
    """Capacidade na unidade mais legível e também em bit/s."""
    for fator, unidade in ((1e9, "Gbit/s"), (1e6, "Mbit/s"), (1e3, "kbit/s")):
        if abs(c) >= fator:
            return f"{br(c / fator)} {unidade} ({br(c)} bit/s)"
    return f"{br(c)} bit/s"


def frequencia(B: float) -> str:
    for fator, unidade in ((1e9, "GHz"), (1e6, "MHz"), (1e3, "kHz")):
        if B >= fator:
            return f"{br_curto(B / fator)} {unidade} ({br_curto(B)} Hz)"
    return f"{br_curto(B)} Hz"


def snr_texto(snr: float) -> str:
    db = linear_para_db(snr)
    return f"{br_curto(snr)} (linear) = {'-∞' if db == -math.inf else br(db)} dB"


def linha(titulo: str) -> None:
    print("=" * 78)
    print(titulo)
    print("=" * 78)


def mostrar_caminho(caminho: Path) -> str:
    try:
        return str(caminho.relative_to(Path.cwd()))
    except ValueError:
        return str(caminho)


# ----------------------------------------------------------------------------
# Modo parâmetro: nyquist, shannon e comparar
# ----------------------------------------------------------------------------

def mostrar_snr(snr: float, snr_db: str | None) -> None:
    if snr_db is not None:
        print(f"  SNR = 10^({snr_db}/10) = {snr_texto(snr)}")
    else:
        print(f"  SNR = {snr_texto(snr)}")


def modo_nyquist(B: float, N: int) -> None:
    linha("Nyquist - canal ideal (sem ruído): C = 2B·log2(N)")
    m = math.log2(N)
    print(f"  B = {frequencia(B)}")
    print(f"  N = {N} níveis  ->  m = log2({N}) = {br_curto(m)} bits/símbolo")
    if not m.is_integer():
        print("      (N não é potência de 2: m fracionário, vale como limite teórico)")
    print(f"  taxa de sinalização = 2B = {br_curto(2 * B)} baud (símbolos/s)")
    print(f"  C = 2 × {br_curto(B)} × {br_curto(m)} = {taxa(nyquist(B, N))}")


def modo_shannon(B: float, snr: float, snr_db: str | None) -> None:
    linha("Shannon - canal com ruído: C = B·log2(1 + SNR)")
    efic = math.log2(1 + snr)
    print(f"  B = {frequencia(B)}")
    mostrar_snr(snr, snr_db)
    print(f"  log2(1 + SNR) = log2({br_curto(1 + snr)}) = {br(efic, 4)} bit/s/Hz"
          "  (eficiência espectral máxima)")
    print(f"  C = {br_curto(B)} × {br(efic, 4)} = {taxa(shannon(B, snr))}")
    nm = n_max(snr)
    print(f"  N_max = √(1 + SNR) = {br(nm)} níveis ({br(math.log2(nm), 3)} bits/símbolo)")


def modo_comparar(B: float, snr: float, snr_db: str | None, N: int) -> None:
    linha("Nyquist (canal ideal) x Shannon (canal com ruído)")
    cn, cs, nm = nyquist(B, N), shannon(B, snr), n_max(snr)
    print(f"  B = {frequencia(B)}")
    mostrar_snr(snr, snr_db)
    print(f"  N = {N} níveis ({br_curto(math.log2(N))} bits/símbolo)")
    print()
    print(f"  Nyquist  C = 2B·log2(N)      = {taxa(cn)}")
    print(f"  Shannon  C = B·log2(1 + SNR) = {taxa(cs)}")
    print(f"  N_max = √(1 + SNR)           = {br(nm)} níveis ({br(math.log2(nm), 3)} bits/símbolo)")
    print()
    if cs == 0:
        print("  Com SNR = 0 a capacidade de Shannon é 0: nenhuma taxa é alcançável.")
    elif cn > cs:
        print(f"  Resultado: N = {N} > N_max -> a taxa de Nyquist ULTRAPASSA o limite de Shannon")
        print(f"             em {taxa(cn - cs)} (+{br((cn / cs - 1) * 100)} %).")
        print("             Essa taxa não pode ser obtida com erro arbitrariamente baixo neste canal:")
        print(f"             o ruído não deixa o receptor distinguir {N} níveis.")
    else:
        print(f"  Resultado: N = {N} <= N_max -> a taxa de Nyquist fica dentro do limite de Shannon")
        print(f"             (usa {br(cn / cs * 100)} % da capacidade do canal).")


# ----------------------------------------------------------------------------
# Experimentos da atividade
# ----------------------------------------------------------------------------

def preparar_matplotlib():
    """Importa o matplotlib só quando os gráficos são pedidos e aplica o estilo."""
    import matplotlib
    matplotlib.use("Agg")                        # gera os PNGs sem abrir janelas
    import matplotlib.pyplot as plt
    from matplotlib import font_manager

    instaladas = {f.name for f in font_manager.fontManager.ttflist}
    fontes = [f for f in ("Segoe UI", "DejaVu Sans") if f in instaladas] or ["sans-serif"]
    plt.rcParams.update({
        "font.family": fontes,
        "font.size": 10,
        "figure.facecolor": COR["fundo"],
        "axes.facecolor": COR["fundo"],
        "axes.edgecolor": COR["eixo"],
        "axes.labelcolor": COR["tinta2"],
        "axes.titlecolor": COR["tinta"],
        "axes.titlesize": 12,
        "axes.titleweight": "bold",
        "axes.titlelocation": "left",
        "axes.titlepad": 12,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "axes.axisbelow": True,
        "grid.color": COR["grade"],
        "grid.linewidth": 0.8,
        "xtick.color": COR["eixo"],
        "ytick.color": COR["eixo"],
        "xtick.labelcolor": COR["tinta2"],
        "ytick.labelcolor": COR["tinta2"],
        "legend.frameon": False,
        "legend.fontsize": 9,
        "savefig.dpi": 200,
    })
    return plt


def formato_br(ax, eixo: str = "y") -> None:
    from matplotlib.ticker import FuncFormatter
    fmt = FuncFormatter(lambda v, _: br_curto(v))
    (ax.yaxis if eixo == "y" else ax.xaxis).set_major_formatter(fmt)


def rotulo(ax, texto: str, xy: tuple, dx: float = 8, dy: float = 0, **kw) -> None:
    """Rótulo direto (em tinta neutra) ao lado de um ponto; pode ficar fora da área do gráfico."""
    opcoes = dict(textcoords="offset points", va="center", color=COR["tinta2"],
                  fontsize=9, annotation_clip=False)
    opcoes.update(kw)
    ax.annotate(texto, xy=xy, xytext=(dx, dy), **opcoes)


def salvar(plt, fig, pasta: Path, nome: str) -> None:
    pasta.mkdir(parents=True, exist_ok=True)
    caminho = pasta / nome
    fig.savefig(caminho, bbox_inches="tight", pad_inches=0.2)
    plt.close(fig)
    print(f"  gráfico salvo em: {mostrar_caminho(caminho)}")


def experimento_1(plt, pasta: Path) -> None:
    linha("EXPERIMENTO 1 - Capacidade de Nyquist (canal ideal): C = 2B·log2(N)")
    C = {B: [nyquist(B, N) for N in EXP1_N] for B in EXP1_B}

    print("Capacidade C em kbit/s:\n")
    rot = 28
    print(f"  {'N (níveis)':<{rot}}" + "".join(f"{N:>10}" for N in EXP1_N))
    print(f"  {'m = log2 N (bits/símbolo)':<{rot}}"
          + "".join(f"{br_curto(math.log2(N)):>10}" for N in EXP1_N))
    print("  " + "-" * (rot + 10 * len(EXP1_N)))
    for B in EXP1_B:
        print(f"  {'B = ' + br_curto(B / 1e3) + ' kHz':<{rot}}"
              + "".join(f"{br(c / 1e3):>10}" for c in C[B]))

    print("\nObservações calculadas:")
    b0, b1 = EXP1_B[0], EXP1_B[-1]
    razoes = sorted({round(c1 / c0, 9) for c0, c1 in zip(C[b0], C[b1])})
    print(f"  - B × {br_curto(b1 / b0)} ({br_curto(b0 / 1e3)} -> {br_curto(b1 / 1e3)} kHz): "
          f"C × {' / '.join(br(r) for r in razoes)} para todo N -> C é proporcional a B")
    for B in EXP1_B:
        difs = sorted({round(C[B][i + 1] - C[B][i], 6) for i in range(len(EXP1_N) - 1)})
        print(f"  - B = {br_curto(B / 1e3)} kHz: cada vez que N dobra (+1 bit/símbolo), C soma "
              f"{' / '.join(br(d / 1e3) for d in difs)} kbit/s (= 2B)")
    n0, n1 = EXP1_N[0], EXP1_N[-1]
    print(f"  - N × {n1 // n0} ({n0} -> {n1} níveis) multiplica C por apenas "
          f"{br(C[b0][-1] / C[b0][0])} (= log2 {n1} / log2 {n0})")

    if plt:
        fig, ax = plt.subplots(figsize=(7.5, 4.5))
        for k, B in enumerate(EXP1_B):
            y = [c / 1e3 for c in C[B]]
            nome = f"B = {br_curto(B / 1e3)} kHz"
            ax.plot(EXP1_N, y, color=SERIES[k], marker=MARCADORES[k], label=nome, **LINHA)
            rotulo(ax, f"{nome}: {br_curto(y[-1])} kbit/s", (EXP1_N[-1], y[-1]))
        ax.set_xticks(EXP1_N, [f"{N}\n({br_curto(math.log2(N))} bit{'s' if N > 2 else ''})"
                               for N in EXP1_N])
        ax.set_xlim(1, 17)
        ax.set_ylim(0, max(C[b1]) / 1e3 * 1.1)
        formato_br(ax)
        ax.set_title("Experimento 1 – Capacidade de Nyquist: C = 2B·log2(N)")
        ax.set_xlabel("N – níveis de sinalização (bits por símbolo)")
        ax.set_ylabel("Capacidade C (kbit/s)")
        ax.legend(loc="upper left")
        salvar(plt, fig, pasta, "exp1_nyquist.png")
    print()


def experimento_2(plt, pasta: Path) -> None:
    linha("EXPERIMENTO 2 - Capacidade de Shannon: C = B·log2(1 + SNR)")
    C = {snr: [shannon(B, snr) for B in EXP2_B] for snr in EXP2_SNR}

    print("Capacidade C em kbit/s:\n")
    rot, col = 28, 12
    print(f"  {'SNR (linear)':<{rot}}" + "".join(f"{br_curto(s):>{col}}" for s in EXP2_SNR))
    print(f"  {'SNR (dB)':<{rot}}" + "".join(f"{br(linear_para_db(s)):>{col}}" for s in EXP2_SNR))
    print(f"  {'log2(1 + SNR) (bit/s/Hz)':<{rot}}"
          + "".join(f"{br(math.log2(1 + s), 3):>{col}}" for s in EXP2_SNR))
    print("  " + "-" * (rot + col * len(EXP2_SNR)))
    for i, B in enumerate(EXP2_B):
        print(f"  {'B = ' + br_curto(B / 1e3) + ' kHz':<{rot}}"
              + "".join(f"{br(C[s][i] / 1e3):>{col}}" for s in EXP2_SNR))

    todos = [(C[s][i], B, s) for s in EXP2_SNR for i, B in enumerate(EXP2_B)]
    maior, menor = max(todos), min(todos)
    print()
    print(f"Maior capacidade: {taxa(maior[0])}  (B = {br_curto(maior[1] / 1e3)} kHz, "
          f"SNR = {br_curto(maior[2])})")
    print(f"Menor capacidade: {taxa(menor[0])}  (B = {br_curto(menor[1] / 1e3)} kHz, "
          f"SNR = {br_curto(menor[2])})")
    print(f"Maior / menor = {br(maior[0] / menor[0])}")

    print("\nObservações calculadas:")
    razoes = sorted({round(C[s][-1] / C[s][0], 9) for s in EXP2_SNR})
    print(f"  - Para cada SNR, C/B é constante: C(10 kHz) / C(1 kHz) = "
          f"{' / '.join(br(r) for r in razoes)} -> C cresce linearmente com B")
    for s0, s1 in [(1_000, 5_000), (10_000, 50_000), (1_000, 50_000)]:
        e0, e1 = math.log2(1 + s0), math.log2(1 + s1)
        print(f"  - SNR × {br_curto(s1 / s0)} ({br_curto(s0)} -> {br_curto(s1)}): C × {br(e1 / e0, 4)}"
              f" para todo B; a eficiência sobe só {br(e1 - e0, 4)} bit/s/Hz")
    e0 = math.log2(1 + EXP2_SNR[0])
    snr5 = (1 + EXP2_SNR[0]) ** 5 - 1
    print(f"  - Para C × 5 a partir de SNR = {br_curto(EXP2_SNR[0])} seria preciso "
          f"(1 + SNR)^5 - 1 = {br_cient(snr5)} ({br(linear_para_db(snr5), 1)} dB)")

    if plt:
        fig, ax = plt.subplots(figsize=(7.5, 4.5))
        x = [B / 1e3 for B in EXP2_B]
        for k, s in enumerate(EXP2_SNR):
            y = [c / 1e3 for c in C[s]]
            ax.plot(x, y, color=SERIES[k], marker=MARCADORES[k], markersize=6,
                    label=f"SNR = {br_curto(s)} ({br(linear_para_db(s), 1)} dB)",
                    **{c: v for c, v in LINHA.items() if c != "markersize"})
            rotulo(ax, f"SNR = {br_curto(s)}", (x[-1], y[-1]))
        for valor, B, _s, texto, dx, dy, ha in [
                (*maior, f"maior: {br(maior[0] / 1e3)} kbit/s", -12, 10, "right"),
                (*menor, f"menor: {br(menor[0] / 1e3)} kbit/s", 10, -12, "left")]:
            ax.plot(B / 1e3, valor / 1e3, marker="o", markersize=12, markerfacecolor="none",
                    markeredgecolor=COR["tinta"], markeredgewidth=1.2, linestyle="none", zorder=5)
            rotulo(ax, texto, (B / 1e3, valor / 1e3), dx, dy, ha=ha, color=COR["tinta"])
        ax.set_xticks(x)
        ax.set_xlim(0.5, 10.5)
        ax.set_ylim(0, maior[0] / 1e3 * 1.1)
        formato_br(ax)
        ax.set_title("Experimento 2 – Capacidade de Shannon: C = B·log2(1 + SNR)")
        ax.set_xlabel("Largura de banda B (kHz)")
        ax.set_ylabel("Capacidade C (kbit/s)")
        ax.legend(loc="upper left")
        salvar(plt, fig, pasta, "exp2_shannon.png")
    print()


def experimento_3(plt, pasta: Path) -> None:
    linha(f"EXPERIMENTO 3 - Influência do ruído: B = {br_curto(EXP3_B / 1e3)} kHz, "
          f"SNR de {EXP3_SNR_DB[0]} a {EXP3_SNR_DB[-1]} dB")
    snrs = [db_para_linear(db) for db in EXP3_SNR_DB]
    C = [shannon(EXP3_B, s) for s in snrs]
    passo = EXP3_SNR_DB[1] - EXP3_SNR_DB[0]

    print("SNR = 10^(SNR_dB/10)  e  C = B·log2(1 + SNR):\n")
    print(f"  {'SNR (dB)':>9}{'SNR (linear)':>15}{'log2(1+SNR)':>14}{'C (kbit/s)':>13}"
          f"{'ΔC (+' + str(passo) + ' dB)':>15}")
    print("  " + "-" * 66)
    for i, db in enumerate(EXP3_SNR_DB):
        dc = "-" if i == 0 else "+" + br((C[i] - C[i - 1]) / 1e3)
        print(f"  {db:>9}{br(snrs[i]):>15}{br(math.log2(1 + snrs[i]), 3):>14}"
              f"{br(C[i] / 1e3):>13}{dc:>15}")

    print(f"\nComparação em {', '.join(str(d) for d in EXP3_COMPARAR[:-1])} e "
          f"{EXP3_COMPARAR[-1]} dB:\n")
    print(f"  {'SNR (dB)':>9}{'SNR (linear)':>15}{'C (kbit/s)':>13}{'ΔC (+10 dB)':>14}"
          f"{'C / C(-10 dB)':>16}{'C/B (bit/s/Hz)':>17}")
    print("  " + "-" * 84)
    anterior = None
    for db in EXP3_COMPARAR:
        c = C[EXP3_SNR_DB.index(db)]
        dc = "-" if anterior is None else "+" + br((c - anterior) / 1e3)
        rz = "-" if anterior is None else br(c / anterior, 3)
        print(f"  {db:>9}{br_curto(db_para_linear(db)):>15}{br(c / 1e3):>13}{dc:>14}{rz:>16}"
              f"{br(c / EXP3_B, 3):>17}")
        anterior = c
    c_ini, c_fim = C[EXP3_SNR_DB.index(EXP3_COMPARAR[0])], C[EXP3_SNR_DB.index(EXP3_COMPARAR[-1])]
    print("\nObservações calculadas:")
    print(f"  - +10 dB = SNR × 10; em SNR alta isso soma ≈ B·log2(10) = "
          f"{br(EXP3_B * math.log2(10) / 1e3)} kbit/s (soma, não multiplica)")
    print(f"  - De {EXP3_COMPARAR[0]} para {EXP3_COMPARAR[-1]} dB a SNR é multiplicada por "
          f"{br_curto(db_para_linear(EXP3_COMPARAR[-1] - EXP3_COMPARAR[0]))}, "
          f"mas C só por {br(c_fim / c_ini)}")
    print(f"  - Em 0 dB (sinal = ruído) C = B = {br_curto(C[0])} bit/s")

    if plt:
        fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 4.4))
        y = [c / 1e3 for c in C]
        a1.plot(EXP3_SNR_DB, y, color=SERIES[0], marker="o", **LINHA)
        for db in EXP3_COMPARAR:
            i = EXP3_SNR_DB.index(db)
            rotulo(a1, f"{br(y[i])}", (db, y[i]), -6, 9, ha="right")
        a1.set_xticks(EXP3_SNR_DB)
        a1.set_ylim(0, max(y) * 1.12)
        formato_br(a1)
        a1.set_title("(a) C × SNR em dB (pedido no enunciado)")
        a1.set_xlabel("SNR (dB)")
        a1.set_ylabel("Capacidade C (kbit/s)")

        smax = snrs[-1]
        xs = [smax * k / 400 for k in range(401)]
        a2.plot(xs, [shannon(EXP3_B, s) / 1e3 for s in xs], color=SERIES[0], linewidth=2)
        a2.plot(snrs, y, color=SERIES[0], marker="o", linestyle="none",
                **{c: v for c, v in LINHA.items() if c != "linewidth"})
        for db in (30, 35, 40):
            i = EXP3_SNR_DB.index(db)
            rotulo(a2, f"{db} dB", (snrs[i], y[i]), 0, -14, ha="center")
        i30, i40 = EXP3_SNR_DB.index(30), EXP3_SNR_DB.index(40)
        a2.text(0.5, 0.18,
                f"SNR × 10 (de {br_curto(snrs[i30])} para {br_curto(snrs[i40])}):\n"
                f"C só +{br(y[i40] - y[i30])} kbit/s",
                transform=a2.transAxes, ha="center", color=COR["tinta2"], fontsize=9)
        a2.set_xlim(-smax * 0.03, smax * 1.05)
        a2.set_ylim(0, max(y) * 1.12)
        formato_br(a2)
        formato_br(a2, "x")
        a2.set_title("(b) a mesma curva com a SNR em escala linear")
        a2.set_xlabel("SNR (linear)")
        fig.suptitle(f"Experimento 3 – Influência do ruído (B = {br_curto(EXP3_B / 1e3)} kHz): "
                     "C = B·log2(1 + SNR)", x=0.065, ha="left", fontsize=12, fontweight="bold",
                     color=COR["tinta"])
        fig.tight_layout()
        salvar(plt, fig, pasta, "exp3_ruido.png")
    print()


def experimento_4(plt, pasta: Path) -> None:
    snr = db_para_linear(EXP4_SNR_DB)
    lim, nm = shannon(EXP4_B, snr), n_max(snr)
    linha(f"EXPERIMENTO 4 - Nyquist x Shannon: B = {br_curto(EXP4_B / 1e3)} kHz, "
          f"SNR = {EXP4_SNR_DB} dB ({br_curto(snr)})")
    print(f"Limite de Shannon: C = {br_curto(EXP4_B)} × log2(1 + {br_curto(snr)}) = {taxa(lim)}")
    print(f"N_max = √(1 + SNR) = {br(nm)} níveis = {br(math.log2(nm), 3)} bits/símbolo\n")

    print(f"  {'N':>4}{'m (bits)':>10}{'Nyquist (kbit/s)':>18}{'Shannon (kbit/s)':>18}"
          f"{'Nyquist/Shannon':>17}   Situação")
    print("  " + "-" * 92)
    acima = []
    for N in EXP4_N:
        c = nyquist(EXP4_B, N)
        if c > lim:
            acima.append(N)
            sit = f"ULTRAPASSA o limite (+{br(c - lim)} bit/s)"
        else:
            sit = "dentro do limite"
        print(f"  {N:>4}{br_curto(math.log2(N)):>10}{br(c / 1e3):>18}{br(lim / 1e3):>18}"
              f"{br(c / lim * 100, 1) + ' %':>17}   {sit}")
    print()
    print(f"Configurações em que Nyquist ultrapassa Shannon: "
          f"N = {', '.join(str(n) for n in acima) if acima else 'nenhuma'}")
    slide = EXP4_B * round(math.log10(1 + snr), 1) / round(math.log10(2), 1)
    print(f"Obs.: o slide 24 da aula 12 arredonda log10(1.001) ≈ 3 e log10(2) ≈ 0,3 e obtém "
          f"{br_curto(slide)} bit/s.")
    print(f"      Com esse valor N = 32 daria exatamente o limite; pelo valor exato "
          f"({br(lim)} bit/s),")
    print(f"      e porque N_max = {br(nm)} < 32, N = 32 já ultrapassa.")

    if plt:
        fig, ax = plt.subplots(figsize=(7.5, 4.6))
        from matplotlib.ticker import NullLocator
        y = [nyquist(EXP4_B, N) / 1e3 for N in EXP4_N]
        topo = max(y) * 1.12
        ax.axhspan(lim / 1e3, topo, color=COR["critico"], alpha=0.06, linewidth=0)
        ax.text(EXP4_N[0], topo * 0.97, "  acima do limite de Shannon: inalcançável sem erros",
                va="top", color=COR["critico"], fontsize=9)
        ax.axhline(lim / 1e3, color=COR["tinta"], linestyle=(0, (5, 3)), linewidth=1.4,
                   label=f"Limite de Shannon ({br(lim / 1e3)} kbit/s)")
        ax.plot(EXP4_N, y, color=SERIES[0], marker="o", label="Nyquist: C = 2B·log2(N)", **LINHA)
        # a reta de Nyquist cruza o limite exatamente em N = N_max
        ax.plot(nm, lim / 1e3, marker="o", markersize=12, markerfacecolor="none",
                markeredgecolor=COR["tinta"], markeredgewidth=1.2, linestyle="none", zorder=5)
        ax.annotate(f"cruzamento em\nN_max = √(1 + SNR) = {br(nm)}", xy=(nm, lim / 1e3),
                    xytext=(34, lim / 1e3 - 6), ha="left", va="top", color=COR["tinta"],
                    fontsize=9, arrowprops=dict(arrowstyle="-", color=COR["muda"], linewidth=1))
        xa = [N for N in EXP4_N if N in acima]
        ya = [nyquist(EXP4_B, N) / 1e3 for N in xa]
        ax.plot(xa, ya, marker="^", markersize=10, color=COR["critico"],
                markeredgecolor=COR["fundo"], markeredgewidth=1.5, linestyle="none", zorder=4,
                label="Nyquist acima do limite")
        for N, v in zip(xa, ya):
            rotulo(ax, f"N = {N}: {br(v)} kbit/s (+{br_curto(v * 1e3 - lim, 0)} bit/s)",
                   (N, v), -12, 12, ha="right", color=COR["tinta"])
        ax.set_xscale("log", base=2)
        ax.set_xticks(EXP4_N, [f"{N}\n({br_curto(math.log2(N))} bit{'s' if N > 2 else ''})"
                               for N in EXP4_N])
        ax.xaxis.set_minor_locator(NullLocator())
        ax.set_xlim(EXP4_N[0] / 1.25, EXP4_N[-1] * 1.25)
        ax.set_ylim(0, topo)
        formato_br(ax)
        ax.set_title(f"Experimento 4 – Nyquist × Shannon (B = {br_curto(EXP4_B / 1e3)} kHz, "
                     f"SNR = {EXP4_SNR_DB} dB)")
        ax.set_xlabel("N – níveis de sinalização (bits por símbolo), escala log2")
        ax.set_ylabel("Capacidade C (kbit/s)")
        ax.legend(loc="lower right")
        salvar(plt, fig, pasta, "exp4_nyquist_x_shannon.png")
    print()


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


def modo_experimentos(sem_graficos: bool, pasta: Path, saida: str) -> None:
    plt = None if sem_graficos else preparar_matplotlib()
    with ExitStack() as pilha:
        if saida:
            Path(saida).parent.mkdir(parents=True, exist_ok=True)
            arq = pilha.enter_context(open(saida, "w", encoding="utf-8"))
            pilha.enter_context(redirect_stdout(Tee(sys.stdout, arq)))
        experimento_1(plt, pasta)
        experimento_2(plt, pasta)
        experimento_3(plt, pasta)
        experimento_4(plt, pasta)
    if saida:
        print(f"Saída gravada em: {mostrar_caminho(Path(saida).resolve())}")


# ----------------------------------------------------------------------------
# Validação: exemplos da aula 12 e conferências internas
# ----------------------------------------------------------------------------

def modo_validar() -> bool:
    linha("VALIDAÇÃO - exemplos da aula 12 e conferências internas")
    resultados = []

    def caso(descricao: str, ok: bool, detalhe: str) -> None:
        resultados.append(ok)
        print(f"  [{'OK' if ok else 'FALHOU'}] {descricao}")
        print(f"         {detalhe}")

    def perto(a: float, b: float) -> bool:
        return math.isclose(a, b, rel_tol=1e-12, abs_tol=1e-9)

    c = nyquist(20, 4)
    caso("Aula 12, slide 14: Nyquist com B = 20 Hz e N = 4", perto(c, 80),
         f"obtido {taxa(c)}, esperado 80 bit/s")

    s = db_para_linear(30)
    caso("Aula 12, slide 23: 30 dB em escala linear", perto(s, 1000),
         f"obtido 10^(30/10) = {br_curto(s)}, esperado 1.000")

    c = shannon(3000, 1000)
    pelo_log10 = 3000 * math.log10(1001) / math.log10(2)
    caso("Aula 12, slide 24: Shannon com B = 3.000 Hz e SNR = 1.000 (valor exato)",
         perto(c, pelo_log10),
         f"obtido {taxa(c)}; pelo caminho do slide, 3.000 × log10(1.001)/log10(2) = "
         f"{br(pelo_log10)} bit/s")
    slide = 3000 * round(math.log10(1001), 1) / round(math.log10(2), 1)
    caso("Aula 12, slide 24: valor do slide com os arredondamentos log10(1.001) ≈ 3, log10(2) ≈ 0,3",
         perto(slide, 30_000),
         f"3.000 × 3/0,3 = {br_curto(slide)} bit/s; diferença para o exato = "
         f"{br(slide - c)} bit/s ({br((slide / c - 1) * 100)} %)")

    dbs = [0, 3, 10, 30, 47]
    ok = sum(perto(linear_para_db(db_para_linear(d)), d) for d in dbs)
    caso("Conversão dB -> linear -> dB volta ao valor original", ok == len(dbs),
         f"{ok}/{len(dbs)} valores ({', '.join(str(d) for d in dbs)} dB)")

    casos = [(B, s) for B in EXP1_B for s in [1, 1000, 5000, 50000]]
    ok = sum(perto(nyquist(B, n_max(s)), shannon(B, s)) for B, s in casos)
    caso("Identidade da aula: 2B·log2(√(1 + SNR)) = B·log2(1 + SNR)", ok == len(casos),
         f"{ok}/{len(casos)} combinações de B e SNR")

    casos = [(B, m) for B in EXP1_B for m in range(1, 7)]
    ok = sum(perto(nyquist(B, 2 ** m), 2 * B * m) for B, m in casos)
    caso("Nyquist com N = 2^m é exatamente 2B·m", ok == len(casos),
         f"{ok}/{len(casos)} combinações (m = 1 a 6)")

    caso("Shannon nos extremos: SNR = 0 -> C = 0 e SNR = 0 dB -> C = B",
         shannon(5000, 0) == 0 and perto(shannon(5000, db_para_linear(0)), 5000),
         f"C(SNR = 0) = {br(shannon(5000, 0))} bit/s; "
         f"C(0 dB) = {br(shannon(5000, db_para_linear(0)))} bit/s com B = 5.000 Hz")

    invalidas = [(ler_niveis, "1"), (ler_niveis, "2.5"), (ler_frequencia, "-5"),
                 (ler_frequencia, "0"), (ler_snr, "-3"), (ler_snr, "1.000"), (ler_snr, "abc")]
    rejeitadas = 0
    for funcao, entrada in invalidas:
        try:
            funcao(entrada)
        except ValueError:
            rejeitadas += 1
    caso("Entradas inválidas são rejeitadas", rejeitadas == len(invalidas),
         f"{rejeitadas}/{len(invalidas)}: N = 1, N = 2.5, B = -5, B = 0, SNR = -3, "
         "SNR = '1.000' (ambíguo), SNR = 'abc'")

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

    ap = argparse.ArgumentParser(description="Capacidade de canais: Nyquist e Shannon")
    sub = ap.add_subparsers(dest="modo", metavar="MODO")

    p = sub.add_parser("experimentos", help="roda os 4 experimentos da atividade (padrão)")
    p.add_argument("--sem-graficos", action="store_true", help="só as tabelas, sem gerar PNGs")
    p.add_argument("--pasta", default=str(PASTA / "graficos"),
                   help="pasta dos gráficos (padrão: graficos/ ao lado do programa)")
    p.add_argument("--saida", default=str(PASTA / "saida_experimentos.txt"),
                   help="arquivo onde a saída também é gravada ('' para não gravar)")

    p = sub.add_parser("nyquist", help="C = 2B·log2(N)")
    p.add_argument("--B", required=True, help="largura de banda (Hz; aceita k/M/G: 3k)")
    p.add_argument("--N", required=True, help="número de níveis de sinalização (inteiro >= 2)")

    for nome, ajuda in (("shannon", "C = B·log2(1 + SNR)"),
                        ("comparar", "Nyquist x Shannon com os mesmos B e SNR")):
        p = sub.add_parser(nome, help=ajuda)
        p.add_argument("--B", required=True, help="largura de banda (Hz; aceita k/M/G: 3k)")
        g = p.add_mutually_exclusive_group(required=True)
        g.add_argument("--snr", help="SNR em escala linear (ex.: 1000)")
        g.add_argument("--snr-db", help="SNR em dB (ex.: 30)")
        if nome == "comparar":
            p.add_argument("--N", required=True, help="número de níveis de sinalização")

    sub.add_parser("validar", help="confere o programa com os exemplos da aula 12")
    args = ap.parse_args()

    try:
        if args.modo == "nyquist":
            modo_nyquist(ler_frequencia(args.B), ler_niveis(args.N))
        elif args.modo in ("shannon", "comparar"):
            B = ler_frequencia(args.B)
            snr = ler_snr(args.snr) if args.snr is not None else ler_snr_db(args.snr_db)
            if args.modo == "shannon":
                modo_shannon(B, snr, args.snr_db)
            else:
                modo_comparar(B, snr, args.snr_db, ler_niveis(args.N))
        elif args.modo == "validar":
            sys.exit(0 if modo_validar() else 1)
        else:
            modo_experimentos(getattr(args, "sem_graficos", False),
                              Path(getattr(args, "pasta", PASTA / "graficos")),
                              getattr(args, "saida", str(PASTA / "saida_experimentos.txt")))
    except (ValueError, OSError) as e:
        print(f"Erro: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
