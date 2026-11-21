"""Funções comuns do robô do CUB: códigos dos projetos-padrão, leitura de números e gravação dos JSONs."""
import json, re, os, datetime

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DADOS = os.path.join(RAIZ, 'dados')

# Os 19 projetos-padrão da ABNT NBR 12.721:2006 (mesmos códigos usados na Biblioteca de Obras)
PROJETOS = ['R1-B', 'PP4-B', 'R8-B', 'PIS',
            'R1-N', 'PP4-N', 'R8-N', 'R16-N',
            'R1-A', 'R8-A', 'R16-A',
            'CAL8-N', 'CSL8-N', 'CSL16-N',
            'CAL8-A', 'CSL8-A', 'CSL16-A',
            'RP1Q', 'GI']
PARCELAS = ['mat', 'mo', 'adm', 'eq']   # materiais, mão de obra, despesas administrativas, equipamentos

MESES_PT = ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 'julho', 'agosto',
            'setembro', 'outubro', 'novembro', 'dezembro']


def codigo(txt, padrao=None):
    """Normaliza 'PP-4-B', 'CSL-16-A', 'R 8 N', 'R-1' (+ padrão) → código canônico. None se não reconhecer."""
    t = re.sub(r'[\s\-–]', '', txt.upper())
    if t in ('PIS', 'RP1Q', 'GI'):
        return t
    m = re.fullmatch(r'(R1|PP4|R8|R16|CAL8|CSL8|CSL16)([BNA])?', t)
    if not m:
        return None
    suf = m.group(2) or padrao
    c = f'{m.group(1)}-{suf}' if suf else None
    return c if c in PROJETOS else None


def num(txt):
    """'2.795,37' → 2795.37"""
    t = txt.strip().replace('R$', '').replace(' ', '')
    if not re.fullmatch(r'-?\d{1,3}(\.\d{3})*(,\d+)?|-?\d+(,\d+)?', t):
        raise ValueError(f'número inválido: {txt!r}')
    return float(t.replace('.', '').replace(',', '.'))


def brl(v):
    """2795.37 → '2.795,37' ('—' se vazio)"""
    if v is None:
        return '—'
    return f'{v:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')


def mes_iso(ano, mes):
    return f'{int(ano):04d}-{int(mes):02d}'


def meses_entre(ini, fim):
    a, m = map(int, ini.split('-'))
    out = []
    while mes_iso(a, m) <= fim:
        out.append(mes_iso(a, m))
        m += 1
        if m == 13:
            a, m = a + 1, 1
    return out


def validar(valores, minimo=12):
    """valores = {proj: {total, mat, mo, adm, eq}}. Devolve lista de problemas (vazia = ok)."""
    prob = []
    if len(valores) < minimo:
        prob.append(f'só {len(valores)} projetos-padrão (mínimo {minimo})')
    for p, v in valores.items():
        if p not in PROJETOS:
            prob.append(f'código desconhecido {p}')
        tot = v.get('total')
        if not tot or not (300 < tot < 20000):
            prob.append(f'{p}: total fora da faixa ({tot})')
        partes = [v.get(k) for k in PARCELAS]
        if all(x is not None for x in partes) and tot and abs(sum(partes) - tot) > 0.05 + tot * 0.0005:
            prob.append(f'{p}: soma das parcelas {sum(partes):.2f} ≠ total {tot:.2f}')
    return prob


def sanear(valores):
    """Parcelas que não somam o total (erro de digitação no PDF do Sinduscon): mantém o total oficial e descarta
    as parcelas daquele projeto. Devolve a lista de projetos saneados."""
    feitos = []
    for p, v in valores.items():
        partes = [v.get(k) for k in PARCELAS]
        tot = v.get('total')
        if tot and all(x is not None for x in partes) and abs(sum(partes) - tot) > 0.05 + tot * 0.0005:
            for k in PARCELAS:
                v.pop(k, None)
            feitos.append(p)
    return feitos


def caminho_uf(uf):
    return os.path.join(DADOS, f'cub-{uf}.json')


def ler_uf(uf):
    p = caminho_uf(uf)
    if os.path.exists(p):
        with open(p, encoding='utf-8') as f:
            return json.load(f)
    return {'uf': uf, 'fontes': {}, 'meses': {}}


def gravar_uf(d):
    os.makedirs(DADOS, exist_ok=True)
    d['meses'] = dict(sorted(d['meses'].items()))
    with open(caminho_uf(d['uf']), 'w', encoding='utf-8') as f:
        json.dump(d, f, ensure_ascii=False, indent=1, sort_keys=False)


def registrar(d, fonte_id, fonte_info, mes, desoneracao, valores, origem):
    """Guarda um mês de uma fonte. desoneracao: 'sem' | 'com'. Devolve 'novo' | 'alterado' | 'igual'."""
    d['fontes'].setdefault(fonte_id, fonte_info)
    slot = d['meses'].setdefault(mes, {}).setdefault(fonte_id, {})
    antes = slot.get(desoneracao, {}).get('valores')
    if antes == valores:
        return 'igual'
    slot[desoneracao] = {'valores': valores, 'origem': origem,
                         'coletado_em': datetime.date.today().isoformat()}
    return 'novo' if antes is None else 'alterado'
