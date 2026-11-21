# miltonjose-cub

Robô que coleta o **CUB/m²** (Custo Unitário Básico, ABNT NBR 12.721:2006) divulgado pelos Sinduscons e guarda a série em JSON, para uso nas ferramentas de [miltonjose.com](https://miltonjose.com) (Quantify, Biblioteca de Obras, skill de orçamento paramétrico).

## Fontes

| Fonte | UFs | Como |
|---|---|---|
| Portal da CBIC — http://cub.org.br/cub-m2-estadual/ | AC, AM, BA, CE, DF, ES, GO, MA, MG, MT, PA, PB, PE, PI, PR, RJ, RN, RO, RR, SC, SE | "Relatório 5 – Composição CUB/m²", desde out/2015 |
| Sites dos próprios Sinduscons | SP, RS, MS, SE, MG, RO… | coletores próprios (em construção) |

Os dados são públicos; cada registro guarda a fonte e os parâmetros da consulta. Os PDFs originais não são armazenados.

## Arquivos (`dados/`)

| Arquivo | Conteúdo |
|---|---|
| `cub-<UF>.json` | tudo da UF: `fontes` + `meses[AAAA-MM][fonte][sem\|com].valores[projeto] = {mat, mo, adm, eq, total}` |
| `cub-ultimo.json` | último mês de cada UF (fonte principal), com parcelas |
| `cub-serie.json` | série dos totais da fonte principal: `{UF: {mes: {sem\|com: {projeto: total}}}}` |
| `manifesto.json` | por UF: fontes, primeiro/último mês, nº de meses |
| `bib-indices.json` | formato `bib-indices/1` da Biblioteca de Obras |
| `estado.json` | controle interno (meses ainda não publicados) |

`sem` = sem desoneração da mão de obra; `com` = com desoneração. Projetos-padrão: R1-B, PP4-B, R8-B, PIS, R1-N, PP4-N, R8-N, R16-N, R1-A, R8-A, R16-A, CAL8-N, CSL8-N, CSL16-N, CAL8-A, CSL8-A, CSL16-A, RP1Q, GI.

Leitura por CDN: `https://cdn.jsdelivr.net/gh/engmiltonjose/miltonjose-cub@main/dados/cub-ultimo.json`

## Rotina

GitHub Actions (`.github/workflows/cub-diario.yml`): dias úteis de 1 a 15 de cada mês e toda segunda, às 08:00 (Brasília). Abre uma issue atribuída ao dono só quando há mês novo, retificação ou falha.

Carga histórica manual: Actions → "CUB diário" → Run workflow → `inicio = 2015-10`.

Local: `python scripts/atualizar_cub.py [--inicio AAAA-MM] [--ufs GO,DF]`.
