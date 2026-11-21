"""Gera os arquivos de consumo a partir de dados/cub-<UF>.json:

- dados/manifesto.json   → o que existe: por UF, fontes, primeiro/último mês, nº de meses
- dados/cub-ultimo.json  → último mês de cada UF (fonte principal), com parcelas — leve, para apps
- dados/cub-serie.json   → série completa dos totais da fonte principal: {UF: {mes: {sem|com: {proj: total}}}}
- dados/bib-indices.json → formato bib-indices/1 da Biblioteca de Obras (só totais, sem desoneração)
"""
import os, json, glob, datetime, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cub_comum as C


def fonte_principal(d, mes, des='sem'):
    """Fonte do mês para a série: só as principais (Sinduscon da capital), em ordem alfabética do id.
    As fontes regionais (ex.: Juiz de Fora, Noroeste-PR) ficam só no cub-<UF>.json."""
    ordem = sorted(f for f in d['fontes'] if d['fontes'][f].get('principal'))
    for f in ordem:
        v = d['meses'].get(mes, {}).get(f, {}).get(des)
        if v:
            return f, v['valores']
    return None, None


def main():
    man = {'gerado_em': datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds'),
           'projetos': C.PROJETOS, 'ufs': {}}
    ultimo, serie, bib = {}, {}, []
    for p in sorted(glob.glob(os.path.join(C.DADOS, 'cub-??.json'))):
        d = json.load(open(p, encoding='utf-8'))
        uf = d['uf']
        fontes = {}
        for fid, info in d['fontes'].items():
            ms = sorted(m for m, x in d['meses'].items() if fid in x)
            if ms:
                fontes[fid] = {**info, 'primeiro': ms[0], 'ultimo': ms[-1], 'meses': len(ms)}
        if not fontes:
            continue
        man['ufs'][uf] = {'arquivo': f'cub-{uf}.json', 'fontes': fontes,
                          'ultimo': max(f['ultimo'] for f in fontes.values())}
        serie[uf] = {}
        for mes in sorted(d['meses']):
            for des in ('sem', 'com'):
                f, v = fonte_principal(d, mes, des)
                if v:
                    serie[uf].setdefault(mes, {})[des] = {k: x['total'] for k, x in v.items()}
            if 'sem' in serie[uf].get(mes, {}):
                f, _ = fonte_principal(d, mes, 'sem')
                bib.append({'uf': uf, 'mes': mes, 'valores': serie[uf][mes]['sem'],
                            'fonte': f"{d['fontes'][f]['nome']} via robô miltonjose-cub"})
        um = max(serie[uf]) if serie[uf] else None
        if um:
            reg = {'mes': um}
            for des in ('sem', 'com'):
                f, v = fonte_principal(d, um, des)
                if v:
                    reg[des] = {'fonte': d['fontes'][f]['nome'], 'valores': v}
            ultimo[uf] = reg
    w = lambda nome, obj, ind=None: json.dump(obj, open(os.path.join(C.DADOS, nome), 'w', encoding='utf-8'),
                                             ensure_ascii=False, indent=ind, separators=None if ind else (',', ':'))
    w('manifesto.json', man, 1)
    w('cub-ultimo.json', ultimo, 1)
    w('cub-serie.json', serie)
    w('bib-indices.json', {'formato': 'bib-indices/1', 'cub': bib})
    print(f'saídas: {len(man["ufs"])} UFs')


if __name__ == '__main__':
    main()
