#!/usr/bin/env python3
"""
Gera a apresentacao do Trabalho II sobre o modelo oficial da UNISINOS.

Mesmo esquema do Trabalho I: cada slide do modelo e uma imagem de fundo em tela
cheia (logo e moldura ja desenhados), com caixas de texto, formas e tabelas
nativas por cima. Os numeros vem do proprio repositorio (metricas.py, o log e
os graficos de resultados/), entao os slides nao divergem da execucao oficial.

As notas de cada slide sao o roteiro de fala; o gerador tambem as grava em
roteiro_apresentacao.md, com o tempo de cada slide, para ensaiar.

Uso:  python scripts/gerar_apresentacao.py
Saida: Apresentacao_Trabalho2_Matheus_Milanezi.pptx e roteiro_apresentacao.md
"""

from __future__ import annotations

import io
import re
import sys
import zipfile
from pathlib import Path

from PIL import Image
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.dml import MSO_LINE_DASH_STYLE
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt

RAIZ = Path(__file__).resolve().parent.parent
REPO = RAIZ / "repo"
RESULTADOS = REPO / "resultados"
# o modelo da UNISINOS ficou na pasta do Trabalho I
MODELO = RAIZ.parent / "Trabalho 1" / "Modelo-de-apresentacao-Unisinos.pptx"
SAIDA = RAIZ / "Apresentacao_Trabalho2_Matheus_Milanezi.pptx"
ROTEIRO = RAIZ / "roteiro_apresentacao.md"

sys.path.insert(0, str(REPO))
import canal  # noqa: E402
import metricas  # noqa: E402
from formato import br  # noqa: E402

# ---------------------------------------------------------------------------
# Identidade visual: azul do modelo + as cores dos esquemas nos graficos
# ---------------------------------------------------------------------------
AZUL = RGBColor(0x25, 0x3A, 0x7E)        # cor institucional do modelo
AZUL_ESCURO = RGBColor(0x1A, 0x2A, 0x5E)
TEXTO_2 = RGBColor(0x4A, 0x55, 0x78)     # texto secundario, azul acinzentado
MUDO = RGBColor(0x6B, 0x72, 0x87)
BRANCO = RGBColor(0xFF, 0xFF, 0xFF)
CLARO = RGBColor(0xC9, 0xD1, 0xE8)       # texto secundario sobre o azul
CARTAO = RGBColor(0xEE, 0xF1, 0xF8)      # tinta clara do azul do modelo
CARTAO_BORDA = RGBColor(0xD5, 0xDB, 0xEA)
LINHA = RGBColor(0x9A, 0xA3, 0xB8)
ERRO = RGBColor(0xD9, 0x4E, 0x1A)        # caracteres que chegaram errados

# mesmas cores do experimentos.py
ESQUEMAS = [("bpsk", "nrz"), ("bpsk", "manchester"), ("16qam", "nrz"),
            ("16qam", "manchester")]
COR = {("bpsk", "nrz"): RGBColor(0x2A, 0x78, 0xD6),
       ("bpsk", "manchester"): RGBColor(0xEB, 0x68, 0x34),
       ("16qam", "nrz"): RGBColor(0x1B, 0xAF, 0x7A),
       ("16qam", "manchester"): RGBColor(0xED, 0xA1, 0x00)}
CHIPS_POR_SIMBOLO = {"bpsk": 1, "16qam": 4}
CHIPS_POR_BIT = {"nrz": 1, "manchester": 2}

# Imagens de fundo do modelo (ppt/media/imageN.png)
FUNDO_CAPA = "ppt/media/image1.png"         # capa branca com o U azul
FUNDO_CONTEUDO = "ppt/media/image3.png"     # branco com logo e moldura
FUNDO_DESTAQUE = "ppt/media/image4.png"     # azul com logo e moldura
FUNDO_FIM = "ppt/media/image6.png"          # encerramento branco

# Grade dos slides de conteudo (polegadas; slide de 13,33 x 7,5)
X0 = 1.88           # alinhado com o texto do modelo, a direita do logo
LARG = 10.87        # ate a moldura da direita
Y_CONTEUDO = 2.05

ROTEIRO_SLIDES: list[tuple[str, int, str]] = []   # (titulo, segundos, fala)


def nome(m: str, c: str) -> str:
    return f"{'BPSK' if m == 'bpsk' else '16-QAM'} + {'NRZ' if c == 'nrz' else 'Manchester'}"


def eta(m: str, c: str) -> float:
    return metricas.eficiencia_espectral(CHIPS_POR_SIMBOLO[m], CHIPS_POR_BIT[c])


def limpar_fundo_conteudo(dados: bytes) -> bytes:
    """
    A imagem de fundo branca do modelo traz um residuo: o hifen de 'laboris-'
    do texto de exemplo ficou gravado nela, em (1647-1655, 533-534) px. Pinta a
    regiao com a cor do fundo ao redor.
    """
    im = Image.open(io.BytesIO(dados)).convert("RGBA")
    cor_fundo = im.getpixel((1630, 533))
    for y in range(528, 540):
        for x in range(1642, 1661):
            im.putpixel((x, y), cor_fundo)
    saida = io.BytesIO()
    im.save(saida, format="PNG")
    return saida.getvalue()


# ===========================================================================
# Primitivas
# ===========================================================================

def novo_slide(prs, fundo: str, imagens: dict):
    layout = next(l for l in prs.slide_layouts if l.name == "Em branco")
    s = prs.slides.add_slide(layout)
    s.shapes.add_picture(io.BytesIO(imagens[fundo]), 0, 0,
                         prs.slide_width, prs.slide_height)
    return s


def texto(slide, x, y, w, h, paragrafos, *, tamanho=16, cor=AZUL,
          negrito=False, alinhamento=PP_ALIGN.LEFT, ancora=MSO_ANCHOR.TOP,
          fonte=None, espaco_depois=0):
    """
    paragrafos: str, ou lista de paragrafos; cada paragrafo e str ou lista de
    trechos (texto, {opcoes}) com opcoes negrito/cor/tamanho/fonte.
    """
    caixa = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = caixa.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = ancora
    _preencher(tf, paragrafos, tamanho, cor, negrito, alinhamento, fonte,
               espaco_depois)
    return caixa


def _preencher(tf, paragrafos, tamanho, cor, negrito, alinhamento, fonte,
               espaco_depois):
    if isinstance(paragrafos, str):
        paragrafos = [paragrafos]
    for i, par in enumerate(paragrafos):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = alinhamento
        if espaco_depois and i < len(paragrafos) - 1:
            p.space_after = Pt(espaco_depois)
        trechos = [(par, {})] if isinstance(par, str) else par
        for conteudo, op in trechos:
            r = p.add_run()
            r.text = conteudo
            f = r.font
            f.size = Pt(op.get("tamanho", tamanho))
            f.bold = op.get("negrito", negrito)
            f.color.rgb = op.get("cor", cor)
            if op.get("fonte", fonte):
                f.name = op.get("fonte", fonte)


def titulo(slide, principal: str, apoio: str, *, claro=False):
    """Par titulo em negrito + linha regular, como no modelo."""
    cor = BRANCO if claro else AZUL
    texto(slide, X0, 0.62, LARG, 0.7, principal, tamanho=34, negrito=True,
          cor=cor)
    texto(slide, X0, 1.27, LARG, 0.45, apoio, tamanho=20, cor=cor)


def rodape(slide, conteudo: str, *, claro=False):
    texto(slide, X0, 6.55, LARG, 0.3, conteudo, tamanho=12,
          cor=CLARO if claro else MUDO)


def retangulo(slide, x, y, w, h, cor, *, arredondado=False, borda=None,
              raio=0.12, forma=None):
    tipo = forma or (MSO_SHAPE.ROUNDED_RECTANGLE if arredondado
                     else MSO_SHAPE.RECTANGLE)
    f = slide.shapes.add_shape(tipo, Inches(x), Inches(y), Inches(w), Inches(h))
    if arredondado:
        f.adjustments[0] = raio
    f.fill.solid()
    f.fill.fore_color.rgb = cor
    if borda:
        f.line.color.rgb = borda
        f.line.width = Pt(1)
    else:
        f.line.fill.background()
    f.shadow.inherit = False
    return f


