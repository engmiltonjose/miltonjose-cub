"""Leitor genérico de tabelas do CUB em PDF diagramado (colunas por padrão Baixo/Normal/Alto).

Para cada código de projeto (R-1, PP-4, R-8, R-16, PIS, CAL-8, CSL-8, CSL-16, RP1Q, GI) pega o
primeiro valor em R$/m² à direita na mesma linha; o padrão (B/N/A) vem do cabeçalho "Padrão X"
mais próximo acima, na coluna mais próxima.
"""
import re, pymupdf
from cub_comum import codigo, num

RE_COD = re.compile(r'^(R-?1|R-?8|R-?16|PP-?4|PIS|CAL-?8|CSL-?8|CSL-?16|RP1Q|GI)(-[BNA])?$', re.I)
RE_VAL = re.compile(r'^\d{1,2}\.\d{3},\d{2}$|^\d{3},\d{2}$')
PADROES = {'baixo': 'B', 'normal': 'N', 'alto': 'A'}


def palavras(conteudo):
    """(página, x, y, texto), juntando códigos partidos: 'CAL' '-' '8' → 'CAL-8'; 'R' '8-N' → 'R8-N'."""
    doc = pymupdf.open(stream=conteudo, filetype='pdf')
    for n, p in enumerate(doc):
        ws = sorted(p.get_text('words'), key=lambda w: (round((w[1] + w[3]) / 2), w[0]))
        i = 0
        while i < len(ws):
            w = ws[i]
            t, y = w[4], (w[1] + w[3]) / 2
            if t.upper() in ('R', 'PP', 'CAL', 'CSL'):
                junta, j = t, i + 1
                while j < len(ws) and j <= i + 2 and abs((ws[j][1] + ws[j][3]) / 2 - y) < 3 and re.fullmatch(r'[-–]|\d{1,2}(-[BNA])?', ws[j][4]):
                    junta += ws[j][4].replace('–', '-')
                    j += 1
                    if re.search(r'\d', junta):
                        break
                if re.search(r'\d', junta):
                    yield n, w[0], y, junta
                    i = j
                    continue
            yield n, w[0], y, t
            i += 1


def ler(conteudo, paginas=None):
    ws = [w for w in palavras(conteudo) if paginas is None or w[0] in paginas]
    cabec = [(pg, x, y, PADROES[t.lower()]) for pg, x, y, t in ws if t.lower() in PADROES]
    out = {}
    for pg, x, y, t in ws:
        m = RE_COD.match(t)
        if not m:
            continue
        base = m.group(1)
        if m.group(2):
            cod = codigo(base + m.group(2))
        elif base.upper() in ('PIS', 'RP1Q', 'GI'):
            cod = codigo(base)
        else:
            acima = [c for c in cabec if c[0] == pg and c[2] < y - 2]
            if not acima:
                continue
            ylin = max(c[2] for c in acima)
            linha = [c for c in acima if abs(c[2] - ylin) < 4]
            pad = min(linha, key=lambda c: abs(c[1] - x))[3]
            cod = codigo(base, pad)
        if not cod or cod in out:
            continue
        dir_ = sorted((w for w in ws if w[0] == pg and abs(w[2] - y) < 3 and x < w[1] < x + 140 and RE_VAL.match(w[3])),
                      key=lambda w: w[1])
        if dir_:
            out[cod] = {'total': num(dir_[0][3])}
    return out
