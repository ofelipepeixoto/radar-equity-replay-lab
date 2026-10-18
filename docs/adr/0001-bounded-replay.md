# ADR0001 — Replay sintético antes de agentes e provedores

Status: aceito para o laboratório; não homologado para dados/ordens reais.

Contexto: o AI Hedge Fund contém TUI, modelos, caches e paper/backtest. O ecossistema já possui TradingAgents para teses/contrapontos e Capital Web3 para diagnósticos DeFi; duplicar agentes ou portal não acrescenta uma competência distinta. O pedido exige uma adaptação em novo repositório.

Decisão: implementar um replay buy-and-hold limitado, com pesos fornecidos, evidência temporal, entrada em T+1, custos e comparação consistente com benchmark. Núcleo Python stdlib e pacote de instruções para ChatGPT. Só dados fictícios; nenhuma rede, dependência runtime de terceiros, conta, API, ordem ou estado de broker.

Alternativas: fork completo preserva histórico, mas importa dependências/serviços e riscos sem resolver a primeira experiência; adaptar grafo TradingAgents repete trabalho; criar módulo Capital mistura domínio; introduzir MCP/web/Supabase agora amplia operação sem validar utilidade.

Consequências: não gera sinais ou valida alpha; cronologia declarada não prova origem dos dados/pesos; resultados são apenas hipóteses com custos simplificados. Dados futuros de preço são necessários para a marcação histórica, mas não orientam decisões no código. O operador/LLM pode conhecer o futuro: este laboratório não elimina esse viés externo.

Integração ao Evidence Kit exige contrato SDK real e teste; um hash próprio não é recibo autenticado. Qualquer conector passa por autorização/custos no Hub e homologação separada. Não ativar n8n para rodar continuamente este CLI.