def circulo(slide, cx, cy, r, cor):
    return retangulo(slide, cx - r, cy - r, 2 * r, 2 * r, cor,
                     forma=MSO_SHAPE.OVAL)


def seta(slide, x, y, w, h, tipo=MSO_SHAPE.RIGHT_ARROW, cor=AZUL):
    return retangulo(slide, x, y, w, h, cor, forma=tipo)


def linha(slide, x1, y1, x2, y2, cor, espessura, *, tracejado=False):
    c = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(x1),
                                   Inches(y1), Inches(x2), Inches(y2))
    c.line.color.rgb = cor
    c.line.width = Pt(espessura)
    if tracejado:
        c.line.dash_style = MSO_LINE_DASH_STYLE.DASH
    return c


def cartao(slide, x, y, w, h, cabecalho, corpo, *, tam_cab=19, tam_corpo=15,
           fonte_cab=None, fundo=CARTAO, cor_cab=AZUL, cor_corpo=TEXTO_2):
    forma = retangulo(slide, x, y, w, h, fundo, arredondado=True, raio=0.07)
    tf = forma.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = Inches(0.22)
    tf.margin_top = Inches(0.18)
    tf.margin_bottom = Inches(0.12)
    tf.vertical_anchor = MSO_ANCHOR.TOP
    _preencher(tf, [[(cabecalho, {"negrito": True, "tamanho": tam_cab,
                                  "fonte": fonte_cab, "cor": cor_cab})],
                    [(corpo, {"tamanho": tam_corpo, "cor": cor_corpo})]],
               tam_corpo, AZUL, False, PP_ALIGN.LEFT, None, 6)
    return forma


def estatistica(slide, x, y, w, h, numero, rotulo, *, fundo=CARTAO,
                cor_num=AZUL, cor_rot=TEXTO_2, tam_num=40, tam_rot=15):
    """Numero grande com uma legenda curta embaixo."""
    retangulo(slide, x, y, w, h, fundo, arredondado=True, raio=0.07)
    texto(slide, x + 0.22, y + 0.18, w - 0.44, h - 0.3,
          [[(numero, {"negrito": True, "tamanho": tam_num, "cor": cor_num})],
           [(rotulo, {"tamanho": tam_rot, "cor": cor_rot})]], espaco_depois=2)


def tabela(slide, x, y, larguras, linhas, *, tamanho=16, altura_linha=0.44,
           cab_fundo=AZUL, cab_texto=BRANCO, corpo_fundo=None,
           corpo_texto=AZUL, alinhamentos=None, altura_cab=None):
    """
    linhas[0] e o cabecalho. Uma celula pode ser str ou uma lista de
    paragrafos no formato de texto() (para trechos com cores diferentes).
    """
    n_l, n_c = len(linhas), len(larguras)
    gt = slide.shapes.add_table(n_l, n_c, Inches(x), Inches(y),
                                Inches(sum(larguras)),
                                Inches(altura_linha * n_l))
    t = gt.table
    t.first_row = True
    t.horz_banding = False
    for j, lw in enumerate(larguras):
        t.columns[j].width = Inches(lw)
    for i in range(n_l):
        t.rows[i].height = Inches(altura_cab if i == 0 and altura_cab
                                  else altura_linha)
        for j in range(n_c):
            c = t.cell(i, j)
            c.margin_left = c.margin_right = Inches(0.12)
            c.margin_top = c.margin_bottom = Inches(0.04)
            c.vertical_anchor = MSO_ANCHOR.MIDDLE
            c.fill.solid()
            if i == 0:
                c.fill.fore_color.rgb = cab_fundo
            else:
                c.fill.fore_color.rgb = corpo_fundo or (
                    BRANCO if i % 2 else RGBColor(0xF6, 0xF7, 0xFB))
            tf = c.text_frame
            tf.word_wrap = True
            conteudo = linhas[i][j]
            alin = alinhamentos[j] if alinhamentos else PP_ALIGN.LEFT
            if isinstance(conteudo, list):
                _preencher(tf, conteudo, tamanho, corpo_texto, False, alin,
                           None, 0)
                continue
            p = tf.paragraphs[0]
            p.alignment = alin
            r = p.add_run()
            r.text = str(conteudo)
            r.font.size = Pt(tamanho)
            r.font.bold = (i == 0) or (j == 0)
            r.font.color.rgb = cab_texto if i == 0 else corpo_texto
    return gt


def imagem(slide, caminho_ou_bytes, x, y, *, w=None, h=None):
    fonte = (io.BytesIO(caminho_ou_bytes) if isinstance(caminho_ou_bytes, bytes)
             else str(caminho_ou_bytes))
    return slide.shapes.add_picture(fonte, Inches(x), Inches(y),
                                    Inches(w) if w else None,
                                    Inches(h) if h else None)


def recorte(caminho: Path, caixa: tuple[int, int, int, int]) -> bytes:
    saida = io.BytesIO()
    Image.open(caminho).crop(caixa).save(saida, format="PNG")
    return saida.getvalue()


def notas(slide, titulo_roteiro: str, segundos: int, fala: str):
    slide.notes_slide.notes_text_frame.text = (
        f"[cerca de {segundos} s] {fala}")
    ROTEIRO_SLIDES.append((titulo_roteiro, segundos, fala))


def lista_valores(slide, x, y, w, cabecalho, linhas, *, passo=0.55):
    """Cabecalho + linhas 'bolinha da cor do esquema, nome, valor'."""
    texto(slide, x, y, w, 0.4, cabecalho, tamanho=18, negrito=True)
    y += 0.6
    for (m, c), valor in linhas:
        circulo(slide, x + 0.11, y + 0.17, 0.11, COR[(m, c)])
        texto(slide, x + 0.35, y, w - 1.9, 0.36, nome(m, c), tamanho=16,
              cor=TEXTO_2, ancora=MSO_ANCHOR.MIDDLE)
        texto(slide, x + w - 1.55, y, 1.55, 0.36, valor, tamanho=18,
              negrito=True, alinhamento=PP_ALIGN.RIGHT,
              ancora=MSO_ANCHOR.MIDDLE)
        y += passo
    return y


# ===========================================================================
# Dados
# ===========================================================================

def ler_mensagens() -> tuple[str, dict]:
    """Le a secao MENSAGEM DE TESTE do log oficial."""
    log = (RESULTADOS / "log_experimentos.txt").read_text(encoding="utf-8")
    original = re.search(r'MENSAGEM DE TESTE: "(.*)"', log).group(1)
    nomes = {nome(m, c): (m, c) for m, c in ESQUEMAS}
    recebidas, atual = {}, None
    secao = log.split("MENSAGEM DE TESTE")[1].split("EFICIÊNCIA")[0]
    for l in secao.splitlines():
        if l.strip() in nomes:
            atual = nomes[l.strip()]
            continue
        achou = re.match(r"\s+(\d+) dB  (.*?)   \((\d+) bits? errados?\)$", l)
        if achou and atual:
            db, msg, erros = achou.groups()
            recebidas[(atual, int(db))] = (msg, int(erros))
    return original, recebidas


def dados() -> dict:
    d = {"ebn0": {}, "snr": {}, "shannon": {}}
    for m, c in ESQUEMAS:
        e = metricas.ebn0_necessario(m, c)
        d["ebn0"][(m, c)] = e
        d["snr"][(m, c)] = canal.ebn0_para_snr_db(e, eta(m, c))
        d["shannon"][(m, c)] = metricas.limite_shannon_ebn0_db(eta(m, c))
    d["original"], d["mensagens"] = ler_mensagens()
    return d


# ===========================================================================
# Slides
# ===========================================================================

def s_capa(prs, img):
    s = novo_slide(prs, FUNDO_CAPA, img)
    x, w = 5.76, 6.95
    texto(s, x, 2.05, w, 0.4, "Trabalho II", tamanho=20)
    texto(s, x, 2.45, w, 1.45, "Do texto ao texto, passando pelo ruído",
          tamanho=40, negrito=True)
    texto(s, x, 3.95, w, 0.6, "Sistema de transmissão digital", tamanho=28)
    texto(s, x, 4.7, w, 0.9,
          ["Matheus Milanezi", "Prof. Cristiano Bonato Both · 30/11/2026"],
          tamanho=18, espaco_depois=2)
    notas(s, "Capa", 20,
          "Meu trabalho é um sistema de transmissão digital completo: eu digito "
          "um texto, ele vira bits, passa por um canal com ruído e é "
          "reconstruído do outro lado. No caminho, comparo duas modulações e "
          "dois códigos de linha e meço quantos bits chegam errados.")


