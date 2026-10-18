# Entrega educacional 0.2.0 — 18/10/2026

Implementação experimental completa do fluxo definido nas três fontes anexadas:
fixture fictícia → contrato estrito → replay em T+1 → custos e benchmark →
relatório verificável → caderno offline em português. Revisão humana pendente.
Não é implantação de serviço financeiro nem uma versão estável homologada.

## O que está implementado

- Motor Python stdlib preservado, sem seleção de ativos, rede ou corretora.
- Caderno HTML responsivo com quatro caminhos, comparação com custo zero,
  custos separados, curva/drawdown, cronologia UTC e download JSON sanitizado.
- Três cadernos gerados: [replay](demo/replay.html), [perda](demo/loss.html)
  e [caixa](demo/cash.html). Abrir os HTMLs localmente; GitHub mostra o código.
- Roteiro de quatro execuções efetivas da CLI com conferência independente
  usando `Fraction`, sem importar o motor para o cálculo de referência.
- Recusas verificadas: evidência um segundo posterior, entrada na sessão T,
  campo extra `approved` e sobrescrita. Entradas originais preservadas.
- Guia de uso no ChatGPT, fontes com hashes, especificação UX e CI atualizados.

## Execução desta entrega

Ambiente local: Python 3.12.14 em Linux/POSIX. Comandos executados:

```sh
PYTHONPATH=src python3 -m unittest discover -s tests -v
PYTHONPATH=src python3 tools/run_exercises.py --output-dir docs/validation/run-20261018
PYTHONPATH=src python3 -m radar_equity_replay.workbook examples/replay.json --output docs/demo/replay.html
PYTHONPATH=src python3 -m radar_equity_replay.workbook examples/loss.json --output docs/demo/loss.html
PYTHONPATH=src python3 -m radar_equity_replay.workbook examples/cash.json --output docs/demo/cash.html
git diff --check
```

**60 testes aprovados:** 31 de núcleo/CLI/IO, 11 do roteiro independente e
18 do caderno. Abrangem tipos, limites, cronologia, fórmulas, custos, curvas,
privacidade, payloads HTML, Unicode perto de 1 MiB e exclusividade de arquivos.
O [log da execução](validation/run-20261018/run.json) registra argumentos,
códigos de saída, versões e hashes dos bytes de fonte/entradas/saídas.

Todos os relatórios e entradas variantes dessa pasta são gerados e fictícios;
não editar manualmente. Para reproduzir, usar um diretório **novo**. Para os
cadernos, usar arquivos novos e comparar com `cmp`; o resultado é determinístico.
Os caminhos absolutos do log identificam o ambiente desta execução.

| Exercício | Saldo final carteira (BRL) | Retorno | Drawdown máximo |
| --- | ---: | ---: | ---: |
| Replay com custos | 1087.03444981 | 8.70344498% | 0.13617437% |
| Replay sem custos | 1090.00000000 | 9.00000000% | 0.00000000% |
| Perda com custos | 518.74188780 | -48.12581122% | 48.12581122% |
| Caixa | 1000.00000000 | 0.00000000% | 0.00000000% |

Exemplo principal: BRL 1.000, parcelas declaradas 60%/30% e 10% de caixa,
taxa de 10 bps e slippage de 5 bps em cada lado. Um ponto-base corresponde a
0,01 ponto percentual. Entrada em 06/01/2026; liquidação em 08/01/2026.
SHA-256 exato da entrada:
`89f62a5eb564fa1595752ec3e71c788561829cdaf2d235ee8d9fdfd03de1f49f`.

Benchmark com o mesmo capital, entrada e modelo de custos: saldo final
BRL 1076.76485434, retorno 7.67648543%, drawdown 0.14995000%.
A exposição é diferente: benchmark 100% aplicado, carteira com caixa.
Excesso de 1.02695955 p.p. é uma diferença aritmética entre fixtures,
sem demonstração de habilidade, alpha ou adequação à pessoa.

Build wheel offline aprovado (`--no-deps --no-build-isolation`, sem índice).
O módulo do caderno foi executado diretamente do wheel 0.2.0 e seu HTML
coincidiu byte a byte com `docs/demo/replay.html`. O wheel é intermediário de
validação, não uma release publicada.

## Revisão de segurança e UX

Três divergências observadas foram corrigidas e receberam regressões:

1. Delimitadores vazios de porta/query/fragmento escapavam da validação URL.
   A correção está na PR de contrato anterior a esta camada.
2. O oráculo independente aceitava `0` no lugar de `false` em metadados
   aninhados, por igualdade de tipos numéricos do Python. Agora compara tipos.
3. A cópia sem custos expandia Unicode para ASCII e podia ultrapassar 1 MiB
   em uma entrada válida. Agora preserva UTF-8.

Não foi observado XSS nem eco de IDs, URLs ou texto de evidência nos testes.
Isso descreve o escopo revisado, sem promessa de segurança universal.
A soma dos componentes publicados pode diferir na última casa de um total
calculado antes do arredondamento; o caderno explicita essa diferença e a
separa do efeito dos custos no saldo final.

A validação de interface foi estrutural/automatizada. O ambiente não tinha
Chromium utilizável e a obtenção do navegador de teste não foi concluída;
não houve teste visual, de teclado, zoom, leitor de tela ou participantes
humanos. A especificação [UX](UX.md) registra essas tarefas pendentes.
Não há declaração de conformidade WCAG ou melhora de usabilidade medida.

## Estado e limites

`review_status=pending`; `execution_allowed=false` em todos os relatórios.
As datas e o caráter sintético são declarações. Hash e guard temporal não
autenticam evidência ou ausência de conhecimento futuro do operador/LLM.
O modelo omite dividendos, impostos, juros, câmbio, empréstimo de ações,
liquidez e impacto real. Não anualiza, estima Sharpe ou prevê recuperação.

Código versionado em PRs para revisão; sem merge, deploy, servidor, feed,
API paga, automação persistente ou integração financeira. A CI remota é uma
verificação separada da execução local, com resultado informado na PR.
Homologação por segundo operador humano ainda pendente. Windows não homologado.

Próximos experimentos: repetir o caderno com outro operador; testar navegação
por teclado/zoom; comparar uma nova fixture fictícia mantendo preços e pesos
e variando apenas os custos. As integrações do ecossistema continuam futuras.

Reversão: descartar os relatórios de laboratório e reverter a camada de código.
Não existe migração, conta ou estado financeiro para restaurar. Preservadas
as licenças MIT de Carlos Felipe e Virat Singh e o manifesto de atribuição.
