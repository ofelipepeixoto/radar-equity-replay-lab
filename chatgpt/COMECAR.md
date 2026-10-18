# Começar no ChatGPT

1. Criar um projeto chamado **Radar Equity Replay Lab**.
2. Copiar INSTRUCOES.md para as instruções do projeto. Adicionar docs/CONTRACT.md, um exemplo JSON e os arquivos do motor acessíveis no ambiente de código, ou um relatório já calculado.
3. Pedir a análise de um exemplo fictício. Conferir quais arquivos foram lidos e se houve execução real. Se não houver ferramenta de código, usar a explicação qualitativa, sem dizer que o programa foi testado.

Mensagem sugerida:

> Use os arquivos do Radar Equity Replay Lab. Execute o exemplo fictício, se o ambiente permitir. Explique o que muda ao entrar apenas em T+1, mostre custos, retorno e maior queda versus o benchmark. Separe cálculo de hipóteses e não transforme o resultado em recomendação ou ordem. Se não executar o código, declare isso.

Outros exercícios: comparar o mesmo exemplo com custo zero e com custos; analisar o cenário de perda; observar uma carteira só de caixa; fornecer evidência posterior à decisão e confirmar sua recusa. Salvar resultados em arquivos novos, sem sobrescrever a entrada.

## Caderno visual e nova evidência de execução

Com o motor disponível no ambiente de código, gerar um arquivo HTML novo:

```sh
PYTHONPATH=src python3 -m radar_equity_replay.workbook examples/replay.json --output /tmp/replay-workbook.html
```

O caderno oferece as quatro escolhas iniciais, comparação com custo zero,
curva/drawdown, cronologia UTC, limites e download do JSON sanitizado.
Os cálculos são feitos pelo Python; o navegador apresenta o resultado.
HTML já gerado não prova execução na conversa que o abriu. Para nova execução,
usar a CLI acima e registrar o comando e o hash exato da entrada.

Para conferir os três exemplos e custo zero por um método independente:

```sh
mkdir -p results
PYTHONPATH=src python3 tools/run_exercises.py --output-dir results/nova-conferencia
```

Não repetir com o mesmo nome de pasta. O arquivo `run.json` registra as quatro
execuções da CLI, recusas esperadas, versões e hashes. Relatos de sessões
anteriores continuam sendo declarações históricas, não execução desta conversa.

Não anexar extratos, posições reais, credenciais ou dados pessoais. Não há conexão automática a corretora, dados de mercado, modelo pago ou n8n. A versão é uma hipótese de laboratório, não substitui a aplicação completa upstream e não foi instalada automaticamente na sua conta.

Guia oficial consultado em18/10/2026: [projetos e conversas do ChatGPT](https://learn.chatgpt.com/docs/projects). Fontes/instruções são compartilhadas no projeto; um projeto por si não concede acesso a pastas locais ou ferramentas de execução. A disponibilidade precisa ser conferida na sessão.

Aceite pendente: um segundo operador humano repetir os três exemplos numa conversa nova e conferir os números com a metodologia. Ensaio com agente e CI não substituem esse aceite.