def s_cadeia(prs, img):
    s = novo_slide(prs, FUNDO_CONTEUDO, img)
    titulo(s, "Cada caixa é um arquivo Python", "A cadeia implementada")
    bw, bh, g = 1.85, 1.15, 0.42
    y_tx, y_rx = Y_CONTEUDO, Y_CONTEUDO + 1.6
    tx = [("Mensagem", "ASCII"), ("Bits", "fonte.py"),
          ("Código de linha", "codigo_linha.py"), ("Modulação", "modulacao.py")]
    rx = [("BER", "metricas.py"), ("Texto", "fonte.py"),
          ("Decodificação", "codigo_linha.py"), ("Demodulação", "modulacao.py")]

    def caixa(x, y, cab, arq):
        f = retangulo(s, x, y, bw, bh, CARTAO, arredondado=True, raio=0.1)
        tf = f.text_frame
        tf.word_wrap = True
        tf.margin_left = tf.margin_right = Inches(0.08)
        tf.vertical_anchor = MSO_ANCHOR.MIDDLE
        _preencher(tf, [[(cab, {"negrito": True, "tamanho": 16})],
                        [(arq, {"tamanho": 12, "cor": TEXTO_2,
                                "fonte": "Consolas"})]],
                   16, AZUL, False, PP_ALIGN.CENTER, None, 2)

    for i, (cab, arq) in enumerate(tx):
        x = X0 + i * (bw + g)
        caixa(x, y_tx, cab, arq)
        seta(s, x + bw + 0.08, y_tx + bh / 2 - 0.16, g - 0.16, 0.32)
    for i, (cab, arq) in enumerate(rx):
        x = X0 + i * (bw + g)
        caixa(x, y_rx, cab, arq)
        if i:
            seta(s, x - g + 0.08, y_rx + bh / 2 - 0.16, g - 0.16, 0.32,
                 MSO_SHAPE.LEFT_ARROW)
        else:
            # a BER compara o que chegou com o que foi enviado
            linha(s, x + bw / 2, y_tx + bh + 0.06, x + bw / 2, y_rx - 0.06,
                  LINHA, 1.5, tracejado=True)
    xc = X0 + 4 * (bw + g)
    f = retangulo(s, xc, y_tx, X0 + LARG - xc, y_rx + bh - y_tx, AZUL,
                  arredondado=True, raio=0.08)
    tf = f.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = Inches(0.12)
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    _preencher(tf, [[("Canal AWGN", {"negrito": True, "tamanho": 18})],
                    [("ruído gaussiano com SNR controlada", {"tamanho": 13,
                                                            "cor": CLARO})],
                    [("canal.py", {"tamanho": 12, "cor": CLARO,
                                   "fonte": "Consolas"})]],
               16, BRANCO, False, PP_ALIGN.CENTER, None, 6)
    # retorno do canal para o receptor
    seta(s, xc - g + 0.08, y_rx + bh / 2 - 0.16, g - 0.16, 0.32,
         MSO_SHAPE.LEFT_ARROW)

    y = y_rx + bh + 0.45
    texto(s, X0, y, 1.6, 0.4, "Circulam:", tamanho=16, negrito=True,
          ancora=MSO_ANCHOR.MIDDLE)
    itens = ["bits", "chips", "símbolos I + jQ", "valores suaves"]
    x = X0 + 1.4
    for i, item in enumerate(itens):
        w = 1.0 + 0.08 * len(item)
        f = retangulo(s, x, y, w, 0.4, BRANCO, arredondado=True, raio=0.5,
                      borda=CARTAO_BORDA)
        tf = f.text_frame
        tf.margin_top = tf.margin_bottom = 0
        tf.vertical_anchor = MSO_ANCHOR.MIDDLE
        _preencher(tf, [item], 15, AZUL, False, PP_ALIGN.CENTER, None, 0)
        x += w
        if i < len(itens) - 1:
            texto(s, x, y, 0.4, 0.4, "→", tamanho=18, cor=TEXTO_2,
                  alinhamento=PP_ALIGN.CENTER, ancora=MSO_ANCHOR.MIDDLE)
            x += 0.4
    rodape(s, "Python 3 + numpy + matplotlib · simulação em banda base "
              "equivalente: cada símbolo é um número complexo, sem gerar a "
              "portadora")
    notas(s, "A cadeia", 60,
          "Esta é a cadeia inteira, e cada caixa é um arquivo Python. Em cima, "
          "o transmissor: a mensagem em ASCII vira bits; o código de linha "
          "transforma os bits em chips, que é o que de fato vai para o meio; e "
          "a modulação transforma os chips em símbolos. O canal soma ruído "
          "gaussiano, o AWGN, com nível controlado. Embaixo, o receptor faz o "
          "caminho de volta: demodula, decodifica e junta os bits em texto. No "
          "fim, comparo o que chegou com o que foi enviado para calcular a "
          "BER, a taxa de erro de bits. Um detalhe de implementação: a "
          "simulação é em banda base, cada símbolo é um número complexo, I "
          "mais jQ, sem gerar a senoide da portadora. Isso não muda a BER e "
          "permite simular milhões de bits em segundos.")


def s_bits_chips(prs, img):
    s = novo_slide(prs, FUNDO_CONTEUDO, img)
    titulo(s, "Bits viram chips",
           "Geração de dados e codificação de canal")
    letra = "R"
    bits = [int(b) for b in format(ord(letra), "08b")]
    manchester = []
    for b in bits:
        manchester += [0, 1] if b else [1, 0]

    xl, xc, slot, ch = X0, X0 + 1.75, 0.6, 0.55

    def celula(x, w, y, v):
        f = retangulo(s, x, y, w, ch, AZUL if v else CARTAO)
        tf = f.text_frame
        tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
        tf.vertical_anchor = MSO_ANCHOR.MIDDLE
        _preencher(tf, [str(v)], 18, BRANCO if v else AZUL, True,
                   PP_ALIGN.CENTER, "Consolas", 0)

    linhas_y = [Y_CONTEUDO, Y_CONTEUDO + 0.85, Y_CONTEUDO + 1.7,
                Y_CONTEUDO + 2.55]
    rotulos = [("Caractere", "fonte.py"), ("Bits", "fonte.py"),
               ("NRZ", "1 chip por bit"), ("Manchester", "2 chips por bit")]
    for y, (r, sub) in zip(linhas_y, rotulos):
        texto(s, xl, y - 0.04, 1.7, ch + 0.1,
              [[(r, {"negrito": True, "tamanho": 17})],
               [(sub, {"tamanho": 11, "cor": TEXTO_2})]],
              ancora=MSO_ANCHOR.MIDDLE)
    f = retangulo(s, xc, linhas_y[0], 8 * slot - 0.04, ch, CARTAO)
    tf = f.text_frame
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    _preencher(tf, [[(f"'{letra}'", {"negrito": True, "fonte": "Consolas"}),
                     (f"  = {ord(letra)} em ASCII", {})]], 18, AZUL, False,
               PP_ALIGN.CENTER, None, 0)
    for i, b in enumerate(bits):
        celula(xc + i * slot, slot - 0.04, linhas_y[1], b)
        celula(xc + i * slot, slot - 0.04, linhas_y[2], b)
        celula(xc + i * slot, slot / 2 - 0.03, linhas_y[3], manchester[2 * i])
        celula(xc + i * slot + slot / 2 - 0.01, slot / 2 - 0.03, linhas_y[3],
               manchester[2 * i + 1])
    texto(s, xc, linhas_y[3] + ch + 0.2, 8 * slot, 0.7,
          [[("Bit 0 → ", {}), ("10", {"negrito": True, "fonte": "Consolas"}),
            (" (descida no meio)    Bit 1 → ", {}),
            ("01", {"negrito": True, "fonte": "Consolas"}),
            (" (subida)", {})]], tamanho=14, cor=TEXTO_2)

    xr = 8.75
    w = X0 + LARG - xr
    itens = [
        ("NRZ: a referência", "Um chip igual ao bit. Sem redundância e sem "
         "transição garantida."),
        ("Manchester", "Convenção IEEE 802.3 (Ethernet de 10 Mbit/s): "
         "transição no meio de todo bit."),
        ("Decodificação suave", "O receptor compara as duas metades do bit e "
         "aproveita a energia dos dois chips."),
    ]
    for i, (cab, corpo) in enumerate(itens):
        cartao(s, xr, Y_CONTEUDO + i * 1.45, w, 1.3, cab, corpo, tam_cab=18,
               tam_corpo=15)
    rodape(s, "Mensagens com acento são recusadas: o ASCII tem 128 caracteres. "
              "No receptor, os bits voltam a texto de 8 em 8")
    notas(s, "Bits viram chips", 60,
          "Começando pela fonte: cada caractere vira 8 bits. O R, primeira "
          "letra da mensagem de teste, é 82 em ASCII, ou 0 1 0 1 0 0 1 0. "
          "Depois vem o código de linha. No NRZ, cada bit vira um chip igual a "
          "ele: é a referência. No Manchester, cada bit vira dois chips: o 0 "
          "vira 1 0, uma descida no meio do bit, e o 1 vira 0 1, uma subida. "
          "É a convenção da Ethernet de 10 megabits. Reparem que a linha do "
          "Manchester tem o dobro de chips: isso vai custar o dobro de banda. "
          "No receptor, o Manchester não decide chip por chip: ele compara as "
          "duas metades do bit; se a segunda for maior, é uma subida, bit 1. "
          "Assim aproveita a energia dos dois chips.")


