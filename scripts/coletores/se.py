"""Sinduscon-SE — https://sinduscon-se.com.br/cub

A página traz o histórico (tabelas "historico-table"): para cada mês, PDF normal e desonerado.
"""
import re, html
from comum_site import Site, mes_de_texto
import pdf_posicional

UF = 'SE'
FONTE_ID = 'sinduscon-se'
FONTE = {'nome': 'Sinduscon-SE', 'origem': 'https://sinduscon-se.com.br/cub', 'principal': True}
PRIMEIRO_MES = '2015-10'


def catalogo(site):
    h = site.get('https://sinduscon-se.com.br/cub').text
    out = {}
    for tr in re.findall(r'<tr[^>]*>(.*?)</tr>', h, re.S):
        txt = html.unescape(re.sub(r'<[^>]+>', ' ', tr))
        mes = mes_de_texto(txt)
        if not mes:
            continue
        for u in re.findall(r'href="([^"]+\.pdf)"', tr):
            des = 'com' if re.search(r'(?i)deson', u.rsplit('/', 1)[-1]) else 'sem'
            out.setdefault((mes, des), u)
    return out


N = r'(\d{1,2}\.\d{3},\d{2}|\d{1,3},\d{2})'
ORDEM = {('Residenciais', 'B'): ['R-1', 'PP-4', 'R-8', 'PIS'], ('Residenciais', 'N'): ['R-1', 'PP-4', 'R-8', 'R-16'],
         ('Residenciais', 'A'): ['R-1', 'R-8', 'R-16'], ('Comerciais', 'N'): ['CAL-8', 'CSL-8', 'CSL-16'],
         ('Comerciais', 'A'): ['CAL-8', 'CSL-8', 'CSL-16']}


def ler_composicao(conteudo):
    """Blocos 'Item <códigos> Material … Mão-de-Obra … Desp. Admin. … Equipamento … [Total] …'."""
    import pymupdf
    from cub_comum import codigo
    t = re.sub(r'\s+', ' ', ' '.join(p.get_text() for p in pymupdf.open(stream=conteudo, filetype='pdf')))
    out = {}
    blocos = list(re.finditer(r'Item ((?:[A-Z]{1,3}-?\d{0,2}Q?\d? )+)Material ', t))
    for k, b in enumerate(blocos):
        cods = b.group(1).split()
        antes = t[blocos[k - 1].end() if k else 0:b.start()]
        mp = re.findall(r'(Residenciais|Comerciais)\s*-\s*(Baixo|Normal|Alto)', antes)
        pad = {'Baixo': 'B', 'Normal': 'N', 'Alto': 'A'}[mp[-1][1]] if mp else 'B'
        fim_bloco = blocos[k + 1].start() if k + 1 < len(blocos) else len(t)
        trecho = 'Material ' + t[b.end():fim_bloco]
        # o PDF às vezes omite um código no cabeçalho (ex.: PP-4 no Normal desonerado):
        # se a linha Material tem mais valores que códigos, usa a ordem padrão do bloco
        n_mat = len(re.findall(N, trecho[:trecho.find('Mão-de-Obra')]))
        tipo = mp[-1][0] if mp else 'Residenciais'
        padrao_bloco = ORDEM.get((tipo, pad)) if not any('GI' in c or 'Q' in c for c in cods) else ['RP1Q', 'GI']
        if n_mat > len(cods) and padrao_bloco and len(padrao_bloco) == n_mat:
            cods = padrao_bloco
        n = len(cods)
        linhas_ = {}
        for rot, chave in (('Material', 'mat'), ('Mão-de-Obra', 'mo'), ('Desp. Admin.', 'adm'),
                           ('Equipamento', 'eq'), ('Total', 'total')):
            i = trecho.find(rot)
            if i >= 0:
                linhas_[chave] = re.findall(N, trecho[i + len(rot):])[:n]
        if 'total' not in linhas_ and 'eq' in linhas_:
            i = trecho.find('Equipamento')
            linhas_['total'] = re.findall(N, trecho[i:])[n:2 * n]
        if any(len(linhas_.get(c, [])) < n for c in ('mat', 'mo', 'adm', 'eq', 'total')):
            continue
        nums = sum((linhas_[c] for c in ('mat', 'mo', 'adm', 'eq', 'total')), [])
        f = lambda s: float(s.replace('.', '').replace(',', '.'))
        for i, c in enumerate(cods):
            c = 'RP1Q' if c.upper() in ('RPQ1', 'RP1Q') else c
            cod = codigo(c) or codigo(c, pad)
            if cod:
                out[cod] = {'mat': f(nums[i]), 'mo': f(nums[n + i]), 'adm': f(nums[2 * n + i]),
                            'eq': f(nums[3 * n + i]), 'total': f(nums[4 * n + i])}
    return out


def coletar(desejados, log=print):
    site = Site()
    for (mes, des), u in sorted(catalogo(site).items()):
        if (mes, des) not in desejados:
            continue
        r = site.get(u)
        if r.content[:4] != b'%PDF':
            log(f'SE {mes} {des}: arquivo não é PDF')
            continue
        vals = ler_composicao(r.content) or pdf_posicional.ler(r.content)
        yield mes, des, vals, {'arquivo': u}
