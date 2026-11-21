"""Sinduscon-RO — http://sindusconro.com.br/home/?page_id=41

Duas listagens de arquivos (WP-Filebase), uma onerada e uma desonerada, com linhas de ano
seguidas das linhas de mês ("10-outubro") e o link ?wpfb_dl=N do PDF. O mês é conferido no
próprio PDF ("MÊS: 10 ANO: 2026").
"""
import re, html, pymupdf
from comum_site import Site
import pdf_posicional

UF = 'RO'
FONTE_ID = 'sinduscon-ro'
FONTE = {'nome': 'Sinduscon-RO', 'origem': 'http://sindusconro.com.br/home/?page_id=41', 'principal': True}
PRIMEIRO_MES = '2015-10'
PAGINAS = {'sem': 'http://sindusconro.com.br/home/?page_id=378', 'com': 'http://sindusconro.com.br/home/?page_id=340'}


def catalogo(site):
    out = {}
    for des, url in PAGINAS.items():
        h = site.get(url).text
        tb = re.search(r'<table.*?</table>', h, re.S)
        if not tb:
            continue
        ano = None
        for r in re.findall(r'<tr[^>]*>(.*?)</tr>', tb.group(0), re.S):
            txt = html.unescape(re.sub(r'<[^>]+>', ' ', r)).strip()
            if re.fullmatch(r'20\d\d', txt):
                ano = txt
                continue
            m = re.match(r'(\d{2})\s*-', txt)
            link = re.search(r'href="([^"]*wpfb_dl=\d+)"', r)
            if ano and m and link:
                out.setdefault((f'{ano}-{m.group(1)}', des), html.unescape(link.group(1)))
    return out


def coletar(desejados, log=print):
    site = Site()
    for (mes, des), u in sorted(catalogo(site).items()):
        if (mes, des) not in desejados:
            continue
        r = site.get(u)
        if r.content[:4] != b'%PDF':
            log(f'RO {mes} {des}: arquivo não é PDF')
            continue
        t = ' '.join(p.get_text() for p in pymupdf.open(stream=r.content, filetype='pdf'))
        m = re.search(r'M[ÊE]S:\s*(\d{1,2})\s+ANO:\s*(\d{4})', t)
        if m and f'{m.group(2)}-{int(m.group(1)):02d}' != mes:
            log(f'RO {mes} {des}: PDF diz {m.group(2)}-{int(m.group(1)):02d}; ignorado')
            continue
        yield mes, des, pdf_posicional.ler(r.content), {'arquivo': u}
