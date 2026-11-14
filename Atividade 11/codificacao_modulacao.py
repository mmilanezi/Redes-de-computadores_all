"""
Atividade 11 - Codificação de Banda Base e Modulação Digital
Redes de Computadores - UNISINOS 2026/2 - Matheus Milanezi

Códigos de linha (banda base): NRZ unipolar, NRZ polar e Manchester.
Modulações de uma portadora senoidal e(t) = A·sen(2π·f·t + θ): ASK, FSK e BPSK.
Todos os sinais são formas de onda amostradas a FS. O ruído é AWGN, e o receptor decide
cada bit por correlação com a forma de onda esperada naquele intervalo de bit.

Convenções (aula 13):
  NRZ unipolar  0 -> 0 V                          1 -> +V
  NRZ polar     0 -> -V                           1 -> +V
  Manchester    0 -> descida no meio do bit       1 -> subida no meio do bit   (slide 14, IEEE 802.3)
  ASK           0 -> amplitude 0                  1 -> amplitude A             (slide 20)
  FSK           0 -> f0 = fc                      1 -> f1 = 2·fc               (slide 20)
  BPSK          0 -> fase 180° (-A)               1 -> fase 0° (+A)            (slides 23 e 26)

Uso:
  python codificacao_modulacao.py                                   todos os experimentos
  python codificacao_modulacao.py experimentos [--rapido] [--pasta DIR] [--saida ARQ]
  python codificacao_modulacao.py codificar [--bits 1011... | --texto "Re"]
  python codificacao_modulacao.py modular   [--bits 1011... | --texto "Re"]
  python codificacao_modulacao.py ruido --ebn0 6 [--bits ... | --texto ...] [--semente N]
  python codificacao_modulacao.py validar
"""

import argparse
import math
import sys
from contextlib import ExitStack, redirect_stdout
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import numpy as np

PASTA = Path(__file__).resolve().parent

# Parâmetros dos sinais
RB = 1_000              # taxa de bits (bit/s)
TB = 1 / RB             # duração de um bit (s)
FC = 2_000              # frequência da portadora (Hz)
F0, F1 = FC, 2 * FC     # FSK: frequência do bit 0 e do bit 1 (slide 20)
A = 1.0                 # amplitude da portadora (V)
V = 1.0                 # nível dos códigos de linha (V)
FS = 100_000            # frequência de amostragem (Hz)
N = round(FS * TB)      # amostras por bit (100)

# Sequência padrão: a dos slides 13 e 14 da aula 13 (14 bits), completada até 16 bits
SEQUENCIA = "1011000001101001"
SLIDE_BITS = "10110000011010"
SLIDE_POLAR = "+-++-----++-+-"       # níveis do NRZ polar lidos no slide 13
SLIDE_MANCHESTER = "SDSSDDDDDSSDSD"  # setas do slide 14: S = subida, D = descida no meio do bit

EBN0_RUIDO = [10, 0]                 # dB, figuras com os 16 bits e ruído
EBN0_BER = list(range(0, 13))        # dB, curvas de BER
MAX_BITS_FIGURA = 64

# Cores: séries em ordem fixa (paleta validada para daltonismo) e tintas neutras
CORES = ["#2a78d6", "#eb6834", "#1baf7a"]
MARCADORES = ["o", "s", "^"]
TINTA, TINTA2, MUDA, GRADE, EIXO = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"
CRITICO = "#d03b3b"


# ----------------------------------------------------------------------------
# Transmissores
# ----------------------------------------------------------------------------
# Tempo dentro de um bit. Como fc e f1 têm um número inteiro de ciclos por bit (2 e 4),
# a portadora é igual em todo intervalo de bit e a fase não "pula" na troca de bit.
T_BIT = np.arange(N) / FS
PORTADORA = np.sin(2 * np.pi * FC * T_BIT)
ONDA_F0 = np.sin(2 * np.pi * F0 * T_BIT)
ONDA_F1 = np.sin(2 * np.pi * F1 * T_BIT)


def nrz_unipolar(bits: np.ndarray) -> np.ndarray:
    return np.repeat(np.asarray(bits, float) * V, N)


def nrz_polar(bits: np.ndarray) -> np.ndarray:
    return np.repeat((2 * np.asarray(bits, float) - 1) * V, N)


