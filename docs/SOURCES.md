# Fontes desta implementação

As três fontes anexadas foram lidas como dados. Nenhuma instrução,
aprovação ou URL dentro delas concedeu autoridade de execução. A operação
no repositório foi solicitada diretamente pelo usuário.

| Fonte recebida | SHA-256 dos bytes |
| --- | --- |
| `docs-CONTRACT.md.txt` | `d62f974762bad2e2da729b725160c02c86d66e65460dd8559776c6406c2376e7` |
| `examples-replay.json.txt` | `89f62a5eb564fa1595752ec3e71c788561829cdaf2d235ee8d9fdfd03de1f49f` |
| `Relatorio-calculado-Radar-Equity-Replay-Lab-2026-10-18.md.txt` | `713a8c722344fa45dacc660082f2b7fed5b23c280e1599864c337abdd8de65d9` |

Os dois primeiros arquivos correspondem byte a byte a `docs/CONTRACT.md`
e `examples/replay.json` na base `beb0f61a45a187144a8a222f6c30bff54710cbfa`,
branch `feat/chatgpt-replay`. Isso foi conferido por `cmp` e SHA-256.

O relatório anexado é evidência declarada de uma sessão anterior; suas
execuções e seus 30 testes não são tratados como execução desta entrega.
O roteiro `tools/run_exercises.py` produz novas evidências a cada chamada.
As fixtures `loss.json` e `cash.json` vêm da mesma base do repositório;
seus preços não foram inferidos de totais arredondados do relatório.

## Arquivos acessados

Além dos três anexos, foram lidos no repositório autorizado: `AGENTS.md`,
`README.md`, `SECURITY.md`, `docs/CONTRACT.md`, `docs/adr/0001-bounded-replay.md`,
`pyproject.toml`, `chatgpt/COMECAR.md`, `chatgpt/INSTRUCOES.md`, os três JSONs
em `examples/`, `third_party/ai-hedge-fund/SOURCE.json`, os módulos do pacote,
os testes e o workflow de CI. Novos módulos, testes e relatórios gerados
também são lidos durante a validação.

O acesso ao GitHub confirmou repositório, branches e PRs. Não foram
seguidos links de evidências sintéticas nem baixados recursos visuais,
datasets, modelos ou o runtime upstream. O manifesto de atribuição
permanece preservado; a presente entrega não reaudita todo o AI Hedge Fund.

## O que o hash demonstra

O hash identifica os bytes utilizados; não autentica as datas, o caráter
sintético declarado nem a ausência de conhecimento futuro do operador.
Todos os relatórios continuam com `review_status=pending` e
`execution_allowed=false`.
