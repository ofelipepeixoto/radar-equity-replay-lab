# Contrato do replay educacional v1

CLI: `PYTHONPATH=src python3 -m radar_equity_replay examples/replay.json --output NOVO.json`. Python3.11+ em Linux/POSIX; sem dependências runtime de terceiros. IO Windows não homologado. Não há consulta de mercado, algoritmo de seleção, broker, rebalanceamento ou API paga.

## Envelope estrito

JSON UTF-8 de até1MiB. Chaves exatas, nenhum campo opcional oculto:

| Campo | Regra |
| --- | --- |
| schema | radar-equity-replay-input/v1 |
| synthetic_only | booleano true; false recusado |
| project_id | ID opaco alfanumérico com `_`/`-`, até64 caracteres |
| currency | USD,BRL ouEUR; sem conversão cambial |
| initial_capital | String decimal com duas casas,0,01 a10¹² |
| decision_at | UTC canônico YYYY-MM-DDTHH:MM:SSZ |
| execute_on | Data ISO canônica da sessão1 fornecida |
| price_basis | synthetic_adjusted_close_no_dividends |
| assets | Lista de1–20IDs distintos |
| target_weights | Objeto com exatamente os IDs; strings decimais em[0,1], soma≤1 |
| fee_bps / slippage_bps | Strings decimais em[0,100], até6casas |
| evidence |1–50objetos, esquema abaixo |
| sessions |3–2.500sessões, esquema abaixo |

Números financeiros são strings, ponto decimal e no máximo seis casas, sem expoente, sinal negativo ou separadores. Números JSON literais, NaN/Infinity, chaves duplicadas, nulos, Unicode inválido, controles, campos extras e estrutura excessivamente profunda são recusados. Apenas o true literal de synthetic_only é aceito como booleano do contrato. Não incluir aprovação, chave, caminho de código ou credencial.

Cada evidência tem exatamente `evidence_id`, `available_at`, `source_url`, `text`. ID único; disponibilidade UTC não posterior à decisão; URL HTTPS de domínio terminado em `.invalid`, sem usuário/senha, porta, query ou fragmento; texto de1–1.000caracteres não vazio. Nada é buscado, renderizado ou executado. Datas e caráter sintético são declarações, não autenticidade comprovada.

Cada sessão tem `date`, `available_at`, `prices`, `benchmark_price`. Datas são crescentes/únicas; disponibilidade UTC na própria data e estritamente crescente. Prices tem exatamente os assets, com preços positivos de0,000001 a10⁹; benchmark_price usa o mesmo intervalo/unidade. Todos os preços são strings, até6casas. O programa não verifica calendário de bolsa, feriados, delistings ou eventos corporativos: a sessão seguinte é a seguinte **fornecida no arquivo**.

## Cronologia e fronteira de evidência

O índice0 representa a última sessão disponível antes da decisão; o índice1 é a entrada hipotética. Exigir `sessions[0].available_at ≤ decision_at < sessions[1].available_at` e `execute_on = sessions[1].date`. Assim, a entrada usa o fechamento do índice1, nunca o índice0. Os preços posteriores entram apenas na marcação/liquidação do algoritmo; os pesos são recebidos, não calculados dos preços futuros.

Isso não prova que o operador escolheu os pesos sem conhecer o futuro, nem que um LLM treinado depois desconheça os resultados. O guard também não autentica available_at. Evidência posterior falha, em vez de ser silenciosamente aceita. Não trocar data ou símbolo para contornar a recusa.

## Método financeiro explicitamente limitado

Comprar e manter, long-only, unidades fracionárias e uma única entrada, sem margem ou short. O peso fornecido representa uma fração do capital inicial **incluindo** taxa de entrada e slippage dentro dessa parcela. Não é peso ótimo recomendado nem peso exato pós-custos sobre NAV. Caixa residual = capital×(1−soma dos pesos), sem juros.

Se `f=fee_bps/10000`, `s=slippage_bps/10000`, capital `C`, peso `w` e preço de entrada `P₁`:

`parcela=C×w`; `unidades=parcela/[(1+f)×P₁×(1+s)]`.

A taxa de entrada incide sobre o notional efetivo; o slippage aumenta o preço de compra. Em cada fechamento posterior: `NAV=caixa+Σ(unidades×preço)`. No fim: vender hipoteticamente a `Pfinal×(1−s)` e descontar taxa `f` sobre esse notional de saída. Taxa e slippage são registrados separadamente em entrada/saída. Estes são custos **modelados**, não medição de spread, liquidez ou impacto real.

Benchmark: investir100% do mesmo capital na série benchmark, na mesma sessão1 e com as mesmas taxas/slippage de entrada/saída. A carteira pode conter caixa; comparar excesso de retorno não ajusta risco ou exposição e não comprova alpha.

Retorno%=100×(NAVfinal/C−1). Excesso em **pontos percentuais** é retorno da carteira menos retorno do benchmark. Drawdown%=maior100×(pico−NAV)/pico, incluindo capital inicial, marca de entrada, marcas seguintes e liquidação final. A curva distingue close_mark de final_liquidation no último dia; não contar esses dois pontos como dois pregões ou períodos independentes.

Não há Sharpe, CAGR ou significância estatística. Dividendos, juros, impostos, câmbio, aluguel, liquidez e impacto são omitidos. A precisão interna é Decimal50dígitos em contexto próprio, com arredondamento half-even; a saída arredonda a8casas; minúsculos custos podem arredondar a zero. O modelo de preços é declarado sintético, não normalizador de preços reais.

## Saída e arquivos

Schema `radar-equity-replay-report/v1`, `mode=synthetic_buy_and_hold_replay`, dados de metodologia/período, métricas e curvas de carteira/benchmark, hash SHA-256 dos **bytes exatos** de entrada e ponteiros JSON. Campos `review_status=pending`, `execution_allowed=false` e guard de autenticidade/origem da decisão não verificada. Não é recibo nativo do Evidence Kit, aprovação de corretora ou análise de suitability.

Não ecoa project_id, IDs de ativos/evidências, URLs ou texto. Métricas e hash ainda podem revelar informações: não há garantia universal de anonimização. Só usar fixtures públicas e fictícias.

Entrada é arquivo regular limitado e recusa symlink final/pais. Pais de saída já devem existir, caminho não aceita `.`/`..` ou componentes vazios; arquivo novo é criado exclusivamente em0600, sem sobrescrita. Erro CLI é genérico, não ecoa entrada/paths. Não é sandbox de filesystem, servidor multiusuário ou transação de broker. Em falha de escrita, investigar eventual arquivo parcial antes de repetir com outro nome; não há promessa de atomicidade de relatório.

Exemplos executáveis: replay.json,loss.json,cash.json. Eles documentam o contrato e os casos de ganho/perda/caixa; o valor econômico de estratégia alguma é inferido dessas fixtures.
