# Revisão independente da adaptação

Data UTC: 2026-10-18. Alvo: `radar-equity-replay-lab/src`, quatro módulos Python. Examinei o código e os três exemplos; não li os testes do autor antes de escrever a verificação independente. Nenhum arquivo da adaptação foi alterado nesta revisão.

**Resultado: 25 testes independentes aprovados**, sem falhas. O teste está em `independent_replay_review.py`; log em `independent-replay-review.log`; hashes dos módulos em `independent-reviewed-source-sha256.json`. Core SHA256: `4150b00450384ded46d324246ab3fee035f7c3121e92a93479e7f7818ff38c5c`.

Coberturas verificadas:

- Entrada usa o preço da segunda sessão; alterar o preço da primeira não cria lucro retrospectivo.
- Conta sem custos/preço constante retorna zero. Custo ida/volta com preço constante confere com fórmula independente `capital * (1-fee)/(1+fee) * (1-slip)/(1+slip)`.
- Caixa total e parcial permanecem em caixa e não cobram taxas sobre valor não investido.
- Série idêntica ao benchmark, 100% investida, com taxas iguais, produz resultados idênticos.
- Drawdown usa pico→vale, inclui o capital inicial e o custo da liquidação final. Cenário intermediário de queda 50% e recuperação mantém drawdown de 50%.
- Valores máximos/mínimos admitidos permanecem finitos sob Decimal.
- Futuro documental declarado, sessão de entrada incorreta, decisão na/apos disponibilidade da entrada, números JSON, não finitos, pesos fora do intervalo, chaves duplicadas, URLs externas/query/credenciais/porta, datas inválidas, preços zero, entrada excessiva e aninhamento excessivo são recusados.
- Saída não ecoa IDs, nomes dos ativos, URL ou texto de evidências fornecidos. `execution_allowed:false`, revisão pendente e autenticidade dos timestamps não confirmada permanecem explícitos.
- Entrada symlink/FIFO/diretório/excessiva e saída symlink/ancestral symlink/existente são recusadas; arquivo existente preservado; nova saída usa modo 0600.

Não identifiquei defeito bloqueador no recorte implementado. A versão final usa contexto Decimal próprio, com precisão 50 e ROUND_HALF_EVEN, e calcula a diferença em pontos percentuais antes de arredondar o texto da saída. Os mesmos 25 testes independentes foram reexecutados após essa estabilização e passaram; o manifesto registra a versão final.

Esta revisão usa preços, evidências e timestamps fictícios. Não homologa recomendação, corretora, autenticidade das declarações, qualidade de modelos, alpha, produção ou comportamento de mercado. A comparação com benchmark 100% investido usa taxas iguais, mas não iguala exposição a risco quando o portfólio mantém caixa. As limitações no relatório do motor deixam o escopo explícito.
