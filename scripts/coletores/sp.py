"""SindusCon-SP — https://sindusconsp.com.br/servicos/cub/

Cada mês é uma categoria do Download Manager (/downloads/<slug>/) com o "Boletim Econômico"
sem e com desoneração (PDF). O boletim traz os 19 projetos-padrão e a composição do R8-N.
"""
import re, html, requests
from comum_site import Site, mes_de_texto
import pdf_posicional

UF = 'SP'
FONTE_ID = 'sinduscon-sp'
FONTE = {'nome': 'SindusCon-SP', 'origem': 'https://sindusconsp.com.br/servicos/cub/ (Boletim Econômico)',
         'principal': True}
BASE = 'https://sindusconsp.com.br'


def composicao_r8n(conteudo):
    """Quadro 'padrão R8-N': mão de obra, material, despesas administrativas, total."""
    import pymupdf
    t = ' '.join(p.get_text() for p in pymupdf.open(stream=conteudo, filetype='pdf'))
    t = re.sub(r'\s+', ' ', t)
    m = re.search(r'padrão R8-N.{0,120}?Mão-de-obra.{0,40}?([\d.]+,\d{2}).{0,40}?Material\s+([\d.]+,\d{2}).{0,40}?'
                  r'Despesas Administrativas\s+([\d.]+,\d{2}).{0,40}?Total\s+([\d.]+,\d{2})', t)
    if not m:
        return None
    f = lambda s: float(s.replace('.', '').replace(',', '.'))
    return {'mo': f(m.group(1)), 'mat': f(m.group(2)), 'adm': f(m.group(3)), 'eq': 0.0, 'total': f(m.group(4))}


def catalogo(site, desejados=None):
    """{(mes, des): url_da_pagina_do_boletim}"""
    h = site.get(f'{BASE}/servicos/cub/').text
    cats = sorted(set(re.findall(r'href="(https://sindusconsp\.com\.br/downloads/\d{2}-[a-z\-0-9]+/)"', h)))
    out = {}
    ler_feed(site, cats, out)
    # meses que a listagem não mostra: tenta os endereços no padrão usual
    import datetime
    from cub_comum import MESES_PT
    hoje = datetime.date.today()
    faltam = []
    for ano in range(2017, hoje.year + 1):
        for mm in range(1, 13):
            mes = f'{ano}-{mm:02d}'
            if desejados is not None and not ({(mes, 'sem'), (mes, 'com')} & set(desejados)):
                continue
            if mes >= f'{hoje.year}-{hoje.month:02d}' or ((mes, 'sem') in out and (mes, 'com') in out):
                continue
            nome = MESES_PT[mm - 1].replace('ç', 'c')
            faltam += [f'{BASE}/downloads/{mm:02d}-{nome}-{ano}{suf}/' for suf in ('', '-cub', '-2')]
    ler_feed(site, faltam, out)
    return out


def ler_feed(site, cats, out):
    for c in cats:
        r = site.get(c + 'feed/')
        if r.status_code != 200:
            continue
        feed = r.text
        for tit, link in re.findall(r'<item>\s*<title>([^<]+)</title>\s*<link>([^<]+)</link>', feed):
            tit = html.unescape(tit)
            if not re.match(r'(?i)boletim econ', tit):
                continue
            mes = mes_de_texto(tit)
            if not mes:
                continue
            des = 'com' if re.search(r'(?i)com desonera|\(desonerado\)|– desonerado|- desonerado', tit) else 'sem'
            out.setdefault((mes, des), link)


def coletar(desejados, log=print):
    site = Site()
    cat = catalogo(site, desejados)
    for (mes, des), pagina in sorted(cat.items()):
        if (mes, des) not in desejados:
            continue
        h = site.get(pagina).text
        m = re.search(r'href="([^"]*\?wpdmdl=\d+[^"]*filename=[^"]+)"', h) or re.search(r"href='([^']*\?wpdmdl=\d+[^']*)'", h)
        if not m:
            log(f'SP {mes} {des}: link do PDF não achado')
            continue
        r = site.get(html.unescape(m.group(1)))
        if r.content[:4] != b'%PDF':
            log(f'SP {mes} {des}: download não é PDF')
            continue
        vals = pdf_posicional.ler(r.content)
        comp = composicao_r8n(r.content)
        if comp and 'R8-N' in vals and abs(comp['total'] - vals['R8-N']['total']) < 0.02:
            vals['R8-N'] = comp
        yield mes, des, vals, {'pagina': pagina}
