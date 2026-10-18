# Radar Equity Replay Lab

**Estude uma carteira fictícia no ChatGPT, com datas, custos e perdas visíveis.**

Laboratório educacional PT-BR de Carlos Felipe, com motor original MIT inspirado em padrões do [AI Hedge Fund](https://github.com/virattt/ai-hedge-fund/tree/78b779c1389e2d1452dc29606d2c4126d859b964). O operador fornece pesos hipotéticos; o programa entra somente no fechamento da sessão seguinte e compara o resultado com um benchmark usando os mesmos custos.

Não é fundo, gestora, consultoria individual ou cópia completa do AI Hedge Fund. Não escolhe ações, otimiza carteiras, gera ordens ou se conecta a corretora, dados de mercado ou LLM/API paga. **A versão aceita apenas cenários declarados fictícios**, com URLs de evidência `.invalid`; essa declaração não é autenticação do conteúdo.

## Usar no ChatGPT

Abra [o guia](chatgpt/COMECAR.md) e copie [as instruções](chatgpt/INSTRUCOES.md) para um projeto ChatGPT. Disponibilize os arquivos do motor e um exemplo em um ambiente de código autorizado, ou anexe um relatório já calculado. Se não houver execução de Python, peça apenas a explicação qualitativa e confira que o modelo declara essa limitação.

> Use o exemplo fictício. Explique a entrada em T+1, o efeito dos custos, o retorno e a maior queda versus o benchmark. Separe cálculo de hipóteses; não transforme o resultado em uma recomendação ou ordem real.

O guia está preparado; nada foi instalado automaticamente na sua conta. Um link de GitHub não instala código ou concede acesso a contas/pastas. CI e ensaio por agente não substituem a homologação por um segundo operador humano numa conversa nova.

## Três cenários reproduzíveis

Python3.11+ em Linux/POSIX com controles de arquivo no-follow. CLI Windows não homologado; plataforma incompatível é recusada. Sem dependências runtime de terceiros, credenciais ou configuração `.env`.

```sh
PYTHONPATH=src python3 -m radar_equity_replay examples/replay.json --output /tmp/equity-replay.json
PYTHONPATH=src python3 -m radar_equity_replay examples/loss.json --output /tmp/equity-loss.json
PYTHONPATH=src python3 -m radar_equity_replay examples/cash.json --output /tmp/equity-cash.json
```

Usar caminhos novos: arquivos existentes não são sobrescritos. Entrada até1MiB,1–20ativos,3–2.500sessões e1–50evidências. JSON estrito; dinheiro, preços, pesos e taxas são strings decimais. Exemplos são fictícios; o primeiro preço foi escolhido para tornar evidente que a entrada não pode ocorrer em T.

| Cenário | O que ensina |
| --- | --- |
| replay.json | Carteira parcial, caixa residual, custos de ida/volta e benchmark |
| loss.json | Perda e drawdown sem promessa de recuperação |
| cash.json | Peso zero mantém caixa sem juros/custos de ativos; benchmark continua investido |

No exemplo replay, capital fictício BRL1.000 resulta em BRL1.087,03444981 após os custos modelados; é aritmética de fixture, não resultado de investimento real.

O [contrato e as fórmulas](docs/CONTRACT.md) explicam unidades fracionárias, orçamento de entrada incluindo custos, marcação por fechamento e liquidação final. Não há rebalanceamento, dividendos, impostos, juros, câmbio, margem, short, liquidez ou impacto real. Comparação com benchmark não ajusta risco e não demonstra alpha.

## Resultado verificável

O relatório inclui hash da entrada, datas/metodologia, curvas, custos, retorno, drawdown, benchmark, ponteiros e limites. Sempre `review_status=pending` e `execution_allowed=false`. Não ecoa IDs, URLs ou texto de evidências. Hash não prova fonte, data, verdade, independência da escolha dos pesos ou autorização.

Evidência posterior à decisão é recusada. O código usa preços futuros somente para avaliação histórica dos pesos fornecidos; não é possível provar a partir desse arquivo que o operador ou um LLM não conhecia esses preços ao escolher os pesos. O motor não avalia uma tese, modelo preditivo ou habilidade de seleção.

## Desenvolvimento

```sh
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

**30 testes próprios e25testes independentes aprovados.** Testes cobrem T+1, custos por fórmula independente, caixa, benchmark comparável, drawdown, limites/tipos/valores extremos, rejeição de futuro e autoridade, privacidade de texto e IO sem sobrescrita/symlinks. Build wheel local aprovado. A CI executa testes e os três exemplos em Python3.11/3.12; resultados locais e remotos ficam registrados na PR.

Não confundir testes do laboratório com os625testes do upstream ou com os testes focais de um patch candidato de rede. O ambiente desta entrega não teve chamada paga, conta de corretora, feed real ou produção.

## Lugar no ecossistema

O `TradingAgents` já possui laboratório de teses/contrapontos; o Capital Web3 preserva seu domínio DeFi e portal. Este componente concentra-se em **replay temporal e avaliação de hipóteses**, sem outro grafo de personas, portal ou motor DeFi. Evidence Kit, Hub e Router são possibilidades futuras: não há integração SDK/MCP, banco ou n8n ativo aqui.

- [ADR de escopo](docs/adr/0001-bounded-replay.md)
- [Segurança e limites](SECURITY.md)
- [Contribuição](CONTRIBUTING.md)
- [Origem e atribuição](THIRD_PARTY_NOTICES.md)
- [Auditoria em30seções e evidências](https://github.com/ofelipepeixoto/radar-equity-replay-lab/blob/docs/ai-hedge-fund-audit/docs/Relatorio-AI-Hedge-Fund-2026-10-18.md), em PR independente.

Próximos marcos: revisão humana da PR e repetição dos exercícios por outro operador no ChatGPT; comparar números por método independente; só então decidir se há valor para um consumidor do ecossistema. Dados reais, conexão de modelos/feeds, broker, integração e comercialização são etapas separadas, não promessas desta versão.

MIT original de Carlos Felipe; MIT2024Virat Singh preservada em third_party/ai-hedge-fund/LICENSE. Não há endosso do autor upstream, investidores famosos ou provedores. Experimento em branch para revisão, sem merge/deploy/release estável automático.