def s_modulacao(prs, img):
    s = novo_slide(prs, FUNDO_CONTEUDO, img)
    titulo(s, "Duas modulações com a mesma energia",
           "Modulação e demodulação")
    h = 4.25
    # BPSK
    x, w = X0, 3.15
    retangulo(s, x, Y_CONTEUDO, w, h, CARTAO, arredondado=True, raio=0.05)
    texto(s, x + 0.25, Y_CONTEUDO + 0.2, w - 0.5, 0.8,
          [[("BPSK", {"negrito": True, "tamanho": 20})],
           [("1 chip por símbolo", {"tamanho": 14, "cor": TEXTO_2})]])
    cy, cx = Y_CONTEUDO + 2.25, x + w / 2
    linha(s, x + 0.3, cy, x + w - 0.3, cy, LINHA, 1.25)
    linha(s, cx, cy - 0.9, cx, cy + 0.9, LINHA, 1.25)
    for sinal, chip in ((-1, 0), (1, 1)):
        px = cx + sinal * 0.9
        circulo(s, px, cy, 0.17, COR[("bpsk", "nrz")])
        texto(s, px - 0.6, cy + 0.3, 1.2, 0.7,
              [[(f"chip {chip}", {"negrito": True, "fonte": "Consolas"})],
               [("−1" if sinal < 0 else "+1", {"cor": TEXTO_2})]],
              tamanho=15, alinhamento=PP_ALIGN.CENTER)
    texto(s, x + 0.25, Y_CONTEUDO + h - 0.65, w - 0.5, 0.45,
          "fases de 180° e 0°", tamanho=14, cor=TEXTO_2,
          alinhamento=PP_ALIGN.CENTER)

    # 16-QAM com os rotulos de Gray (2 chips de I + 2 chips de Q)
    x, w = X0 + 3.45, 3.95
    retangulo(s, x, Y_CONTEUDO, w, h, CARTAO, arredondado=True, raio=0.05)
    texto(s, x + 0.25, Y_CONTEUDO + 0.2, w - 0.5, 0.8,
          [[("16-QAM", {"negrito": True, "tamanho": 20})],
           [("4 chips por símbolo: 2 em I, 2 em Q", {"tamanho": 14,
                                                     "cor": TEXTO_2})]])
    gray = {-3: "00", -1: "01", 1: "11", 3: "10"}
    cx, cy, passo = x + w / 2, Y_CONTEUDO + 2.6, 0.8
    linha(s, cx - 1.6, cy, cx + 1.6, cy, LINHA, 1.25)
    linha(s, cx, cy - 1.55, cx, cy + 1.55, LINHA, 1.25)
    for ni in (-3, -1, 1, 3):
        for nq in (-3, -1, 1, 3):
            px, py = cx + ni / 2 * passo, cy - nq / 2 * passo
            circulo(s, px, py, 0.085, COR[("16qam", "nrz")])
            texto(s, px - 0.4, py + 0.08, 0.8, 0.25, gray[ni] + gray[nq],
                  tamanho=11, cor=AZUL, fonte="Consolas",
                  alinhamento=PP_ALIGN.CENTER)

    xr = X0 + 7.7
    wr = X0 + LARG - xr
    blocos = [
        ("Código de Gray", "Vizinhos diferem em um único chip: confundir um "
         "símbolo com o vizinho custa 1 chip, não 2."),
        ("Energia média 1", "A grade é dividida por √10: mesma potência que "
         "o BPSK."),
        ("Saída suave", "Um número por chip: o sinal diz 0 ou 1, o tamanho "
         "diz a confiança."),
    ]
    y = Y_CONTEUDO
    for cab, corpo in blocos:
        texto(s, xr, y, wr, 1.35,
              [[(cab, {"negrito": True, "tamanho": 18})],
               [(corpo, {"tamanho": 15, "cor": TEXTO_2})]], espaco_depois=4)
        y += 1.45
    rodape(s, "Rótulo de cada ponto: 2 chips do eixo I seguidos de 2 chips do "
              "eixo Q, níveis −3, −1, +1, +3 ↔ 00, 01, 11, 10")
    notas(s, "Modulações", 70,
          "Duas modulações. No BPSK, cada chip vira um símbolo: o 0 é menos 1, "
          "o 1 é mais 1, ou seja, fases de 180 e 0 graus. Na 16-QAM, quatro "
          "chips viram um símbolo: os dois primeiros escolhem a posição no "
          "eixo I, o horizontal, e os dois últimos no eixo Q, o vertical. São "
          "16 pontos, e cada um carrega 4 bits. Os rótulos seguem o código de "
          "Gray: dois pontos vizinhos diferem em um único chip. Como o erro "
          "mais comum é o ruído empurrar o símbolo para o vizinho, esse erro "
          "custa 1 chip, e não 2. A grade é dividida por raiz de 10 para que a "
          "energia média seja 1, igual à do BPSK: as duas modulações "
          "transmitem com a mesma potência. E o demodulador não devolve só 0 "
          "ou 1: devolve um número por chip, em que o sinal diz o valor e o "
          "tamanho diz a confiança. É esse número que o Manchester usa para "
          "comparar as duas metades do bit.")


