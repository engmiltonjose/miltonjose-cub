"""Sinduscon-RS — https://sinduscon-rs.com.br/cub-rs/

- "Série Histórica – Valor" (PDF, uma página por ano desde 2007, meses nas colunas): totais dos
  19 projetos-padrão, sem desoneração. Um único arquivo traz toda a série.
- "Preços e Custos da Construção" do mês (PDF, pág. 2): composição (materiais, mão de obra,
  despesas administrativas, equipamentos) do último mês.
O Sinduscon-RS não publica CUB desonerado.
"""
import re, pymupdf
from comum_site import Site
from cub_comum import codigo, num

UF = 'RS'
FONTE_ID = 'sinduscon-rs'
FONTE = {'nome': 'Sinduscon-RS', 'origem': 'https://sinduscon-rs.com.br/cub-rs/ (Série Histórica – Valor)',
         'principal': True}
BASE = 'https://sinduscon-rs.com.br'
PRIMEIRO_MES = '2007-01'
MESES = ['JAN', 'FEV', 'MAR', 'ABR', 'MAI', 'JUN', 'JUL', 'AGO', 'SET', 'OUT', 'NOV', 'DEZ']
RE_VAL = re.compile(r'^\d{1,2}\.\d{3},\d{2,3}$|^\d{1,3},\d{1,3}$')
val = lambda s: round(num(s), 2)
RE_COD = re.compile(r'\b(R ?1|PP ?4|R ?8|R ?16|CAL ?8|CSL ?8|CSL ?16)-([BNA])\b|\b(PIS|RP1Q|GI)\b')


def linhas(pagina):
    """Agrupa as palavras por linha (y) → [(y, [(x, texto)])]."""
    ws = sorted(pagina.get_text('words'), key=lambda w: ((w[1] + w[3]) / 2, w[0]))
    out = []
    for w in ws:
        y = (w[1] + w[3]) / 2
        if out and abs(out[-1][0] - y) < 3:
            out[-1][1].append((w[0], w[4]))
        else:
            out.append((y, [(w[0], w[4])]))
    return out


def cod_da_linha(txt):
    m = RE_COD.search(txt)
    if not m:
        return None
    return codigo(m.group(3)) if m.group(3) else codigo(m.group(1).replace(' ', ''), m.group(2))


def ler_serie(conteudo):
    """{AAAA-MM: {proj: {'total': v}}}"""
    out = {}
    for p in pymupdf.open(stream=conteudo, filetype='pdf'):
        t = p.get_text()
        m = re.search(r'\b(20[0-2]\d)\b', t)
        if not m:
            continue
        ano = m.group(1)
        cols = {}
        for y, ws in linhas(p):
            nomes = [w for w in ws if w[1] in MESES]
            if len(nomes) >= 10:
                cols = {MESES.index(tx) + 1: x for x, tx in nomes}
                break
        if not cols:
            continue
        x0 = min(cols.values()) - 25
        for y, ws in linhas(p):
            esq = ' '.join(tx for x, tx in ws if x < x0)
            cod = cod_da_linha(esq)
            if not cod:
                continue
            for x, tx in ws:
                if x >= x0 and RE_VAL.match(tx):
                    mes = min(cols, key=lambda k: abs(cols[k] - x))
                    out.setdefault(f'{ano}-{mes:02d}', {})[cod] = {'total': val(tx)}
    return out


def ler_composicao(conteudo):
    """Pág. 'Composição CUB/RS do mês' → (AAAA-MM, {proj: {total, mat, mo, adm, eq}})."""
    from comum_site import mes_de_texto
    for p in pymupdf.open(stream=conteudo, filetype='pdf'):
        t = p.get_text()
        if 'Composição CUB/RS' not in t:
            continue
        mes = mes_de_texto(re.sub(r'\s+', ' ', t[t.find('Composição CUB/RS'):][:120]))
        out = {}
        for y, ws in linhas(p):
            cod = cod_da_linha(' '.join(tx for x, tx in ws))
            vals = [val(tx) for x, tx in ws if RE_VAL.match(tx)]
            if cod and len(vals) >= 5:
                out[cod] = dict(zip(['total', 'mat', 'mo', 'adm', 'eq'], vals[:5]))
        return mes, out
    return None, {}


def coletar(desejados, log=print):
    site = Site()
    h = site.get(f'{BASE}/cub-rs/').text
    links = re.findall(r'href="([^"]*/uploads/(\d{4})/(\d{2})/[^"]*\.pdf)"', h)
    serie = sorted({(a, m, u) for u, a, m in links if re.search(r'(?i)SERI[EA]?-?HIST[^/]*VALOR', u)})
    precos = sorted({(a, m, u) for u, a, m in links if re.search(r'(?i)PRECOS?-E-CUSTOS', u)})
    if not serie:
        log('RS: link da Série Histórica – Valor não achado')
        return
    url = serie[-1][2]
    url = url if url.startswith('http') else BASE + url
    dados = ler_serie(site.get(url).content)
    comp_mes, comp = (None, {})
    if precos:
        u = precos[-1][2]
        comp_mes, comp = ler_composicao(site.get(u if u.startswith('http') else BASE + u).content)
    for mes, vals in sorted(dados.items()):
        if (mes, 'sem') not in desejados:
            continue
        if mes == comp_mes:
            for k, c in comp.items():
                if k in vals and abs(c['total'] - vals[k]['total']) < 0.02:
                    vals[k] = c
        yield mes, 'sem', vals, {'arquivo': url}
