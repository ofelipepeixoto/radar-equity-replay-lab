# Alertas deduplicados do lock upstream

Consulta de 108 pacotes pinados: **18 registros, 13 IDs de advisory distintos, oito pacotes**. A diferença se deve à repetição de IDs no serviço de advisories. Não são 18 falhas independentes. Black e pytest são ferramentas de desenvolvimento; os demais são dependências runtime/transitivas. Faixa afetada de versão não comprova caminho explorável neste aplicativo.

| Pacote | Pin | Escopo | IDs distintos | Correções indicadas |
|---|---|---|---:|---|
| black | 23.12.1 | development | 3 | 24.3.0, 26.3.0, 26.3.1 |
| langchain-anthropic | 0.3.5 | runtime/transitive | 1 | 1.4.6 |
| langchain-core | 0.3.86 | runtime/transitive | 2 | 1.2.11, 1.2.22 |
| langchain-openai | 0.3.35 | runtime/transitive | 1 | 1.1.14 |
| multidict | 6.7.1 | runtime/transitive | 1 | 6.9.1 |
| pytest | 7.4.4 | development | 1 | 9.0.3 |
| python-dotenv | 1.0.0 | runtime/transitive | 1 | 1.2.2 |
| urllib3 | 2.7.0 | runtime/transitive | 3 | 2.8.0 |

## IDs e fontes primárias

Não atualizei o lock upstream. Atualizações LangChain entre 0.3 e 1.x exigem migração e regressões; não são troca cega de versão.

- `black==23.12.1`: `PYSEC-2024-48`; aliases CVE-2024-21503, GHSA-fj7x-q9j7-g6q6; https://github.com/advisories/GHSA-fj7x-q9j7-g6q6
- `black==23.12.1`: `PYSEC-2026-2121`; aliases GHSA-3936-cmfr-pm3m, CVE-2026-32274; https://github.com/advisories/GHSA-3936-cmfr-pm3m
- `black==23.12.1`: `PYSEC-2026-2120`; aliases CVE-2026-31900, GHSA-v53h-f6m7-xcgm; https://github.com/advisories/GHSA-v53h-f6m7-xcgm
- `langchain-anthropic==0.3.5`: `PYSEC-2026-2556`; aliases GHSA-gr75-jv2w-4656, CVE-2026-55443; https://github.com/advisories/GHSA-gr75-jv2w-4656
- `langchain-core==0.3.86`: `PYSEC-2026-2193`; aliases GHSA-qh6h-p6c9-ff54, CVE-2026-34070; https://github.com/advisories/GHSA-qh6h-p6c9-ff54
- `langchain-core==0.3.86`: `PYSEC-2026-2562`; aliases CVE-2026-26013, GHSA-2g6r-c272-w58r; https://github.com/advisories/GHSA-2g6r-c272-w58r
- `langchain-openai==0.3.35`: `PYSEC-2026-76`; aliases CVE-2026-41488, GHSA-r7w7-9xr2-qq2r; https://github.com/advisories/GHSA-r7w7-9xr2-qq2r
- `multidict==6.7.1`: `PYSEC-2026-4244`; aliases CVE-2026-104874, GHSA-54p9-h82j-f925; https://github.com/advisories/GHSA-54p9-h82j-f925
- `pytest==7.4.4`: `PYSEC-2026-1845`; aliases GHSA-6w46-j5rx-g56g, CVE-2025-71176; https://github.com/advisories/GHSA-6w46-j5rx-g56g
- `python-dotenv==1.0.0`: `PYSEC-2026-2270`; aliases GHSA-mf9w-mj56-hr94, CVE-2026-28684; https://github.com/advisories/GHSA-mf9w-mj56-hr94
- `urllib3==2.7.0`: `PYSEC-2026-4177`; aliases GHSA-vxq7-64xx-v4gw, CVE-2026-97689; https://github.com/advisories/GHSA-vxq7-64xx-v4gw
- `urllib3==2.7.0`: `PYSEC-2026-4176`; aliases GHSA-gh4c-6fx4-qh6g, CVE-2026-97688; https://github.com/advisories/GHSA-gh4c-6fx4-qh6g
- `urllib3==2.7.0`: `PYSEC-2026-4175`; aliases GHSA-8988-9cw3-xx77, CVE-2026-97687; https://github.com/advisories/GHSA-8988-9cw3-xx77