def s_canal(prs, img):
    s = novo_slide(prs, FUNDO_CONTEUDO, img)
    titulo(s, "O ruído é controlado por Eb/N0",
           "Canal AWGN e controle da SNR")
    f = retangulo(s, X0, Y_CONTEUDO, LARG, 1.05, AZUL, arredondado=True,
                  raio=0.12)
    tf = f.text_frame
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    _preencher(tf, [[("SNR (dB) = Eb/N0 (dB) + 10·log10(η)",
                      {"negrito": True, "fonte": "Consolas", "tamanho": 24})],
                    [("η = bits de informação por símbolo", {"tamanho": 14,
                                                            "cor": CLARO})]],
               16, BRANCO, False, PP_ALIGN.CENTER, None, 2)
    ordem = sorted(ESQUEMAS, key=lambda e: eta(*e))
    linhas = [["Esquema", "η", "SNR − Eb/N0"]]
    for m, c in ordem:
        e = eta(m, c)
        dif = canal.ebn0_para_snr_db(0, e)
        linhas.append([nome(m, c), br(e, 1).replace(",0", ""),
                       f"{'+' if dif > 0.005 else ''}{br(dif)} dB"
                       .replace("-", "−")])
    tabela(s, X0, Y_CONTEUDO + 1.35, [3.3, 1.4, 2.1], linhas, tamanho=17,
           altura_linha=0.5,
           alinhamentos=[PP_ALIGN.LEFT, PP_ALIGN.CENTER, PP_ALIGN.CENTER])
    xr = X0 + 7.2
    wr = X0 + LARG - xr
    blocos = [
        ("SNR = Es/N0", "Energia de um símbolo sobre o ruído."),
        ("Eb/N0", "Energia de um bit de informação. É o eixo justo para "
         "comparar esquemas com η diferentes."),
    ]
    y = Y_CONTEUDO + 1.35
    for cab, corpo in blocos:
        texto(s, xr, y, wr, 1.1,
              [[(cab, {"negrito": True, "tamanho": 18})],
               [(corpo, {"tamanho": 15, "cor": TEXTO_2})]], espaco_depois=4)
        y += 1.0 if cab.startswith("SNR") else 1.3
    texto(s, xr, y, wr, 0.4,
          [[("Com Es = 1:  ", {}),
            ("N0 = 10^(−SNR/10)", {"negrito": True, "fonte": "Consolas"})]],
          tamanho=15)
    rodape(s, "Validação: a SNR medida no ruído gerado foi 10,001 dB para "
              "10 dB pedidos")
    notas(s, "Canal e SNR", 50,
          "O canal. A SNR é a energia de um símbolo sobre o ruído. Só que os "
          "esquemas carregam números diferentes de bits por símbolo, de meio "
          "bit até 4. Para comparar de forma justa, eu fixo o Eb/N0, a energia "
          "por bit de informação, e converto para SNR com esta fórmula. Na "
          "tabela: o BPSK com NRZ tem 1 bit por símbolo, então SNR e Eb/N0 são "
          "iguais; a 16-QAM com NRZ tem 4, e a SNR fica 6 dB acima; o BPSK com "
          "Manchester tem meio bit por símbolo, e fica 3 abaixo. Como a "
          "energia do símbolo é 1, o nível de ruído sai direto da SNR. E eu "
          "conferi o ruído gerado: pedi 10 dB e medi 10,001.")


def s_validacao(prs, img):
    s = novo_slide(prs, FUNDO_CONTEUDO, img)
    titulo(s, "Antes de medir, conferir", "Validação e metodologia")
    stats = [("27/27", "verificações do validar.py passaram"),
             ("12/12", "pontos simulados dentro de 4σ da teoria"),
             ("200", "erros por ponto: incerteza de ±14 %"),
             ("~25 s", "para refazer tudo, com a semente fixa 2026")]
    g = 0.27
    w = (LARG - 3 * g) / 4
    for i, (num, rot) in enumerate(stats):
        estatistica(s, X0 + i * (w + g), Y_CONTEUDO, w, 1.9, num, rot)
    w2 = (LARG - g) / 2
    cartao(s, X0, Y_CONTEUDO + 2.2, w2, 1.95, "O que o validar.py confere",
           "Cada bloco isolado (ASCII, Manchester, energia, Gray, ruído), a "
           "cadeia sem ruído (BER = 0 nos 4 esquemas) e a BER simulada contra "
           "a teórica.", tam_cab=19, tam_corpo=15)
    cartao(s, X0 + w2 + g, Y_CONTEUDO + 2.2, w2, 1.95,
           "Como cada ponto é medido",
           "Blocos de 1.000.000 de bits até 200 erros ou 20.000.000 de bits. "
           "Abaixo de 10⁻⁷ não se simula: seriam bilhões de bits.",
           tam_cab=19, tam_corpo=15)
    rodape(s, "Eb/N0 de 0 a 14 dB, de 1 em 1 dB, nos 4 esquemas · "
              "python validar.py e python experimentos.py")
    notas(s, "Validação", 45,
          "Antes de medir qualquer coisa, eu conferi. O validar.py roda 27 "
          "verificações, de cada bloco isolado até a cadeia inteira. Sem "
          "ruído, a BER tem que dar zero, e deu nos 4 esquemas. Depois, cada "
          "ponto das curvas transmite blocos de um milhão de bits até juntar "
          "200 erros, o que dá uma incerteza de uns 14 por cento. Abaixo de 10 "
          "a menos 7 eu não simulo, porque seriam bilhões de bits. E a semente "
          "é fixa: qualquer pessoa roda o experimentos.py e obtém exatamente "
          "estes números, em uns 25 segundos.")


def _grafico_ber(s, arquivo):
    # 1354 x 991 px
    imagem(s, RESULTADOS / arquivo, X0 - 0.15, Y_CONTEUDO - 0.15, h=4.5)


def s_ber_ebn0(prs, img, d):
    s = novo_slide(prs, FUNDO_CONTEUDO, img)
    titulo(s, "A simulação cai sobre a teoria", "BER × Eb/N0 nos 4 esquemas")
    _grafico_ber(s, "ber_ebn0.png")
    ordem = sorted(ESQUEMAS, key=lambda e: d["ebn0"][e])
    xr = 8.3
    y = lista_valores(s, xr, Y_CONTEUDO, X0 + LARG - xr,
                      "Eb/N0 para BER = 10⁻⁵",
                      [(e, f"{br(d['ebn0'][e])} dB") for e in ordem])
    cartao(s, xr, y + 0.15, X0 + LARG - xr, 1.35, "Mesma curva",
           "BPSK com NRZ ou Manchester: 9,59 dB nos dois.", tam_cab=17,
           tam_corpo=15)
    rodape(s, "Linhas: teoria · marcadores: simulação · BER = 10⁻⁵ é um bit "
              "errado a cada 100 mil")
    notas(s, "BER × Eb/N0", 70,
          "O resultado principal. No eixo horizontal, o Eb/N0; no vertical, a "
          "BER em escala logarítmica: cada linha de grade é 10 vezes menos "
          "erro. As linhas são a teoria, os marcadores a simulação, e eles "
          "coincidem nos 4 esquemas. A referência usual é BER de 10 a menos 5, "
          "um bit errado a cada cem mil. O BPSK chega lá com 9,59 dB, com NRZ "
          "ou com Manchester: as duas curvas são a mesma. A 16-QAM com NRZ "
          "precisa de 13,43, quase 4 dB a mais. E a 16-QAM com Manchester fica "
          "no meio, com 10,56, um resultado que eu explico daqui a pouco.")


def s_ber_snr(prs, img, d):
    s = novo_slide(prs, FUNDO_CONTEUDO, img)
    titulo(s, "No eixo da SNR, a ordem muda",
           "BER × SNR, o gráfico pedido no enunciado")
    _grafico_ber(s, "ber_snr.png")
    ordem = sorted(ESQUEMAS, key=lambda e: d["snr"][e])
    xr = 8.3
    y = lista_valores(s, xr, Y_CONTEUDO, X0 + LARG - xr,
                      "SNR para BER = 10⁻⁵",
                      [(e, f"{br(d['snr'][e])} dB") for e in ordem])
    cartao(s, xr, y + 0.15, X0 + LARG - xr, 1.6,
           "O Manchester só parece melhor",
           "Cada bit usa 2 símbolos: com a mesma SNR, recebe o dobro de "
           "energia e paga com o dobro da banda.", tam_cab=17, tam_corpo=15)
    rodape(s, "As curvas são as mesmas do slide anterior, deslocadas de "
              "10·log10(η)")
    notas(s, "BER × SNR", 50,
          "O enunciado pede a BER em função da SNR, então aqui está o mesmo "
          "resultado com a SNR no eixo. As curvas se deslocam e a ordem muda: "
          "agora o BPSK com Manchester parece o melhor, 3 dB à frente do NRZ. "
          "Mas é efeito do eixo: cada bit Manchester ocupa dois símbolos, "
          "então, com a mesma energia por símbolo, cada bit recebe o dobro de "
          "energia, pagando com o dobro do tempo e da banda. Por isso a "
          "comparação entre esquemas eu fiz em Eb/N0.")