def manchester(bits: np.ndarray) -> np.ndarray:
    """Bit 1: -V na 1ª metade e +V na 2ª (subida). Bit 0: +V e depois -V (descida)."""
    s = (2 * np.asarray(bits, float) - 1) * V
    return np.repeat(np.column_stack([-s, s]), N // 2, axis=1).ravel()


def ask(bits: np.ndarray) -> np.ndarray:
    return (A * np.asarray(bits, float)[:, None] * PORTADORA).ravel()


def fsk(bits: np.ndarray) -> np.ndarray:
    return (A * np.where(np.asarray(bits)[:, None] == 1, ONDA_F1, ONDA_F0)).ravel()


def bpsk(bits: np.ndarray) -> np.ndarray:
    """+A·sen (fase 0°) para o bit 1 e -A·sen (fase 180°) para o bit 0."""
    return (A * (2 * np.asarray(bits, float) - 1)[:, None] * PORTADORA).ravel()


# ----------------------------------------------------------------------------
# Receptores: uma estatística por bit, normalizada para os valores ideais 0/1 ou -1/+1
# ----------------------------------------------------------------------------

def projetar(r: np.ndarray, onda: np.ndarray) -> np.ndarray:
    """Correlação de cada bit (linha de r) com a onda, em unidades de A."""
    return r @ onda / (onda @ onda) / A


def medir_nrz(r: np.ndarray) -> np.ndarray:
    return r.mean(axis=1) / V                                   # média do nível no bit


def medir_manchester(r: np.ndarray) -> np.ndarray:
    return (r[:, N // 2:].mean(axis=1) - r[:, :N // 2].mean(axis=1)) / (2 * V)   # 2ª metade - 1ª


def medir_ask(r: np.ndarray) -> np.ndarray:
    return projetar(r, PORTADORA)


def medir_fsk(r: np.ndarray) -> np.ndarray:
    return projetar(r, ONDA_F1) - projetar(r, ONDA_F0)          # qual frequência "cabe" melhor


@dataclass(frozen=True)
class Tecnica:
    nome: str
    bit0: str
    bit1: str
    gerar: Callable[[np.ndarray], np.ndarray]      # bits -> amostras
    medir: Callable[[np.ndarray], np.ndarray]      # amostras (bits × N) -> estatística por bit
    limiar: float                                  # estatística > limiar -> bit 1
    antipodal: bool                                # bit 0 = -(bit 1): BER Q(√(2·Eb/N0)); senão Q(√(Eb/N0))


CODIGOS = [
    Tecnica("NRZ unipolar", "0 V", "+V", nrz_unipolar, medir_nrz, 0.5, False),
    Tecnica("NRZ polar", "-V", "+V", nrz_polar, medir_nrz, 0.0, True),
    Tecnica("Manchester", "↓ no meio do bit", "↑ no meio do bit", manchester, medir_manchester, 0.0, True),
]
MODULACOES = [
    Tecnica("ASK", "amplitude 0", "amplitude A", ask, medir_ask, 0.5, False),
    Tecnica("FSK", f"f0 = {F0 / 1e3:g} kHz", f"f1 = {F1 / 1e3:g} kHz", fsk, medir_fsk, 0.0, False),
    Tecnica("BPSK", "fase 180°", "fase 0°", bpsk, medir_ask, 0.0, True),
]
TECNICAS = CODIGOS + MODULACOES


def demodular(tec: Tecnica, sinal: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    estatistica = tec.medir(sinal.reshape(-1, N))
    return (estatistica > tec.limiar).astype(np.int8), estatistica


# ----------------------------------------------------------------------------
# Canal e teoria
# ----------------------------------------------------------------------------

def energia_bit(tec: Tecnica) -> float:
    """Energia média por bit (V²·s), com bits 0 e 1 igualmente prováveis."""
    s = tec.gerar(np.array([0, 1])).reshape(2, N)
    return float((s ** 2).sum(axis=1).mean() / FS)


def awgn(sinal: np.ndarray, ebn0_db: float, eb: float, rng) -> tuple[np.ndarray, float]:
    """Soma ruído branco gaussiano. Amostrado a FS, o ruído de densidade N0/2 tem variância N0·FS/2."""
    n0 = eb / 10 ** (ebn0_db / 10)
    sigma = math.sqrt(n0 * FS / 2)
    return sinal + rng.normal(0, sigma, len(sinal)), sigma


def q(x: float) -> float:
    """Probabilidade de uma gaussiana padrão passar de x."""
    return 0.5 * math.erfc(x / math.sqrt(2))


def ber_teorica(antipodal: bool, ebn0_db: float) -> float:
    g = 10 ** (ebn0_db / 10)
    return q(math.sqrt(2 * g)) if antipodal else q(math.sqrt(g))


def ebn0_necessario(antipodal: bool, ber_alvo: float = 1e-5) -> float:
    baixo, alto = -10.0, 30.0
    for _ in range(60):
        meio = (baixo + alto) / 2
        if ber_teorica(antipodal, meio) > ber_alvo:
            baixo = meio
        else:
            alto = meio
    return (baixo + alto) / 2


# ----------------------------------------------------------------------------
# Análise dos sinais
# ----------------------------------------------------------------------------

def transicoes(sinal: np.ndarray) -> np.ndarray:
    """Índices das amostras onde o nível muda."""
    return np.flatnonzero(np.diff(sinal)) + 1


def trecho_sem_transicao(sinal: np.ndarray) -> tuple[float, float]:
    """Início e fim (em bits) do maior trecho em que o nível não muda."""
    marcos = np.r_[0, transicoes(sinal), len(sinal)]
    k = int(np.argmax(np.diff(marcos)))
    return marcos[k] / N, marcos[k + 1] / N


def densidade_espectral(sinal: np.ndarray, tamanho: int = 8192) -> tuple[np.ndarray, np.ndarray]:
    """Periodograma médio (Welch, janela de Hann, 50 % de sobreposição), unilateral, em V²/Hz."""
    janela = np.hanning(tamanho)
    trechos = [sinal[i:i + tamanho] * janela for i in range(0, len(sinal) - tamanho + 1, tamanho // 2)]
    psd = (np.abs(np.fft.rfft(trechos, axis=1)) ** 2).mean(axis=0) / (FS * (janela ** 2).sum())
    psd[1:-1] *= 2
    return np.fft.rfftfreq(tamanho, 1 / FS), psd


# Banda do lobo principal de cada técnica (teoria), conferida no espectro medido
BANDAS = {
    "NRZ unipolar": (0, RB), "NRZ polar": (0, RB), "Manchester": (0, 2 * RB),
    "ASK": (FC - RB, FC + RB), "FSK": (F0 - RB, F1 + RB), "BPSK": (FC - RB, FC + RB),
}


# ----------------------------------------------------------------------------
# Entrada e formatação
# ----------------------------------------------------------------------------

def ler_bits(texto: str) -> np.ndarray:
    s = texto.replace(" ", "")
    if not s or set(s) - {"0", "1"}:
        raise ValueError(f"sequência inválida: '{texto}' (use só 0 e 1, ex.: {SEQUENCIA})")
    if len(s) > MAX_BITS_FIGURA:
        raise ValueError(f"a figura comporta até {MAX_BITS_FIGURA} bits; a sequência tem {len(s)}")
    return np.array([int(c) for c in s], dtype=np.int8)


def texto_para_bits(texto: str) -> np.ndarray:
    try:
        dados = texto.encode("ascii")
    except UnicodeEncodeError:
        raise ValueError(f"o texto tem caracteres fora da tabela ASCII: '{texto}'") from None
    if not dados:
        raise ValueError("texto vazio")
    if len(dados) * 8 > MAX_BITS_FIGURA:
        raise ValueError(f"a figura comporta até {MAX_BITS_FIGURA // 8} caracteres; o texto tem {len(dados)}")
    return np.unpackbits(np.frombuffer(dados, dtype=np.uint8)).astype(np.int8)


def escolher_bits(args) -> np.ndarray:
    if getattr(args, "texto", None) is not None:
        return texto_para_bits(args.texto)
    return ler_bits(getattr(args, "bits", None) or SEQUENCIA)


def ler_numero(texto: str, nome: str) -> float:
    try:
        return float(texto.replace(",", "."))
    except ValueError:
        raise ValueError(f"{nome} inválido: '{texto}'") from None


def br(x: float, casas: int = 2) -> str:
    return f"{x:,.{casas}f}".replace(",", "_").replace(".", ",").replace("_", ".")


def cient(x: float) -> str:
    return f"{x:.2e}".replace(".", ",")


def texto_bits(bits: np.ndarray) -> str:
    return "".join(str(int(b)) for b in bits)


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

def mostrar_convencoes(tecnicas: list[Tecnica]) -> None:
    for tec in tecnicas:
        print(f"  {tec.nome:<14}bit 0 -> {tec.bit0:<20}bit 1 -> {tec.bit1}")


def tabela_codigos(bits: np.ndarray) -> None:
    print(f"  Sequência: {texto_bits(bits)} ({len(bits)} bits, {int(bits.sum())} uns e "
          f"{len(bits) - int(bits.sum())} zeros), V = {br(V, 0)} V\n")
    mostrar_convencoes(CODIGOS)
    print("  (↑ = subida de -V para +V; ↓ = descida de +V para -V)\n")

    print(f"  {'bit':<14}" + "".join(f"{b:>4}" for b in bits))
    for tec in CODIGOS:
        r = tec.gerar(bits).reshape(-1, N)
        if tec.nome == "Manchester":
            celulas = ["↑" if a < b else "↓" for a, b in zip(r[:, 0], r[:, -1])]
        else:
            celulas = ["+V" if x > 0 else "-V" if x < 0 else "0" for x in r[:, 0]]
        print(f"  {tec.nome:<14}" + "".join(f"{c:>4}" for c in celulas))

    print(f"\n  {'código':<14}{'transições':>11}{'maior trecho sem transição':>29}{'nível médio (DC)':>19}")
    for tec in CODIGOS:
        s = tec.gerar(bits)
        ini, fim = trecho_sem_transicao(s)
        print(f"  {tec.nome:<14}{len(transicoes(s)):>11}{br(fim - ini, 1) + ' bits':>29}"
              f"{br(s.mean(), 3) + ' V':>19}")


def tabela_modulacoes(bits: np.ndarray) -> None:
    print("  Parâmetros:")
    print(f"    taxa de bits         Rb = {br(RB, 0)} bit/s (Tb = {br(TB * 1e3, 0)} ms)")
    print(f"    portadora            fc = {br(FC, 0)} Hz ({br(FC * TB, 0)} ciclos por bit)")
    print(f"    FSK                  f0 = {br(F0, 0)} Hz, f1 = {br(F1, 0)} Hz")
    print(f"    amplitude            A = {br(A, 0)} V")
    print(f"    amostragem           fs = {br(FS, 0)} Hz ({N} amostras por bit)")
    print(f"    portadora            e(t) = A·sen(2π·f·t + θ)\n")
    mostrar_convencoes(MODULACOES)
    print()
    rotulos = {"ASK": ("0", "A"), "FSK": (f"{F0 / 1e3:g}k", f"{F1 / 1e3:g}k"), "BPSK": ("180°", "0°")}
    print(f"  {'bit':<14}" + "".join(f"{b:>5}" for b in bits))
    for tec in MODULACOES:
        print(f"  {tec.nome:<14}" + "".join(f"{rotulos[tec.nome][b]:>5}" for b in bits))
    print("  (ASK: amplitude; FSK: frequência em kHz; BPSK: fase)")


def tabela_ruido(resultados: list[dict], bits: np.ndarray, ebn0_db: float) -> None:
    print(f"  Eb/N0 = {br(ebn0_db, 1)} dB  (SNR por amostra = Eb/N0 + 10·log10(2·Rb/fs) = "
          f"{br(ebn0_db + 10 * math.log10(2 * RB / FS), 1)} dB)")
    print(f"  {'técnica':<14}{'σ do ruído':>11}   {'bits enviados':<{len(bits) + 2}}"
          f"{'bits recebidos':<{len(bits) + 2}}erros")
    for r in resultados:
        recebidos = "".join(str(b) if b == e else "x" for b, e in zip(r["recebidos"], bits))
        print(f"  {r['nome']:<14}{br(r['sigma']) + ' V':>11}   {texto_bits(bits):<{len(bits) + 2}}"
              f"{recebidos:<{len(bits) + 2}}{len(r['erros'])}")
    print("  (x = bit errado)")


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
        "axes.grid": True, "axes.axisbelow": True, "grid.color": GRADE, "grid.linewidth": 0.8,
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


def ms(amostras: int) -> np.ndarray:
    return np.arange(amostras) / FS * 1e3


def eixo_tempo(ax, n_bits: int) -> None:
    """Sem grade; linhas tracejadas nos limites de cada bit."""
    ax.grid(False)
    ax.set_xlim(0, n_bits * TB * 1e3)
    for k in range(n_bits + 1):
        ax.axvline(k * TB * 1e3, color=EIXO, linewidth=0.7, linestyle=(0, (3, 3)), zorder=0)
    ax.set_xticks(np.arange(0, n_bits + 1, 1 if n_bits <= 20 else 4) * TB * 1e3)


def rotular_bits(ax, rotulos: list[str], cores=TINTA, tamanho: float = 9, negrito: bool = False) -> None:
    """Escreve um rótulo acima de cada intervalo de bit."""
    if isinstance(cores, str):
        cores = [cores] * len(rotulos)
    for k, (r, c) in enumerate(zip(rotulos, cores)):
        ax.text((k + 0.5) * TB * 1e3, 1.03, r, transform=ax.get_xaxis_transform(), ha="center",
                va="bottom", fontsize=tamanho, color=c, fontweight="bold" if negrito else "normal")


def degraus(ax, sinal: np.ndarray, cor: str, largura: float = 1.8) -> None:
    ax.plot(ms(len(sinal) + 1), np.append(sinal, sinal[-1]), drawstyle="steps-post",
            color=cor, linewidth=largura)


def legenda_direita(ax, texto: str) -> None:
    ax.text(1.01, 0.5, texto, transform=ax.transAxes, ha="left", va="center", fontsize=8.5, color=TINTA2)


def figura_codigos(plt, bits: np.ndarray, pasta: Path, arquivo: str) -> None:
    n = len(bits)
    fonte = 9 if n <= 24 else 7
    fig, eixos = plt.subplots(4, 1, figsize=(11, 7.4), sharex=True,
                              gridspec_kw=dict(height_ratios=[0.55, 1, 1, 1], hspace=0.5))
    relogio = np.tile(np.r_[np.ones(N // 2), np.zeros(N // 2)], n)
    degraus(eixos[0], relogio, MUDA, 1.2)
    eixos[0].set_ylim(-0.2, 1.25)
    eixos[0].set_yticks([])
    eixos[0].set_ylabel("cadência", rotation=0, ha="right", va="center")
    rotular_bits(eixos[0], [str(b) for b in bits], TINTA, fonte + 1, negrito=True)
    eixos[0].set_title(f"Códigos de linha – {n} bits, Rb = {br(RB / 1e3, 0)} kbit/s", pad=26)

    for ax, tec, cor in zip(eixos[1:], CODIGOS, CORES):
        s = tec.gerar(bits)
        ax.axhline(0, color=EIXO, linewidth=0.8)
        degraus(ax, s, cor)
        ax.set_ylim(-1.5, 1.5)
        ax.set_yticks([-V, 0, V], ["−V", "0", "+V"])
        ax.set_ylabel(tec.nome, rotation=0, ha="right", va="center", color=TINTA, fontweight="bold")
        legenda_direita(ax, f"bit 0 → {tec.bit0}\nbit 1 → {tec.bit1}")
        if tec.nome == "Manchester":
            for k, b in enumerate(bits):
                d = 1 if b else -1
                ax.annotate("", xy=((k + 0.5) * TB * 1e3, 0.75 * d), xytext=((k + 0.5) * TB * 1e3, -0.75 * d),
                            arrowprops=dict(arrowstyle="-|>", color=TINTA, linewidth=1, mutation_scale=9))
        else:
            ini, fim = trecho_sem_transicao(s)
            if fim - ini >= 3:
                ax.axvspan(ini * TB * 1e3, fim * TB * 1e3, color=CRITICO, alpha=0.08, linewidth=0)
                ax.text((ini + fim) / 2 * TB * 1e3, 0.55, f"{fim - ini:g} bits sem transição",
                        ha="center", va="center", fontsize=8.5, color=CRITICO)
        eixo_tempo(ax, n)
    eixo_tempo(eixos[0], n)
    eixos[-1].set_xlabel("tempo (ms) – linhas tracejadas: limites de cada bit")
    salvar(plt, fig, pasta, arquivo)


def figura_modulacoes(plt, bits: np.ndarray, pasta: Path, arquivo: str) -> None:
    n = len(bits)
    fonte = 8.5 if n <= 24 else 6.5
    fig, eixos = plt.subplots(5, 1, figsize=(11, 8.6), sharex=True,
                              gridspec_kw=dict(height_ratios=[0.6, 0.8, 1, 1, 1], hspace=0.6))
    t = ms(n * N)

    degraus(eixos[0], nrz_unipolar(bits), MUDA, 1.4)
    eixos[0].set_ylim(-0.2, 1.3)
    eixos[0].set_yticks([])
    eixos[0].set_ylabel("bits", rotation=0, ha="right", va="center")
    rotular_bits(eixos[0], [str(b) for b in bits], TINTA, fonte + 1.5, negrito=True)
    eixos[0].set_title(f"Modulações digitais – Rb = {br(RB / 1e3, 0)} kbit/s, fc = {br(FC / 1e3, 0)} kHz, "
                       f"A = {br(A, 0)} V, fs = {br(FS / 1e3, 0)} kHz", pad=26)

    eixos[1].plot(t, A * np.tile(PORTADORA, n), color=MUDA, linewidth=1)
    eixos[1].set_ylabel(f"portadora\n{br(FC / 1e3, 0)} kHz", rotation=0, ha="right", va="center")
    legenda_direita(eixos[1], "e(t) = A·sen(2π·fc·t)")

    rotulos = {"ASK": ("0", "A"), "FSK": (f"{F0 / 1e3:g} kHz", f"{F1 / 1e3:g} kHz"), "BPSK": ("180°", "0°")}
    for ax, tec, cor in zip(eixos[2:], MODULACOES, CORES):
        ax.plot(t, tec.gerar(bits), color=cor, linewidth=1.3)
        ax.set_ylabel(tec.nome, rotation=0, ha="right", va="center", color=TINTA, fontweight="bold")
        legenda_direita(ax, f"bit 0 → {tec.bit0}\nbit 1 → {tec.bit1}")
        rotular_bits(ax, [rotulos[tec.nome][b] for b in bits], cor, fonte)
    for ax in eixos[1:]:
        ax.axhline(0, color=EIXO, linewidth=0.8)
        ax.set_ylim(-1.35, 1.35)
        ax.set_yticks([-A, 0, A], ["−A", "0", "+A"])
    for ax in eixos:
        eixo_tempo(ax, n)
    eixos[-1].set_xlabel("tempo (ms) – linhas tracejadas: limites de cada bit")
    salvar(plt, fig, pasta, arquivo)


def transmitir_com_ruido(tecnicas: list[Tecnica], bits: np.ndarray, ebn0_db: float, rng) -> list[dict]:
    resultados = []
    for tec in tecnicas:
        limpo = tec.gerar(bits)
        recebido, sigma = awgn(limpo, ebn0_db, energia_bit(tec), rng)
        decididos, estatistica = demodular(tec, recebido)
        resultados.append(dict(nome=tec.nome, tec=tec, limpo=limpo, recebido=recebido, sigma=sigma,
                               recebidos=decididos, estatistica=estatistica,
                               erros=np.flatnonzero(decididos != bits)))
    return resultados


def figura_ruido(plt, resultados: list[dict], bits: np.ndarray, ebn0_db: float, grupo: str,
                 pasta: Path, arquivo: str) -> None:
    n = len(bits)
    fonte = 8.5 if n <= 24 else 6.5
    fig, eixos = plt.subplots(6, 1, figsize=(11, 10.5), sharex=True,
                              gridspec_kw=dict(height_ratios=[2, 1] * 3, hspace=0.55))
    t = ms(n * N)
    centros = (np.arange(n) + 0.5) * TB * 1e3
    for i, (r, cor) in enumerate(zip(resultados, CORES)):
        ax_s, ax_d = eixos[2 * i], eixos[2 * i + 1]
        tec = r["tec"]

        ax_s.plot(t, r["recebido"], color=MUDA, linewidth=0.5, alpha=0.6)
        ax_s.plot(t, r["limpo"], color=cor, linewidth=1.6)
        ax_s.set_ylim(-4, 4)
        ax_s.set_yticks([-4, -1, 0, 1, 4])
        ax_s.set_ylabel("sinal (V)")
        erros = len(r["erros"])
        ax_s.set_title(f"{tec.nome} – {erros} {'bit errado' if erros == 1 else 'bits errados'} de {n}  "
                       f"(σ do ruído = {br(r['sigma'])} V)", fontsize=10.5, pad=18)
        rotular_bits(ax_s, [str(b) for b in bits], TINTA, fonte)
        legenda_direita(ax_s, "enviado")

        errado = np.isin(np.arange(n), r["erros"])
        ax_d.bar(centros, r["estatistica"], width=0.6 * TB * 1e3,
                 color=[CRITICO if e else cor for e in errado])
        ax_d.axhline(0, color=EIXO, linewidth=0.8)
        ax_d.axhline(tec.limiar, color=TINTA, linewidth=1, linestyle=(0, (4, 3)))
        topo = max(1.5, float(np.abs(r["estatistica"]).max()) * 1.1)
        ax_d.set_ylim(-topo, topo)
        ax_d.yaxis.set_major_formatter(lambda v, _: f"{v:g}".replace(".", ","))
        ax_d.set_ylabel("decisão")
        rotular_bits(ax_d, [str(b) for b in r["recebidos"]], [CRITICO if e else TINTA2 for e in errado], fonte)
        legenda_direita(ax_d, "recebido")
    for ax in eixos:
        eixo_tempo(ax, n)
    eixos[-1].set_xlabel("tempo (ms)")
    fig.suptitle(f"{grupo} com ruído AWGN, Eb/N0 = {br(ebn0_db, 0)} dB", x=0.125, ha="left",
                 fontsize=12, fontweight="bold", color=TINTA)
    fig.text(0.125, 0.935, "colorido: sinal transmitido · cinza: sinal recebido · barras: saída do correlador "
             "em cada bit (vermelho = bit errado) · tracejado: limiar de decisão",
             fontsize=9, color=TINTA2)
    salvar(plt, fig, pasta, arquivo)


def figura_ber(plt, curvas: dict, pasta: Path) -> None:
    fig, eixos = plt.subplots(2, 1, figsize=(7.5, 8.6), sharex=True, gridspec_kw=dict(hspace=0.3))
    x = np.linspace(EBN0_BER[0], EBN0_BER[-1], 200)
    req_anti, req_on = ebn0_necessario(True), ebn0_necessario(False)
    for ax, tecnicas, titulo in ((eixos[0], CODIGOS, "Códigos de linha (banda base)"),
                                 (eixos[1], MODULACOES, f"Modulações (portadora de {br(FC / 1e3, 0)} kHz)")):
        ax.plot(x, [ber_teorica(True, e) for e in x], color=TINTA2, linewidth=1.3, zorder=2)
        ax.plot(x, [ber_teorica(False, e) for e in x], color=TINTA2, linewidth=1.3,
                linestyle=(0, (5, 3)), zorder=2)
        ax.text(0.3, ber_teorica(True, 0.3) / 5, "Q(√(2·Eb/N0))", fontsize=9, color=TINTA2, va="top")
        ax.text(8.3, ber_teorica(False, 8.3) * 3, "Q(√(Eb/N0))", fontsize=9, color=TINTA2, va="bottom")
        # Curvas que coincidem: o marcador maior fica por baixo (NRZ polar e Manchester; ASK e FSK)
        grande = 1 if tecnicas is CODIGOS else 0
        for k, tec in enumerate(tecnicas):
            pts = [(e, er / tot) for e, er, tot in curvas[tec.nome] if er > 0]
            tamanho = 10 if k == grande else 7
            ax.plot([p[0] for p in pts], [p[1] for p in pts], linestyle="none", marker=MARCADORES[k],
                    markersize=tamanho, color=CORES[k], markeredgecolor="white", markeredgewidth=1,
                    label=tec.nome, zorder=3)
        ax.axhline(1e-5, color=MUDA, linewidth=0.8)
        ax.annotate("", xy=(req_on, 1e-5), xytext=(req_anti, 1e-5),
                    arrowprops=dict(arrowstyle="<->", color=CRITICO, linewidth=1.2))
        ax.text((req_anti + req_on) / 2, 1.4e-5, f"{br(req_on - req_anti, 1)} dB", ha="center", va="bottom",
                fontsize=9, color=CRITICO)
        ax.set_yscale("log")
        ax.set_ylim(1e-6, 0.5)
        ax.set_title(titulo)
        ax.set_ylabel("BER")
        ax.legend(loc="lower left", title="marcadores: simulação · linhas: teoria",
                  title_fontsize=8.5, alignment="left")
    eixos[1].set_xlabel("Eb/N0 (dB) – energia por bit sobre a densidade de ruído")
    salvar(plt, fig, pasta, "4_ber.png")


def figura_espectro(plt, espectros: dict, pasta: Path) -> None:
    fig, eixos = plt.subplots(2, 1, figsize=(7.5, 7.6), sharex=True, gridspec_kw=dict(hspace=0.3))
    for ax, tecnicas, titulo in ((eixos[0], CODIGOS, "Códigos de linha (banda base)"),
                                 (eixos[1], MODULACOES, "Modulações")):
        topo = -np.inf
        for tec, cor in zip(tecnicas, CORES):
            f, psd = espectros[tec.nome]
            db = 10 * np.log10(psd + 1e-30)
            topo = max(topo, db.max())
            ax.plot(f / 1e3, db, color=cor, linewidth=1.2, label=tec.nome)
        ax.set_ylim(topo - 55, topo + 5)
        ax.set_title(titulo)
        ax.set_ylabel("densidade espectral (dB)")
        ax.legend(loc="upper right")
    for x, rotulo in ((FC, "fc"), (F1, "2·fc")):
        eixos[1].axvline(x / 1e3, color=MUDA, linewidth=0.8, linestyle=(0, (3, 3)))
        eixos[1].text(x / 1e3, 1.01, rotulo, transform=eixos[1].get_xaxis_transform(), ha="center",
                      va="bottom", fontsize=9, color=TINTA2)
    eixos[1].set_xlim(0, 8)
    eixos[1].set_xlabel("frequência (kHz)")
    salvar(plt, fig, pasta, "5_espectro.png")


# ----------------------------------------------------------------------------
# Experimentos
# ----------------------------------------------------------------------------

def medir_ber(tec: Tecnica, ebn0_db: float, rng, min_erros: int, max_bits: int,
              bloco: int = 20_000) -> tuple[int, int]:
    """Transmite blocos de bits aleatórios até juntar min_erros erros ou max_bits bits."""
    eb = energia_bit(tec)
    erros = total = 0
    while erros < min_erros and total < max_bits:
        bits = rng.integers(0, 2, bloco, dtype=np.int8)
        recebido, _ = awgn(tec.gerar(bits), ebn0_db, eb, rng)
        decididos, _ = demodular(tec, recebido)
        erros += int(np.count_nonzero(decididos != bits))
        total += bloco
    return erros, total


def experimento_1(plt, bits: np.ndarray, pasta: Path) -> None:
    linha("1. CÓDIGOS DE LINHA (banda base)")
    tabela_codigos(bits)
    if plt:
        print()
        figura_codigos(plt, bits, pasta, "1_codigos_linha.png")
    print()


def experimento_2(plt, bits: np.ndarray, pasta: Path) -> None:
    linha("2. MODULAÇÕES DIGITAIS (ASK, FSK e BPSK)")
    tabela_modulacoes(bits)
    if plt:
        print()
        figura_modulacoes(plt, bits, pasta, "2_modulacoes.png")
    print()


def experimento_3(plt, bits: np.ndarray, pasta: Path, rng) -> None:
    linha("3. TESTES COM RUÍDO (os mesmos bits, canal AWGN)")
    print("  O receptor correlaciona cada intervalo de bit com a forma de onda esperada")
    print(f"  (soma das {N} amostras do bit) e compara o resultado com o limiar.\n")
    for e in EBN0_RUIDO:
        for grupo, tecnicas, nome in (("Códigos de linha", CODIGOS, "codigos"),
                                      ("Modulações", MODULACOES, "modulacoes")):
            resultados = transmitir_com_ruido(tecnicas, bits, e, rng)
            tabela_ruido(resultados, bits, e)
            if plt:
                figura_ruido(plt, resultados, bits, e, grupo, pasta, f"3_ruido_{nome}_{e:g}dB.png")
            print()


def experimento_4(plt, pasta: Path, rng, min_erros: int, max_bits: int) -> None:
    linha("4. BER x Eb/N0 (bits aleatórios, simulação com as formas de onda)")
    print(f"  Cada ponto: até {min_erros} erros ou {max_bits:,} bits; pontos com BER teórica < 1e-6 "
          "não são simulados.".replace(",", "."))
    print("  Teoria: Q(√(2·Eb/N0)) para NRZ polar, Manchester e BPSK (bit 0 = inverso do bit 1);")
    print("          Q(√(Eb/N0)) para NRZ unipolar e ASK (bit 0 = nada) e para FSK (ondas ortogonais).\n")
    curvas = {}
    for grupo in (CODIGOS, MODULACOES):
        print(f"  {'Eb/N0':>6}" + "".join(f"{t.nome:>14}" for t in grupo) + f"{'Q(√(Eb/N0))':>14}"
              f"{'Q(√(2Eb/N0))':>14}")
        for tec in grupo:
            curvas[tec.nome] = []
        for e in EBN0_BER:
            celulas = []
            for tec in grupo:
                if ber_teorica(tec.antipodal, e) < 1e-6:
                    celulas.append("-")
                    continue
                erros, total = medir_ber(tec, e, rng, min_erros, max_bits)
                curvas[tec.nome].append((e, erros, total))
                celulas.append(cient(erros / total))
            print(f"  {e:>3} dB" + "".join(f"{c:>14}" for c in celulas)
                  + f"{cient(ber_teorica(False, e)):>14}{cient(ber_teorica(True, e)):>14}")
        print()
    anti, on = ebn0_necessario(True), ebn0_necessario(False)
    print(f"  Eb/N0 para BER = 1e-5: {br(anti)} dB (NRZ polar, Manchester, BPSK)")
    print(f"                         {br(on)} dB (NRZ unipolar, ASK, FSK) -> diferença de {br(on - anti)} dB")
    if plt:
        figura_ber(plt, curvas, pasta)
    print()


def experimento_5(plt, pasta: Path, rng) -> None:
    linha("5. ESPECTRO DOS SINAIS (4.000 bits aleatórios)")
    bits = rng.integers(0, 2, 4_000, dtype=np.int8)
    espectros = {tec.nome: densidade_espectral(tec.gerar(bits)) for tec in TECNICAS}
    print(f"  {'técnica':<14}{'lobo principal (teoria)':>25}{'largura':>10}{'potência dentro':>18}")
    for tec in TECNICAS:
        f, psd = espectros[tec.nome]
        f_min, f_max = BANDAS[tec.nome]
        dentro = psd[(f >= f_min) & (f <= f_max)].sum() / psd.sum()
        print(f"  {tec.nome:<14}{f'{br(f_min / 1e3, 0)} a {br(f_max / 1e3, 0)} kHz':>25}"
              f"{f'{br((f_max - f_min) / 1e3, 0)} kHz':>10}{br(100 * dentro, 1) + ' %':>18}")
    if plt:
        figura_espectro(plt, espectros, pasta)
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


def modo_experimentos(rapido: bool, pasta: Path, saida: str, semente: int = 2026) -> None:
    plt = preparar_matplotlib()
    rng = np.random.default_rng(semente)
    bits = ler_bits(SEQUENCIA)
    min_erros, max_bits = (50, 200_000) if rapido else (100, 2_000_000)
    with ExitStack() as pilha:
        if saida:
            Path(saida).parent.mkdir(parents=True, exist_ok=True)
            arq = pilha.enter_context(open(saida, "w", encoding="utf-8"))
            pilha.enter_context(redirect_stdout(Tee(sys.stdout, arq)))
        print(f"Semente: {semente}{'  (modo rápido)' if rapido else ''}\n")
        experimento_1(plt, bits, pasta)
        experimento_2(plt, bits, pasta)
        experimento_3(plt, bits, pasta, rng)
        experimento_4(plt, pasta, rng, min_erros, max_bits)
        experimento_5(plt, pasta, rng)
    if saida:
        print(f"Saída gravada em: {mostrar_caminho(Path(saida))}")


# ----------------------------------------------------------------------------
# Validação
# ----------------------------------------------------------------------------

def modo_validar() -> bool:
    linha("VALIDAÇÃO - convenções da aula 13 e conferências internas")
    resultados = []

    def caso(descricao: str, ok: bool, detalhe: str) -> None:
        resultados.append(ok)
        print(f"  [{'OK' if ok else 'FALHOU'}] {descricao}")
        print(f"         {detalhe}")

    rng = np.random.default_rng(1)
    aleatorios = rng.integers(0, 2, 1_000, dtype=np.int8)
    padrao = ler_bits(SEQUENCIA)
    ok = [t.nome for t in TECNICAS
          if all(np.array_equal(demodular(t, t.gerar(b))[0], b) for b in (padrao, aleatorios))]
    caso("Sem ruído, o receptor devolve os bits enviados", len(ok) == len(TECNICAS),
         f"{len(ok)}/{len(TECNICAS)} técnicas ({', '.join(ok)}),\n"
         f"         com a sequência padrão e com 1.000 bits aleatórios")

    slide = ler_bits(SLIDE_BITS)
    polar = "".join("+" if x > 0 else "-" for x in nrz_polar(slide)[::N])
    caso("Aula 13, slide 13: níveis do NRZ polar", polar == SLIDE_POLAR,
         f"obtido {polar}, slide {SLIDE_POLAR} (sequência {SLIDE_BITS})")

    r = manchester(slide).reshape(-1, N)
    setas = "".join("S" if a < b else "D" for a, b in zip(r[:, 0], r[:, -1]))
    caso("Aula 13, slide 14: sentido da transição Manchester no meio de cada bit", setas == SLIDE_MANCHESTER,
         f"obtido {setas}, slide {SLIDE_MANCHESTER} (S = subida, D = descida)")

    s = manchester(aleatorios)
    meio = np.arange(len(aleatorios)) * N + N // 2
    iguais = int(np.count_nonzero(aleatorios[1:] == aleatorios[:-1]))
    trans = transicoes(s)
    caso("Manchester: uma transição no meio de todo bit, e na borda só entre bits iguais",
         np.isin(meio, trans).all() and len(trans) == len(aleatorios) + iguais,
         f"{len(trans)} transições = {len(aleatorios)} bits + {iguais} pares de bits iguais")

    niveis = (set(np.unique(nrz_unipolar(aleatorios))), set(np.unique(nrz_polar(aleatorios))))
    caso("Níveis do NRZ: unipolar {0, +V} e polar {-V, +V}", niveis == ({0.0, V}, {-V, V}),
         f"unipolar {{{', '.join(br(x, 0) for x in sorted(niveis[0]))}}} V, "
         f"polar {{{', '.join(br(x, 0) for x in sorted(niveis[1]))}}} V")

    ciclos = (FC * TB, F1 * TB)
    passos = np.abs(np.diff(fsk(aleatorios)))
    bordas = passos[np.arange(1, len(aleatorios)) * N - 1]
    caso("Portadoras com número inteiro de ciclos por bit; FSK sem salto de fase na troca de bit",
         all(c == int(c) for c in ciclos) and bordas.max() <= passos.max() + 1e-12,
         f"fc: {ciclos[0]:g} ciclos, f1: {ciclos[1]:g} ciclos; maior passo na borda = "
         f"{br(bordas.max(), 3)} V, maior passo no sinal = {br(passos.max(), 3)} V")

    cruz = abs(ONDA_F0 @ ONDA_F1) / (ONDA_F0 @ ONDA_F0)
    caso("FSK: f0 e f1 são ortogonais em um bit (correlação ≈ 0)", cruz < 1e-9,
         f"correlação normalizada = {cruz:.1e}".replace(".", ","))

    esperado = {"NRZ unipolar": V ** 2 * TB / 2, "NRZ polar": V ** 2 * TB, "Manchester": V ** 2 * TB,
                "ASK": A ** 2 * TB / 4, "FSK": A ** 2 * TB / 2, "BPSK": A ** 2 * TB / 2}
    ok = [t.nome for t in TECNICAS if math.isclose(energia_bit(t), esperado[t.nome], rel_tol=1e-9)]
    caso("Energia média por bit medida nas amostras = valor teórico", len(ok) == len(TECNICAS),
         f"{len(ok)}/{len(TECNICAS)}; ex.: BPSK {cient(energia_bit(MODULACOES[2]))} V²·s = A²·Tb/2, "
         f"ASK {cient(energia_bit(MODULACOES[0]))} V²·s = A²·Tb/4 (metade dos bits sem sinal)")

    ruido, sigma = awgn(np.zeros(1_000_000), 0, 1e-3, rng)
    caso("Ruído com a variância pedida (N0·fs/2)", math.isclose(ruido.std(), sigma, rel_tol=0.01),
         f"desvio medido {br(ruido.std(), 4)} V, esperado {br(sigma, 4)} V")

    detalhes, ok = [], 0
    for tec in TECNICAS:
        erros, total = medir_ber(tec, 4, rng, min_erros=10 ** 9, max_bits=200_000)
        p = ber_teorica(tec.antipodal, 4)
        z = (erros / total - p) / math.sqrt(p * (1 - p) / total)
        ok += abs(z) < 4
        detalhes.append(f"{tec.nome} {cient(erros / total)} (teoria {cient(p)})")
    caso("BER simulada = teórica em Eb/N0 = 4 dB (200.000 bits, tolerância de 4 desvios)",
         ok == len(TECNICAS), f"{ok}/{len(TECNICAS)}:\n         "
         + "\n         ".join("; ".join(detalhes[i:i + 2]) for i in range(0, len(detalhes), 2)))

    invalidas = [(ler_bits, "10102"), (ler_bits, ""), (ler_bits, "abc"), (ler_bits, "1" * 65),
                 (texto_para_bits, "ção"), (texto_para_bits, "")]
    rejeitadas = 0
    for funcao, entrada in invalidas:
        try:
            funcao(entrada)
        except ValueError:
            rejeitadas += 1
    caso("Entradas inválidas são rejeitadas", rejeitadas == len(invalidas),
         f"{rejeitadas}/{len(invalidas)}: bits '10102', vazio, 'abc', 65 bits; texto 'ção', texto vazio")

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

    ap = argparse.ArgumentParser(description="Códigos de linha (NRZ, Manchester) e modulações (ASK, FSK, BPSK)")
    sub = ap.add_subparsers(dest="modo", metavar="MODO")

    p = sub.add_parser("experimentos", help="roda todos os experimentos (padrão)")
    p.add_argument("--rapido", action="store_true", help="menos bits nas curvas de BER (teste)")
    p.add_argument("--pasta", default=str(PASTA / "graficos"), help="pasta das figuras")
    p.add_argument("--saida", default=str(PASTA / "saida_experimentos.txt"),
                   help="arquivo onde a saída também é gravada ('' para não gravar)")

    for nome, ajuda in (("codificar", "figura e tabela dos 3 códigos de linha"),
                        ("modular", "figura e tabela de ASK, FSK e BPSK"),
                        ("ruido", "transmite os bits com ruído e mostra os erros")):
        p = sub.add_parser(nome, help=ajuda)
        g = p.add_mutually_exclusive_group()
        g.add_argument("--bits", help=f"sequência de 0 e 1 (padrão: {SEQUENCIA})")
        g.add_argument("--texto", help="texto ASCII, convertido em 8 bits por caractere")
        p.add_argument("--pasta", default=str(PASTA / "graficos"), help="pasta das figuras")
        if nome == "ruido":
            p.add_argument("--ebn0", required=True, help="Eb/N0 em dB (ex.: 6)")
            p.add_argument("--semente", type=int, default=2026, help="semente do ruído")

    sub.add_parser("validar", help="confere as convenções da aula 13 e o simulador")
    args = ap.parse_args()

    try:
        if args.modo == "validar":
            sys.exit(0 if modo_validar() else 1)
        if args.modo in ("codificar", "modular", "ruido"):
            bits = escolher_bits(args)
            pasta = Path(args.pasta)
            plt = preparar_matplotlib()
            if args.modo == "codificar":
                linha("CÓDIGOS DE LINHA")
                tabela_codigos(bits)
                print()
                figura_codigos(plt, bits, pasta, "codigos_linha.png")
            elif args.modo == "modular":
                linha("MODULAÇÕES DIGITAIS")
                tabela_modulacoes(bits)
                print()
                figura_modulacoes(plt, bits, pasta, "modulacoes.png")
            else:
                ebn0 = ler_numero(args.ebn0, "Eb/N0")
                if not -10 <= ebn0 <= 40:
                    raise ValueError(f"Eb/N0 fora da faixa de -10 a 40 dB: {args.ebn0}")
                rng = np.random.default_rng(args.semente)
                linha("TESTE COM RUÍDO")
                for grupo, tecnicas, nome in (("Códigos de linha", CODIGOS, "codigos"),
                                              ("Modulações", MODULACOES, "modulacoes")):
                    resultados = transmitir_com_ruido(tecnicas, bits, ebn0, rng)
                    tabela_ruido(resultados, bits, ebn0)
                    figura_ruido(plt, resultados, bits, ebn0, grupo, pasta, f"ruido_{nome}_{ebn0:g}dB.png")
                    print()
        else:
            modo_experimentos(getattr(args, "rapido", False),
                              Path(getattr(args, "pasta", PASTA / "graficos")),
                              getattr(args, "saida", str(PASTA / "saida_experimentos.txt")))
    except (ValueError, OSError) as e:
        print(f"Erro: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
