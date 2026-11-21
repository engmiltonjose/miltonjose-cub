"""Apoio aos coletores próprios (sites dos Sinduscons)."""
import re, time, requests
from cub_comum import MESES_PT

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36'
ABREV = {'jan': 1, 'fev': 2, 'mar': 3, 'abr': 4, 'mai': 5, 'jun': 6, 'jul': 7, 'ago': 8, 'set': 9, 'out': 10,
         'nov': 11, 'dez': 12}


class Site:
    def __init__(self, pausa=0.5):
        self.s = requests.Session()
        self.s.headers['User-Agent'] = UA
        self.pausa = pausa

    def get(self, url, **kw):
        for tent in range(4):
            try:
                r = self.s.get(url, timeout=60, **kw)
                time.sleep(self.pausa)
                if r.status_code < 500:
                    return r
            except requests.RequestException:
                pass
            time.sleep(5 * (tent + 1))
        raise RuntimeError(f'sem resposta: {url}')


def mes_de_texto(t):
    """'Boletim – Outubro de 2026', 'JANEIRO/2024', 'out/26', 'MARCO-2021' → 'AAAA-MM' (ou None)."""
    s = t.lower().replace('ç', 'c').replace('ã', 'a')
    nomes = [m.replace('ç', 'c').replace('ã', 'a') for m in MESES_PT]
    m = re.search(r'(' + '|'.join(nomes) + r')\W{0,3}(?:de\s+)?(\d{4})', s)
    if m:
        return f'{m.group(2)}-{nomes.index(m.group(1)) + 1:02d}'
    m = re.search(r'\b(' + '|'.join(ABREV) + r')[a-z]*\W{0,2}(\d{4}|\d{2})\b', s)
    if m:
        a = int(m.group(2))
        a = a + 2000 if a < 100 else a
        return f'{a}-{ABREV[m.group(1)]:02d}'
    return None