def s_mensagem(prs, img, d):
    s = novo_slide(prs, FUNDO_CONTEUDO, img)
    titulo(s, "O que chega do outro lado",
           "Mensagem de teste nos 4 esquemas")
    original = d["original"]

    def celula(m, c, db):
        msg, erros = d["mensagens"][((m, c), db)]
        trechos = []
        for recebido, enviado in zip(msg, original):
            errado = recebido != enviado
            op = {"cor": ERRO, "negrito": True} if errado else {}
            if trechos and trechos[-1][1] == op:
                trechos[-1] = (trechos[-1][0] + recebido, op)
            else:
                trechos.append((recebido, op))
        trechos = [(t, dict(op, fonte="Consolas")) for t, op in trechos]
        rot = ("sem erros" if erros == 0 else
               f"{erros} bit errado" if erros == 1 else
               f"{erros} bits errados")
        return [trechos, [(rot, {"tamanho": 12, "cor": MUDO})]]

    linhas = [["Esquema", "Eb/N0 = 2 dB", "Eb/N0 = 6 dB"]]
    for m, c in ESQUEMAS:
        linhas.append([[[(nome(m, c), {"negrito": True})]],
                       celula(m, c, 2), celula(m, c, 6)])
    tabela(s, X0, Y_CONTEUDO - 0.05, [2.45, 4.21, 4.21], linhas, tamanho=13,
           altura_linha=0.8, altura_cab=0.45)
    previsto = metricas.ber_teorica("16qam", "nrz", 6) * len(original) * 8
    _, erros_6 = d["mensagens"][(("16qam", "nrz"), 6)]
    texto(s, X0, 5.95, LARG, 0.5,
          [[("A 10 dB, chega intacta nos 4 esquemas. ", {"negrito": True}),
            (f"A 16-QAM + NRZ a 6 dB tinha previsão de ≈ {previsto:.0f} bits "
             f"errados; foram {erros_6}.", {"cor": TEXTO_2})]], tamanho=16)
    rodape(s, f"\"{original}\": {len(original)} caracteres = "
              f"{len(original) * 8} bits · em laranja, os caracteres que "
              "chegaram errados")
    notas(s, "Mensagem de teste", 50,
          "O que isso significa para quem lê a mensagem. Transmiti \"Redes de "
          "Computadores - UNISINOS 2026\", 296 bits, nos 4 esquemas. Em "
          "laranja estão os caracteres que chegaram errados. A 2 dB, nenhum "
          "esquema dá conta: o texto fica ilegível. A 6 dB, o BPSK já entrega "
          "quase tudo, e a 16-QAM com NRZ ainda erra 9 bits. A 10 dB, os 4 "
          "chegam intactos. E os números batem com a teoria: para a 16-QAM a "
          "6 dB, a BER prevista dava uns 8 bits errados em 296, e foram 9.")


def s_modulacoes(prs, img, d):
    s = novo_slide(prs, FUNDO_CONTEUDO, img)
    titulo(s, "16-QAM: 4 vezes mais bits pelo mesmo Hz",
           "Comparação entre as modulações, com o mesmo código (NRZ)")
    bpsk, qam = d["ebn0"][("bpsk", "nrz")], d["ebn0"][("16qam", "nrz")]
    g = 0.3
    w = (LARG - 2 * g) / 3
    h = 2.0
    for i, e in enumerate((("bpsk", "nrz"), ("16qam", "nrz"))):
        x = X0 if i == 0 else X0 + 2 * (w + g)
        retangulo(s, x, Y_CONTEUDO, w, h, CARTAO, arredondado=True, raio=0.07)
        circulo(s, x + 0.36, Y_CONTEUDO + 0.39, 0.11, COR[e])
        texto(s, x + 0.6, Y_CONTEUDO + 0.2, w - 0.8, 0.4, nome(*e),
              tamanho=18, negrito=True)
        texto(s, x + 0.25, Y_CONTEUDO + 0.75, w - 0.5, 1.2,
              [[(f"{br(d['ebn0'][e])} dB", {"negrito": True, "tamanho": 38})],
               [(f"{br(eta(*e), 0)} bit/s/Hz", {"tamanho": 18,
                                                "cor": TEXTO_2})]])
    x = X0 + w + g
    retangulo(s, x, Y_CONTEUDO, w, h, AZUL, arredondado=True, raio=0.07)
    texto(s, x + 0.25, Y_CONTEUDO + 0.2, w - 0.5, h - 0.3,
          [[(f"+{br(qam - bpsk)} dB", {"negrito": True, "tamanho": 38})],
           [("de Eb/N0 em troca de", {"tamanho": 15, "cor": CLARO})],
           [("4× a eficiência", {"negrito": True, "tamanho": 22})]],
          cor=BRANCO, alinhamento=PP_ALIGN.CENTER)
    w2 = (LARG - 0.27) / 2
    cartao(s, X0, Y_CONTEUDO + 2.3, w2, 1.95, "Por quê: vizinhos mais perto",
           "Com a mesma energia média, os 16 pontos ficam a 0,63 um do outro; "
           "os 2 do BPSK, a 2. Basta menos ruído para trocar de símbolo.",
           tam_cab=19, tam_corpo=15)
    cartao(s, X0 + w2 + 0.27, Y_CONTEUDO + 2.3, w2, 1.95,
           "Potência × banda",
           "BPSK: pouca potência e banda sobrando (satélites, sondas). "
           "16-QAM: sinal bom e banda cara (Wi-Fi, 4G e 5G).",
           tam_cab=19, tam_corpo=15)
    snr_b, snr_q = d["snr"][("bpsk", "nrz")], d["snr"][("16qam", "nrz")]
    rodape(s, f"Eb/N0 para BER = 10⁻⁵ · em SNR, a diferença é de "
              f"{br(snr_q - snr_b)} dB, porque cada símbolo da 16-QAM leva "
              "4 bits")
    notas(s, "BPSK × 16-QAM", 60,
          "Primeira comparação pedida: as modulações, com o mesmo código, o "
          f"NRZ. A 16-QAM precisa de {br(qam - bpsk)} dB a mais que o BPSK, "
          "mas transmite 4 "
          "vezes mais bits no mesmo Hz de banda. O porquê está na "
          "constelação: com a mesma energia média, os 16 pontos ficam muito "
          "mais apertados, a 0,63 um do outro, contra 2 no BPSK. Então basta "
          "menos ruído para confundir um símbolo com o vizinho. É a troca "
          "entre potência e banda. O BPSK serve onde a potência é pouca e a "
          "banda sobra, como em satélites. A 16-QAM, onde o sinal é bom e a "
          "banda é cara: Wi-Fi, 4G e 5G trocam de modulação conforme a "
          "qualidade do sinal.")


def s_manchester(prs, img, d):
    s = novo_slide(prs, FUNDO_CONTEUDO, img)
    titulo(s, "Manchester: mesma BER, o dobro da banda",
           "Impacto da codificação de canal no BPSK")
    nrz, man = ("bpsk", "nrz"), ("bpsk", "manchester")
    linhas = [["", "NRZ", "Manchester"],
              ["Chips por bit", "1", "2"],
              ["Eficiência", f"{br(eta(*nrz), 0)} bit/s/Hz",
               f"{br(eta(*man), 1)} bit/s/Hz"],
              ["Eb/N0 para 10⁻⁵", f"{br(d['ebn0'][nrz])} dB",
               f"{br(d['ebn0'][man])} dB"]]
    tabela(s, X0, Y_CONTEUDO, [2.3, 1.55, 1.75], linhas, tamanho=17,
           altura_linha=0.5,
           alinhamentos=[PP_ALIGN.LEFT, PP_ALIGN.CENTER, PP_ALIGN.CENTER])
    x = X0 + 5.87
    cartao(s, x, Y_CONTEUDO, X0 + LARG - x, 2.0, "Por que a BER é a mesma",
           "Os 2 chips de cada bit têm sinais opostos, e o receptor compara "
           "os dois: é um símbolo BPSK com a energia dos dois somada.",
           tam_cab=19, tam_corpo=15)
    itens = [
        ("Sincronismo", "Uma transição por bit: o receptor recupera o relógio "
         "mesmo em longas sequências iguais."),
        ("Nível médio zero", "Sem componente DC, o sinal passa por "
         "transformadores e acopladores."),
        ("Detecção, não correção", "Pares 00 e 11 denunciam ruído: 41 pares "
         "inválidos para 5 bits errados a 2 dB."),
    ]
    g = 0.27
    w = (LARG - 2 * g) / 3
    for i, (cab, corpo) in enumerate(itens):
        cartao(s, X0 + i * (w + g), Y_CONTEUDO + 2.3, w, 1.95, cab, corpo,
               tam_cab=18, tam_corpo=15)
    rodape(s, "Esses ganhos não aparecem na BER: o simulador supõe relógio "
              "perfeito. Para corrigir erros, seria preciso um FEC")
    notas(s, "NRZ × Manchester", 60,
          "Segunda comparação: o código de linha. No BPSK, o Manchester não "
          "muda a BER em Eb/N0: 9,59 dB nos dois. Os dois chips de cada bit "
          "têm sinais opostos, e comparar os dois é o mesmo que receber um "
          "único símbolo com a energia somada. O que muda é a banda: o dobro "
          "de chips, metade da eficiência. Então o que o Manchester compra? "
          "Coisas que a BER deste simulador não mede, porque ele supõe relógio "
          "perfeito: a transição em todo bit, que deixa o receptor recuperar o "
          "relógio; o nível médio zero; e a detecção, porque os pares 0 0 e "
          "1 1 não existem e denunciam ruído. Mas é só um alarme: a 2 dB, "
          "foram 41 pares inválidos para 5 bits errados. Ele não corrige "
          "nada; para isso seria preciso um código corretor de erros.")


