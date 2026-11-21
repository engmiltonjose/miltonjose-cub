"""Sinduscon-MG (Belo Horizonte) — https://sinduscon-mg.org.br/cub/

Complementa o portal da CBIC, onde o Sinduscon-MG costuma atrasar. Usa os PDFs
"composicao_cub_<mes>_<ano>.pdf" e "composicao_cub_desonerado_<mes>_<ano>.pdf", que têm o
mesmo formato do Relatório 5 da CBIC.
"""
import re
from comum_site import Site, mes_de_texto
import cbic

UF = 'MG'
FONTE_ID = 'sinduscon-mg'
FONTE = {'nome': 'Sinduscon-MG (site)', 'origem': 'https://sinduscon-mg.org.br/cub/', 'principal': True}
PRIMEIRO_MES = '2025-01'
PAGINAS = ['https://sinduscon-mg.org.br/cub/composicao-cub-m2-por-projeto-padrao',
           'https://sinduscon-mg.org.br/cub/composicao-cub-m2-por-projeto-padrao-desonerado']


def coletar(desejados, log=print):
    site = Site()
    links = set()
    for p in PAGINAS:
        links |= set(re.findall(r'href="([^"]*/uploads/\d{4}/\d{2}/composicao_cub_[^"]+\.pdf)"', site.get(p).text))
    for u in sorted(links):
        nome = u.rsplit('/', 1)[-1]
        mes = mes_de_texto(nome.replace('_', ' '))
        des = 'com' if 'desonerado' in nome.lower() else 'sem'
        if not mes or (mes, des) not in desejados:
            continue
        r = site.get(u)
        if r.content[:4] != b'%PDF':
            continue
        vals = cbic.ler_pdf(r.content, des == 'com')
        mes = vals.pop('_mes_dados', None) or mes
        yield mes, des, vals, {'arquivo': u}
