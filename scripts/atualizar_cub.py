"""Robô do CUB/m² — busca meses novos em todas as fontes e grava dados/cub-<UF>.json.

Uso:
  python scripts/atualizar_cub.py                       # rotina diária (últimos meses)
  python scripts/atualizar_cub.py --inicio 2015-10      # carga histórica
  python scripts/atualizar_cub.py --ufs GO,DF --inicio 2024-01

Saída para o aviso: saida/titulo.txt + saida/novidades.md (só quando há novidade ou falha).
"""
import sys, os, json, time, argparse, datetime, traceback
AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [AQUI, os.path.join(AQUI, 'coletores')]
sys.stdout.reconfigure(encoding='utf-8')
import cub_comum as C
import cbic
import gerar_saidas

ESTADO = os.path.join(C.DADOS, 'estado.json')
SAIDA = os.path.join(C.RAIZ, 'saida')
JANELA_RECHECK = 3    # meses recentes relidos sempre (retificações)
JANELA_AUSENTE = 8    # meses recentes em que "ainda não publicado" é tentado de novo


def mes_atual():
    h = datetime.date.today()
    return C.mes_iso(h.year, h.month)


def recuar(mes, n):
    a, m = map(int, mes.split('-'))
    m -= n
    while m < 1:
        a, m = a - 1, m + 12
    return C.mes_iso(a, m)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--inicio', help='primeiro mês (AAAA-MM); padrão = últimos meses')
    ap.add_argument('--ufs', help='lista de UFs separadas por vírgula')
    ap.add_argument('--pausa', type=float, default=0.4)
    a = ap.parse_args()

    fim = mes_atual()
    ini = a.inicio or recuar(fim, JANELA_AUSENTE)
    recheck_de = recuar(fim, JANELA_RECHECK)
    ausente_de = recuar(fim, JANELA_AUSENTE)
    ufs = a.ufs.split(',') if a.ufs else list(cbic.SINDUSCONS)
    estado = json.load(open(ESTADO, encoding='utf-8')) if os.path.exists(ESTADO) else {'ausentes': {}}

    novidades, alteracoes, falhas, problemas = [], [], [], []
    for uf in ufs:
        if uf not in cbic.SINDUSCONS:
            continue
        d = C.ler_uf(uf)
        try:
            sess = cbic.Sessao(uf)
        except Exception as e:
            falhas.append(f'{uf}: portal da CBIC não abriu ({e})')
            continue
        for k, (sid, nome) in enumerate(cbic.SINDUSCONS[uf]):
            fid = f'cbic-{sid}'
            info = {'nome': nome, 'origem': 'CBIC — http://cub.org.br/cub-m2-estadual/', 'principal': k == 0}
            for mes in C.meses_entre(ini, fim):
                for des in ('sem', 'com'):
                    chave = f'{fid}|{mes}|{des}'
                    ja = d['meses'].get(mes, {}).get(fid, {}).get(des)
                    if ja and mes < recheck_de:
                        continue
                    if chave in estado['ausentes'] and mes < ausente_de:
                        continue
                    ano, mm = mes.split('-')
                    try:
                        vals, motivo = sess.composicao(sid, ano, mm, des == 'com')
                    except Exception as e:
                        falhas.append(f'{uf} {nome} {mes} {des}: {e}')
                        continue
                    finally:
                        time.sleep(a.pausa)
                    if vals is None:
                        estado['ausentes'][chave] = datetime.date.today().isoformat()
                        continue
                    estado['ausentes'].pop(chave, None)
                    mes_dados = vals.pop('_mes_dados', None) or mes
                    prob = C.validar(vals)
                    if prob:
                        problemas.append(f'{uf} {nome} {mes} {des}: ' + '; '.join(prob))
                        continue
                    origem = {'relatorio': 'composicao-cub-m2', 'sinduscon': sid, 'mes_consultado': mes,
                              'desoneracao': des}
                    if mes_dados != mes:
                        origem['obs'] = f'Sinduscon rotula pelo mês de uso ({mes}); gravado no mês dos dados ({mes_dados})'
                    r = C.registrar(d, fid, info, mes_dados, des, vals, origem)
                    if r == 'novo':
                        novidades.append((uf, nome, mes_dados, des, vals.get('R8-N', {}).get('total')))
                    elif r == 'alterado':
                        alteracoes.append(f'{uf} {nome} {mes_dados} ({des} desoneração)')
            print(f'{uf} {nome}: ok', flush=True)
        C.gravar_uf(d)
        json.dump(estado, open(ESTADO, 'w', encoding='utf-8'), ensure_ascii=False, indent=0, sort_keys=True)

    gerar_saidas.main()
    relatorio(novidades, alteracoes, falhas, problemas, carga=bool(a.inicio))


def relatorio(novidades, alteracoes, falhas, problemas, carga):
    os.makedirs(SAIDA, exist_ok=True)
    for f in ('titulo.txt', 'novidades.md'):
        p = os.path.join(SAIDA, f)
        if os.path.exists(p):
            os.remove(p)
    if not (novidades or alteracoes or falhas or problemas) or carga:
        print(f'novos: {len(novidades)} | alterados: {len(alteracoes)} | falhas: {len(falhas)} | problemas: {len(problemas)}')
        if not carga:
            return
    meses = sorted({n[2] for n in novidades})
    if falhas or problemas:
        titulo = f'⚠️ CUB: {len(falhas) + len(problemas)} problema(s) na coleta'
    else:
        titulo = f'✅ CUB novo: {", ".join(meses[-2:])} ({len({n[0] for n in novidades})} UFs)'
    L = [f'# {titulo}', '']
    if novidades:
        L += ['## Meses novos', '', '| UF | Sinduscon | Mês | Desoneração | R8-N (R$/m²) |', '|---|---|---|---|---|']
        for uf, nome, mes, des, r8 in sorted(novidades)[-200:]:
            L.append(f'| {uf} | {nome} | {mes} | {des} | {C.brl(r8)} |')
        L.append('')
    if alteracoes:
        L += ['## Valores retificados pelo Sinduscon', ''] + [f'- {x}' for x in alteracoes] + ['']
    if problemas:
        L += ['## Dados recusados na validação (não gravados)', ''] + [f'- {x}' for x in problemas] + ['']
    if falhas:
        L += ['## Falhas de acesso', ''] + [f'- {x}' for x in falhas[:50]] + ['']
    L += ['**O que fazer:** nada, se só houver meses novos. Em caso de problema, peça ao Claude para olhar o log desta execução.']
    open(os.path.join(SAIDA, 'titulo.txt'), 'w', encoding='utf-8').write(titulo)
    open(os.path.join(SAIDA, 'novidades.md'), 'w', encoding='utf-8').write('\n'.join(L))
    print(titulo)


if __name__ == '__main__':
    try:
        main()
    except Exception:
        traceback.print_exc()
        sys.exit(1)