def s_quatro_pontos(prs, img, d):
    s = novo_slide(prs, FUNDO_CONTEUDO, img)
    titulo(s, "Um resultado que eu não previ",
           "16-QAM + Manchester usa só 4 dos 16 pontos")
    # os dois paineis da direita de constelacoes.png (2413 x 978 px)
    png = recorte(RESULTADOS / "constelacoes.png", (845, 95, 2413, 978))
    imagem(s, png, X0 - 0.1, Y_CONTEUDO, w=6.45)
    texto(s, X0, 5.75, 6.3, 0.35, "Símbolos recebidos com Eb/N0 = 10 dB; "
          "× = símbolo ideal", tamanho=13, cor=MUDO)
    xr = 8.6
    wr = X0 + LARG - xr
    blocos = [
        ("Os 2 chips caem no mesmo eixo", "Bit 1 = 01 → nível −1. "
         "Bit 0 = 10 → nível +3. Os níveis −3 e +1 nunca aparecem."),
        ("4 pontos, 2 bits por símbolo",
         f"BER = Q(√(1,6·Eb/N0)): {br(d['ebn0'][('16qam', 'manchester')])} dB "
         "para 10⁻⁵, confirmado pela simulação."),
        ("0,97 dB de desperdício", "O centro dos pontos não está na origem: "
         "20 % da energia vai nesse deslocamento. Uma QPSK teria a mesma "
         "eficiência com 9,59 dB."),
    ]
    y = Y_CONTEUDO
    for cab, corpo in blocos:
        texto(s, xr, y, wr, 1.35,
              [[(cab, {"negrito": True, "tamanho": 18})],
               [(corpo, {"tamanho": 15, "cor": TEXTO_2})]], espaco_depois=4)
        y += 1.4
    rodape(s, "Lição: código de linha e modulação precisam ser escolhidos "
              "juntos")
    notas(s, "16-QAM + Manchester", 70,
          "Este foi o resultado que eu não previ. Na 16-QAM com Manchester, os "
          "dois chips de um bit caem sempre no mesmo eixo. Como o Manchester "
          "só produz 0 1 e 1 0, só aparecem os níveis menos 1 e mais 3, e a "
          "constelação de 16 pontos encolhe para 4, como se vê à direita. "
          "Vira um esquema de 2 bits por símbolo, com 10,56 dB. E por que ele "
          "perde quase 1 dB para o BPSK? Olhem o centro dos 4 pontos: não "
          "está na origem. 20 por cento da energia de cada símbolo vai nesse "
          "deslocamento, que não carrega informação. 10 log de 1 sobre 0,8 dá "
          "0,97 dB, exatamente a diferença. Uma QPSK teria os mesmos 2 bits "
          "por símbolo sem esse desperdício. A lição é que código de linha e "
          "modulação têm que ser escolhidos juntos.")


def s_impacto(prs, img):
    s = novo_slide(prs, FUNDO_CONTEUDO, img)
    titulo(s, "BER pequena não é erro pequeno", "Impacto da BER na comunicação")
    linhas = [["BER", "Caractere errado", "Em média"]]
    for exp in (2, 3, 5):
        p = 1 - (1 - 10 ** -exp) ** 8
        casas = 1 if p >= 1e-3 else 3
        linhas.append([f"10⁻{'⁰¹²³⁴⁵⁶⁷⁸⁹'[exp]}", f"{br(p * 100, casas)} %",
                       f"1 a cada {br(round(1 / p), 0)} caracteres"])
    tabela(s, X0, Y_CONTEUDO, [1.4, 2.4, 3.0], linhas, tamanho=17,
           altura_linha=0.55)
    pacote = 1 - (1 - 1e-5) ** 12000
    x = X0 + 7.1
    estatistica(s, x, Y_CONTEUDO, X0 + LARG - x, 2.2,
                f"{br(pacote * 100, 0)} %",
                "dos pacotes Ethernet de 1.500 bytes chegam corrompidos com "
                "BER = 10⁻⁵", fundo=AZUL, cor_num=BRANCO, cor_rot=CLARO,
                tam_num=48)
    w2 = (LARG - 0.27) / 2
    cartao(s, X0, Y_CONTEUDO + 2.55, w2, 1.7, "Na mensagem de teste",
           "A 2 dB (BER entre 3·10⁻² e 1·10⁻¹), o texto fica ilegível; a "
           "10 dB, chega intacto.", tam_cab=19, tam_corpo=15)
    cartao(s, X0 + w2 + 0.27, Y_CONTEUDO + 2.55, w2, 1.7,
           "Por isso, além da modulação",
           "Enlaces reais usam CRC para detectar e códigos corretores (FEC) "
           "para corrigir erros.", tam_cab=19, tam_corpo=15)
    rodape(s, "Um caractere de 8 bits se perde se qualquer bit errar: "
              "P = 1 − (1 − BER)⁸; um pacote de 12.000 bits, idem")
    notas(s, "Impacto da BER", 45,
          "O impacto da BER. Um caractere tem 8 bits e se perde se qualquer "
          "um errar. Com BER de 10 a menos 2, um caractere a cada 13 chega "
          "errado: é a mensagem ilegível de 2 dB. Com 10 a menos 5, um a cada "
          "12.500. Parece ótimo, mas um pacote Ethernet de 1.500 bytes tem 12 "
          "mil bits: com essa mesma BER, 11 por cento dos pacotes chegariam "
          "corrompidos e teriam que ser retransmitidos. Por isso enlaces reais "
          "usam CRC para detectar erros e códigos corretores para consertá-los, "
          "além da modulação.")


def s_shannon(prs, img, d):
    s = novo_slide(prs, FUNDO_CONTEUDO, img)
    titulo(s, "Todos longe do limite de Shannon",
           "Eficiência espectral × Eb/N0 necessário para BER = 10⁻⁵")
    # 1574 x 965 px
    imagem(s, RESULTADOS / "eficiencia_shannon.png", X0 - 0.15,
           Y_CONTEUDO - 0.05, w=6.75)
    dist = {e: d["ebn0"][e] - d["shannon"][e] for e in ESQUEMAS}
    ordem = sorted(ESQUEMAS, key=lambda e: -dist[e])
    xr = 8.75
    y = lista_valores(s, xr, Y_CONTEUDO, X0 + LARG - xr,
                      "Distância ao limite",
                      [(e, f"{br(dist[e])} dB") for e in ordem])
    texto(s, xr, y + 0.15, X0 + LARG - xr, 1.6,
          [[("Sem código corretor, ", {"negrito": True}),
            ("nenhum esquema chega perto. A 16-QAM + NRZ é a mais próxima: "
             "ordem alta aproveita melhor um canal bom.", {"cor": TEXTO_2})]],
          tamanho=15)
    rodape(s, "Limite de Shannon: Eb/N0 ≥ (2^η − 1)/η · eficiência com "
              "1 símbolo/s por Hz (Nyquist)")
    notas(s, "Eficiência e Shannon", 50,
          "E a eficiência. No eixo vertical, quantos bits por segundo cada Hz "
          "de banda carrega; no horizontal, o Eb/N0 que cada esquema precisa. "
          "A linha tracejada é o limite de Shannon: à esquerda dela, nenhum "
          "sistema funciona sem erro. Todos os meus esquemas ficam entre 7,7 e "
          "10,4 dB longe do limite, porque nenhum usa código corretor. O mais "
          "próximo é a 16-QAM com NRZ: modulações de ordem alta aproveitam "
          "melhor um canal bom. O mais distante é o BPSK com Manchester: gasta "
          "a mesma energia que o NRZ e entrega metade da eficiência.")


