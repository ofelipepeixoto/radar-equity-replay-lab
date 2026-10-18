# Delimitadores vazios em URLs sintéticas

Conferência de 18/10/2026 contra o contrato v1 e a base `beb0f61`.

O parser de URL aceitava `https://x.invalid/?`, `https://x.invalid/#` e
`https://x.invalid:` porque os componentes vazios eram normalizados pelo
`urlsplit`. O contrato já proibia porta, query e fragmento; o núcleo agora
recusa também a presença dos seus delimitadores. Um `%3F` ou `%23` dentro
do caminho continua sendo conteúdo do caminho e é aceito.

Achado: divergência de validação, de impacto baixo neste motor offline.
Não houve requisição de rede nem divulgação do conteúdo da URL na saída.
Não se infere SSRF ou exploração a partir desse comportamento.

Validação executada em Python 3.12.14:

```sh
PYTHONPATH=src python3 -m unittest discover -s tests -p test_replay.py -v
git diff --check
```

Resultado: 31 testes aprovados, incluindo porta/query/fragmento vazios,
porta explícita, caminho codificado e as 30 verificações anteriores.
Não muda fórmulas, valores das fixtures nem o schema. Reversão: reverter
o commit; isso reabriria a divergência em relação ao contrato.
