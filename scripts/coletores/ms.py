"""Sinduscon-MS — https://sindusconms.com.br/cub/

Um PDF por mês (normal e desonerado). O mês e o ano são lidos do próprio PDF
("MÊS: OUTUBRO ANO: 2026"); o nome do arquivo só serve para pré-filtrar.
Só totais (o quadro de composição do R8-N não identifica as parcelas de forma inequívoca).
"""
import re, pymupdf
from comum_site import Site
from cub_comum import MESES_PT
import pdf_posicional

UF = 'MS'
FONTE_ID = 'sinduscon-ms'
FONTE = {'nome': 'Sinduscon-MS', 'origem': 'https://sindusconms.com.br/cub/', 'principal': True}
PRIMEIRO_MES = '2015-10'
ABREV = ['JAN', 'FEV', 'MAR', 'ABR', 'MAI', 'JUN', 'JUL', 'AGO', 'SET', 'OUT', 'NOV', 'DEZ']


def palpite(url):
    """Mês provável pelo nome/pasta do arquivo → (AAAA-MM, des) ou (None, des)."""
    nome = url.rsplit('/', 1)[-1].upper()
    des = 'com' if ('DESON' in nome or re.search(r'(^|[.\-_])D[.\-_]', nome)) else 'sem'
    up = re.search(r'/uploads/(\d{4})/(\d{2})/', url)
    mm = None
    for i, a in enumerate(ABREV):
        if re.search(rf'(?<![A-Z]){a}', nome):
            mm = i + 1
            break
    ano = re.search(r'(20\d{2})(?!\d)', nome.replace('12721', '').replace('2006', ''))
    if mm and ano:
        return f'{ano.group(1)}-{mm:02d}', des
    if mm and up:
        a, m = int(up.group(1)), int(up.group(2))
        return f'{a if mm <= m else a - 1}-{mm:02d}', des
    return None, des


def mes_do_pdf(t):
    T = t.upper()
    m = re.search(r'M[ÊE]S:\s*([A-ZÇÃ]+)\s+ANO:\s*(\d{4})', T) or \
        re.search(r'REFERENTES\s+AO\s+M[ÊE]S\s+DE\s+([A-ZÇÃ]+)\s+DE\s+(\d{4})', T)
    if not m:
        return None
    nomes = [x.upper() for x in MESES_PT]
    return f'{m.group(2)}-{nomes.index(m.group(1)) + 1:02d}' if m.group(1) in nomes else None


def coletar(desejados, log=print):
    site = Site()
    h = site.get('https://sindusconms.com.br/cub/').text
    links = sorted(set(re.findall(r'href="([^"]+\.pdf)"', h)))
    vistos = set()
    for u in links:
        if u.count('http') != 1:      # link malformado no site (duas URLs coladas)
            continue
        mes, des = palpite(u)
        if mes and (mes, des) not in desejados:
            continue
        try:
            r = site.get(u)
        except RuntimeError as e:
            log(f'MS: {e}')
            continue
        if r.content[:4] != b'%PDF':
            continue
        t = ' '.join(p.get_text() for p in pymupdf.open(stream=r.content, filetype='pdf'))
        mes_real = mes_do_pdf(t)
        des_real = 'com' if re.search(r'(?i)desonera', t) else des
        if not mes_real or (mes_real, des_real) not in desejados or (mes_real, des_real) in vistos:
            continue
        vistos.add((mes_real, des_real))
        yield mes_real, des_real, pdf_posicional.ler(r.content), {'arquivo': u}