def s_metodo(prs, img):
    s = novo_slide(prs, FUNDO_CONTEUDO, img)
    titulo(s, "O que os testes corrigiram", "Método e uso de IA")
    itens = [
        ("Previsto: 4 combinações \"limpas\"",
         "Com Manchester, a 16-QAM usa só 4 dos 16 pontos. Os testes "
         "mostraram isso, e virou a análise dos 0,97 dB."),
        ("Pares inválidos não são bits errados",
         "41 pares para 5 bits errados a 2 dB. A contagem passou a ser "
         "apresentada como alarme de canal ruim."),
        ("Como cada número foi conferido",
         "Simulação contra a fórmula teórica em todos os pontos, 27 "
         "verificações e semente fixa: qualquer pessoa reproduz."),
        ("Uso de IA",
         "Claude Code no planejamento, no código e nos textos, com previsões "
         "antes de rodar. A execução oficial é minha."),
    ]
    w, h, g = 5.3, 1.95, 0.27
    for i, (cab, corpo) in enumerate(itens):
        cartao(s, X0 + (i % 2) * (w + g), Y_CONTEUDO + (i // 2) * (h + g),
               w, h, cab, corpo, tam_cab=19, tam_corpo=16)
    rodape(s, "Detalhes na seção 10 do relatório técnico (docs/relatorio.md)")
    notas(s, "Método e IA", 40,
          "Sobre o método. Usei IA, o Claude Code, no planejamento, no código "
          "e nos textos, sempre com uma previsão antes de rodar. Duas "
          "previsões foram corrigidas pelos testes: as quatro combinações não "
          "eram todas limpas, porque a 16-QAM com Manchester usava só 4 "
          "pontos; e a contagem de pares inválidos não mede erros. Todo número "
          "foi conferido contra a teoria e pelo validar.py, e a execução "
          "oficial é minha, com semente fixa.")


def s_conclusao(prs, img, d):
    s = novo_slide(prs, FUNDO_DESTAQUE, img)
    titulo(s, "Potência, banda e sincronismo",
           "Conclusão: qual esquema para qual enlace", claro=True)
    linhas = [
        ["Se o enlace tem…", "Escolha", "Por quê"],
        ["Pouca potência", "BPSK + NRZ",
         f"menor Eb/N0 ({br(d['ebn0'][('bpsk', 'nrz')])} dB)"],
        ["Banda escassa e boa SNR", "16-QAM + NRZ",
         "4 bit/s/Hz, o mais perto de Shannon"],
        ["Relógio tirado do sinal", "BPSK + Manchester",
         "mesma BER, ao custo do dobro da banda"],
    ]
    tabela(s, X0, Y_CONTEUDO, [3.25, 2.75, 4.87], linhas, tamanho=17,
           altura_linha=0.5, cab_fundo=CARTAO, cab_texto=AZUL,
           corpo_fundo=BRANCO)
    extra = d["ebn0"][("16qam", "nrz")] - d["ebn0"][("bpsk", "nrz")]
    blocos = [
        ("A modulação troca potência por banda",
         f"16-QAM: 4× os bits por Hz, por {br(extra)} dB a mais de Eb/N0."),
        ("O código de linha troca banda por sinal",
         "Manchester: mesma BER e o dobro da banda, em troca de sincronismo e "
         "nível médio zero."),
    ]
    for i, (cab, corpo) in enumerate(blocos):
        texto(s, X0 + i * 5.57, 4.45, 5.3, 1.8,
              [[(cab, {"negrito": True, "tamanho": 20})],
               [(corpo, {"tamanho": 16})]], cor=BRANCO, espaco_depois=6)
    rodape(s, "Simulação e teoria coincidem nos 4 esquemas, de 0 a 14 dB",
           claro=True)
    notas(s, "Conclusão", 45,
          "Para fechar. A modulação troca potência por banda: a 16-QAM dá 4 "
          f"vezes os bits por Hz por {br(extra)} dB a mais. O código de linha "
          "troca "
          "banda por propriedades do sinal: o Manchester não muda a BER e "
          "dobra a banda, em troca de sincronismo. Então a escolha depende do "
          "enlace: com pouca potência, BPSK com NRZ; com banda escassa e sinal "
          "bom, 16-QAM; se o receptor precisa tirar o relógio do próprio "
          "sinal, Manchester. E em todos os casos, simulação e teoria "
          "bateram.")


def s_fim(prs, img):
    s = novo_slide(prs, FUNDO_FIM, img)
    texto(s, 6.53, 2.75, 6.2, 1.2, "Perguntas?", tamanho=66, negrito=True)
    texto(s, 6.53, 4.05, 6.2, 1.1,
          [[("python sistema.py \"Ola\" --modulacao 16qam --ebn0 6",
             {"fonte": "Consolas", "tamanho": 15, "negrito": True})],
           [("github.com/mmilanezi/Redes-de-computadores_Trab-2",
             {"tamanho": 16, "cor": TEXTO_2})]], espaco_depois=6)
    notas(s, "Perguntas", 10,
          "Obrigado. O código, o relatório e os resultados estão no GitHub, e "
          "o README explica como rodar. Se houver tempo, mostro ao vivo uma "
          "transmissão com o sistema.py.")


# ===========================================================================

def gravar_roteiro() -> None:
    total = sum(seg for _t, seg, _f in ROTEIRO_SLIDES)
    partes = [
        "# Roteiro da apresentação – Trabalho II",
        "",
        "Gerado por `scripts/gerar_apresentacao.py` a partir das notas dos "
        "slides (edite lá e gere de novo).",
        f"Tempo previsto: **{total // 60} min {total % 60:02d} s** para 15 min "
        "de apresentação. O tempo ao lado de cada slide é a meta do ensaio; "
        "o acumulado ajuda a saber se está adiantado ou atrasado.",
        "",
    ]
    acumulado = 0
    for i, (t, seg, fala) in enumerate(ROTEIRO_SLIDES, 1):
        acumulado += seg
        partes += [f"## {i}. {t} · {seg} s (acumulado {acumulado // 60}:"
                   f"{acumulado % 60:02d})", "", fala, ""]
    ROTEIRO.write_text("\n".join(partes), encoding="utf-8")


def main() -> None:
    d = dados()
    with zipfile.ZipFile(MODELO) as z:
        imagens = {n: z.read(n) for n in (FUNDO_CAPA, FUNDO_CONTEUDO,
                                          FUNDO_DESTAQUE, FUNDO_FIM)}
    imagens[FUNDO_CONTEUDO] = limpar_fundo_conteudo(imagens[FUNDO_CONTEUDO])

    prs = Presentation(str(MODELO))
    n_modelo = len(prs.slides)

    s_capa(prs, imagens)
    s_cadeia(prs, imagens)
    s_bits_chips(prs, imagens)
    s_modulacao(prs, imagens)
    s_canal(prs, imagens)
    s_validacao(prs, imagens)
    s_ber_ebn0(prs, imagens, d)
    s_ber_snr(prs, imagens, d)
    s_mensagem(prs, imagens, d)
    s_modulacoes(prs, imagens, d)
    s_manchester(prs, imagens, d)
    s_quatro_pontos(prs, imagens, d)
    s_impacto(prs, imagens)
    s_shannon(prs, imagens, d)
    s_metodo(prs, imagens)
    s_conclusao(prs, imagens, d)
    s_fim(prs, imagens)

    # remove os slides de exemplo do modelo; as partes sem referencia nao
    # sao gravadas pelo python-pptx
    lista = prs.slides._sldIdLst
    for sld in list(lista)[:n_modelo]:
        prs.part.drop_rel(sld.rId)
        lista.remove(sld)

    prs.save(str(SAIDA))
    gravar_roteiro()
    total = sum(seg for _t, seg, _f in ROTEIRO_SLIDES)
    print(f"{SAIDA.name}: {len(prs.slides)} slides, fala prevista de "
          f"{total // 60} min {total % 60:02d} s")
    print(f"{ROTEIRO.name}: roteiro de ensaio")


if __name__ == "__main__":
    main()
