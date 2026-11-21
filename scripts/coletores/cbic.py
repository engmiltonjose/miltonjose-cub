"""Coletor do portal da CBIC (http://cub.org.br — só HTTP).

Usa o "Relatório 5 - Composição CUB/m²", que traz para os 19 projetos-padrão o total
e as parcelas (materiais, mão de obra, despesas administrativas, equipamentos).
Um POST por Sinduscon × mês × desoneração. Disponível a partir de out/2015.
"""
import re, time, requests, pymupdf
from cub_comum import codigo, num, PROJETOS, MESES_PT

BASE = 'http://cub.org.br/cub-m2-estadual/'
UA = 'Mozilla/5.0 (robo-cub; dados publicos)'

# UF → [(id no portal, nome)]. O primeiro de cada UF é o "principal" (capital).
SINDUSCONS = {
    'AC': [('4', 'Sinduscon-AC')], 'AM': [('5', 'Sinduscon-AM')], 'BA': [('6', 'Sinduscon-BA')],
    'CE': [('7', 'Sinduscon-CE')], 'DF': [('8', 'Sinduscon-DF')], 'ES': [('9', 'Sinduscon-ES')],
    'GO': [('10', 'Sinduscon-GO')], 'MA': [('11', 'Sinduscon-MA')], 'MT': [('13', 'Sinduscon-MT')],
    'MG': [('1', 'Sinduscon-MG'), ('32', 'Sinduscon-Juiz de Fora'), ('39', 'Sinduscon-GV'),
           ('36', 'Sinduscon Norte'), ('33', 'Sinduscon-Vale do Piranga'), ('34', 'Sinduscon-Lagos')],
    'PR': [('18', 'Sinduscon-PR'), ('19', 'Sinduscon-Noroeste-PR'), ('38', 'Sinduscon-Oeste-PR')],
    'PB': [('15', 'Sinduscon-João Pessoa')], 'PA': [('14', 'Sinduscon-PA')], 'PE': [('16', 'Sinduscon-PE')],
    'PI': [('17', 'Sinduscon-Teresina')], 'RN': [('21', 'Sinduscon-RN')], 'RJ': [('20', 'Sinduscon-Rio')],
    'RO': [('25', 'Sinduscon-RO')], 'RR': [('30', 'Sinduscon-RR')],
    'SC': [('26', 'Sinduscon Grande Florianópolis-SC')], 'SE': [('22', 'Sinduscon-SE')],
}
ROTULOS = [('Materiais', 'mat'), ('Mão de Obra', 'mo'), ('Despesas Administrativas', 'adm'),
           ('Equipamentos', 'eq'), ('Total', 'total')]


class Sessao:
    """Uma sessão por UF (o token csrf vale para vários POSTs)."""
    def __init__(self, uf):
        self.uf, self.url = uf, f'{BASE}{uf}/'
        self.s = requests.Session()
        self.s.headers['User-Agent'] = UA
        h = self._req('get', self.url).text
        self.tok = re.search(r"csrfmiddlewaretoken' value='([^']+)", h).group(1)

    def _req(self, metodo, url, **kw):
        for tent in range(4):
            try:
                r = getattr(self.s, metodo)(url, timeout=60, **kw)
                if r.status_code < 500:
                    return r
            except requests.RequestException:
                pass
            time.sleep(5 * (tent + 1))
        raise RuntimeError(f'CBIC sem resposta: {url}')

    def composicao(self, sid, ano, mes, desonerado):
        """Devolve (valores, None) ou (None, motivo)."""
        r = self._req('post', self.url, headers={'Referer': self.url}, data=dict(
            csrfmiddlewaretoken=self.tok, uf=self.uf, sinduscon=sid, relatorio='composicao-cub-m2',
            ano=str(ano), mes=str(int(mes)), desoneracao='com-desoneracao' if desonerado else 'sem-desoneracao',
            projeto='1'))
        if r.content[:4] != b'%PDF':
            m = re.search(r'Erro:\s*([^<]{0,120})', r.text)
            return None, (m.group(1).strip() if m else 'sem PDF')
        return ler_pdf(r.content, desonerado), None


def mes_dos_dados(conteudo):
    """Alguns Sinduscons (ex.: Grande Florianópolis) rotulam pelo mês de USO:
    'CUB/m² dados de Outubro/2026, para ser usado em Novembro/2026'. Devolve 'AAAA-MM' dos dados ou None."""
    t = ' '.join(p.get_text() for p in pymupdf.open(stream=conteudo, filetype='pdf'))
    m = re.search(r'dados de\s+(\w+)/(\d{4}),?\s+para ser usado', t, re.I)
    if not m:
        return None
    nomes = [x.lower() for x in MESES_PT]
    return f'{m.group(2)}-{nomes.index(m.group(1).lower()) + 1:02d}'


def ler_pdf(conteudo, desonerado=None):
    doc = pymupdf.open(stream=conteudo, filetype='pdf')
    linhas = [l.strip() for p in doc for l in p.get_text().splitlines()]
    texto = ' '.join(linhas)
    md = mes_dos_dados(conteudo)
    if desonerado is not None and ('Desonerad' in texto) != desonerado:
        raise ValueError('PDF não corresponde à desoneração pedida')
    out, i = {}, 0
    while i < len(linhas):
        if linhas[i] != 'Item':
            i += 1
            continue
        i += 1
        cods = []
        while i < len(linhas) and linhas[i] != 'Materiais':
            c = codigo(linhas[i])
            if c:
                cods.append(c)
            i += 1
        for rot, chave in ROTULOS:
            while i < len(linhas) and linhas[i] != rot:
                i += 1
            i += 1
            vals = []
            while len(vals) < len(cods) and i < len(linhas):
                if linhas[i]:
                    try:
                        vals.append(num(linhas[i]))
                    except ValueError:
                        break
                i += 1
            for c, v in zip(cods, vals):
                out.setdefault(c, {})[chave] = v
    vals = {p: out[p] for p in PROJETOS if p in out}
    if md:
        vals['_mes_dados'] = md
    return vals
