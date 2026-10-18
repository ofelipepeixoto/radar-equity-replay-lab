# AI Hedge Fund — mapa de sobreposição no ecossistema Radar

Data da inspeção: 2026-10-18 UTC. Trabalho somente leitura. Nenhum repositório existente foi alterado, nenhum conector foi ativado e nenhum conteúdo privado foi coletado para estas notas. Contagem geral fornecida pelo coordenador: 53 repositórios acessíveis, 42 públicos antes de qualquer criação nesta tarefa. A inspeção abaixo aprofundou sete repositórios públicos; não equivale a auditoria completa dos 53.

## Base externa fixada

- `virattt/ai-hedge-fund` em `78b779c1389e2d1452dc29606d2c4126d859b964` (HEAD do clone público conferido).
- [LICENSE](https://github.com/virattt/ai-hedge-fund/blob/78b779c1389e2d1452dc29606d2c4126d859b964/LICENSE): MIT, copyright 2024 Virat Singh. Atribuição e texto da licença precisam acompanhar cópias/porções substanciais. Dados, marcas, serviços e prompts de terceiros continuam sujeitos a direitos próprios.
- README raiz declara finalidade educacional e pesquisa, não realização de operações reais. Mostra CLI/TUI, paper trading e backtesting. `hedge_fund/README.md` identifica o núcleo v2 como trabalho em progresso; esse estado não deve virar alegação de maturidade.
- Código inspecionado em `hedge_fund/pipeline/stages.py`, `risk/limits.py`, `data/protocol.py` e `llm/contract.py`: separação entre parecer/sinal, construção, limites determinísticos e execução simulada; protocolo de dados distingue indisponibilidade verdadeira de falha de infraestrutura; datas de publicação entram no contrato point-in-time; validade estrutural/confiança do modelo não é probabilidade de lucro.
- Essas observações são inspeção de código. Não comprovam correção financeira, dados point-in-time de provedores reais, rentabilidade ou prontidão operacional.

## Pins e estado encontrado

| Repositório público | Revisão principal inspecionada | Estado e evidência | Sobreposição / papel adequado |
|---|---|---|---|
| `TradingAgents` | main `8b22d43d01d9ddda5d686d093d5385884622f3de`; laboratório `d7f46ac76fbd7f442c1aebab0f65bb28f751300d` | Fork Apache-2.0 da TauricResearch. PR #1 aberta, não rascunho; laboratório ainda em branch separada. Main tem 204 arquivos. | Maior sobreposição: pesquisa financeira multiagente e laboratório português de teses/riscos. Usar como comparador de qualidade e referência; não criar outro grafo de personas como diferencial novo. |
| `capital-web3-advisor` | main `c412fa3b89b79fd86a85cc1f7996fd1c40e90eb8`; branch UX atual `8368ebf9254875f6166a3b0d46354ae495cbfe54` | Main tem 14 arquivos e orientação para branches. PR #17 aberta para `feat/cofre-auth-controls`. README da branch registra homologação sintética cloud, COFRE, Auth/MFA/RLS/Edge v5/Site v6. Não executei homologação novamente. | Produto de consultoria DeFi, entrega privada e revisão por versão. Preservar esse domínio; novo laboratório de ações não deve copiar portal, identidade ou diagnósticos. |
| `radar-evidence-kit` | main `22d3cae88f1a43f55f75d880bbe6b46d5582d0ba` | MIT, núcleo stdlib. 28 arquivos. `Evidence`, `Scope`, checks e recibos SQLite. | Maior potencial compartilhado: identidade de fonte/artefato, versão, hash e revisão. Um contrato próprio semelhante não representa integração real ao SDK. |
| `radar-model-router` | main `f9533a43af86729696c5cd9980adec223beb3410` | MIT com política numérica de terceiro atribuída. 36 arquivos. `Router.route` é serviço de metadados, persistência local, sem execução de modelos. | Futuro roteamento e orçamento governado de chamadas. Não é adaptador de LLM, autenticação ou autorização. Desnecessário importar no primeiro fluxo ChatGPT sem API. |
| `radar-integration-hub` | main `d7084bdf63fcea9cf13ad1c5b3254c828b2cb6e2` | MIT, 54 arquivos. CRM preview fictício, bindings no backend, ações allowlisted e governança SQLite preparada. | Futuro conector de dados autorizado e orçamento, após autenticador, escopo e homologação. Hoje não há conector financeiro nem MCP financeiro conectado. |
| `radar-oaas` | main `aceb046431fa199222f72fb2091c0b63a992102f` | Astro 7/React, avaliação determinística de prontidão; 232 arquivos. Licença proposta pendente, `UNLICENSED`/NOASSERTION. | Pode avaliar hipótese de produto/adoção do laboratório. Não calcula alpha, risco de mercado ou suitability. Não copiar código como se fosse MIT concedida. |
| `radar-agent-observatory` | main `4eedb3bb3b9ce30acca1e2e4dbd922ee7c6ce987`; viewer `c617d50a86745c0c394dbe64001d87cdbd25f18f`; static `dccdbb069e7131c20d79cdb22d4fe17334e3d422` | Main só README. PRs #1/#2 abertas em rascunho. Viewer original MIT declarado na branch, fixtures sintéticas, loader de URLs fixas. | Possível visualização futura de recibos resumidos. Não há telemetria real nem importação genérica pronta; contrato atual recusa `mode: live`. |

## Evidências precisas de maior sobreposição

### TradingAgents: já existe um Radar de Teses e Riscos

[Guia fixado do laboratório](https://github.com/ofelipepeixoto/TradingAgents/blob/d7f46ac76fbd7f442c1aebab0f65bb28f751300d/docs/radar-lab/README.md), [PR #1](https://github.com/ofelipepeixoto/TradingAgents/pull/1).

- Operador fornece trechos de fontes; relatório em português, prévia HTML escapada e revisão humana por hash.
- Demo sem dependências, chaves ou API; dados fictícios. Não percorre URLs.
- Uma geração estruturada, fora do grafo TradingAgents. Adaptador OpenAI preparado com transporte simulado e ativação manual, ainda sem homologação real declarada.
- Revisão local com identidade declarada, prazo de 24h e exportação Markdown; isso não autentica pessoa nem concede poderes de publicação/ordem.
- Orçamento conservador local e persistente; não é teto financeiro de toda conta/API.

Consequência: criar outro laboratório focado apenas em “teses + contrapontos + aprovação” duplicaria esse trabalho. Se um novo repositório for criado para atender ao pedido explícito, o recorte deve ser um pacote portátil de dados e cálculo de carteira hipotética para ChatGPT. O comparador TradingAgents deve aparecer logo no README.

### Capital Web3: não tratar como projeto parado no protótipo local

[Arquitetura na main fixada](https://github.com/ofelipepeixoto/capital-web3-advisor/blob/c412fa3b89b79fd86a85cc1f7996fd1c40e90eb8/docs/architecture.md), [README UX atual fixado](https://github.com/ofelipepeixoto/capital-web3-advisor/blob/8368ebf9254875f6166a3b0d46354ae495cbfe54/README.md), [motor de risco fixado](https://github.com/ofelipepeixoto/capital-web3-advisor/blob/8368ebf9254875f6166a3b0d46354ae495cbfe54/capital_web3/risk.py).

- A branch atual documenta homologação cloud sintética, portal COFRE guiado, revisão/publicação e Auth/MFA/RLS; gates para clientes reais continuam pendentes.
- `capital_web3/risk.py` já tem Decimal, NAV com dívida, concentração por token/rede/protocolo/issuer/bridge/custodian/strategy, stress, IL 50/50 e CLAMM.
- Consequência: não anunciar cálculo básico de NAV/concentração como tecnologia inédita do ecossistema. Novo módulo pode trabalhar com snapshot de ações e cenários declarados, preservando escopo e diferenças de domínio.
- README declara licença comercial/distribuição ainda a definir; ser público não concede licença permissiva a consumidores externos. Não portar esse motor para o novo repo nesta etapa.

### Contratos compartilhados têm significado limitado

- [Evidence/Scope](https://github.com/ofelipepeixoto/radar-evidence-kit/blob/22d3cae88f1a43f55f75d880bbe6b46d5582d0ba/src/radar_evidence/modelos.py) e [check_evidence](https://github.com/ofelipepeixoto/radar-evidence-kit/blob/22d3cae88f1a43f55f75d880bbe6b46d5582d0ba/src/radar_evidence/checks.py): limite de texto 16 KiB, hash do texto completo, span por pontos Unicode, revisão/identidade fornecidas pelo aplicativo confiável; hash não prova verdade ou autoria.
- [Router service](https://github.com/ofelipepeixoto/radar-model-router/blob/f9533a43af86729696c5cd9980adec223beb3410/radar_router/service.py) e [contratos de ecossistema](https://github.com/ofelipepeixoto/radar-model-router/blob/f9533a43af86729696c5cd9980adec223beb3410/docs/ECOSYSTEM.md): não chama modelos nem serviços. Importar SDK no futuro deve ter pin, licença, testes e fronteira de confiança.
- [Governance Hub](https://github.com/ofelipepeixoto/radar-integration-hub/blob/d7084bdf63fcea9cf13ad1c5b3254c828b2cb6e2/src/governance.mjs): ações permitidas atualmente são rascunho/revisão, não operações financeiras. Autenticador de produção deve ser fornecido por backend confiável.
- [Observatory contract](https://github.com/ofelipepeixoto/radar-agent-observatory/blob/c617d50a86745c0c394dbe64001d87cdbd25f18f/docs/CONTRACT.md): até 50 registros, 128 KiB e cinco referências/registro; somente synthetic/historical; schema não autentica fonte, resultado ou autorização.

## Decisão recomendada para novo repositório solicitado

Nome preferido: `radar-equity-research` (ou `radar-portfolio-lab` se a prioridade for carteira hipotética multiclasse). Descrição: “Laboratório educacional para validar snapshots de ações e estudar carteira hipotética com cálculos reproduzíveis e revisão de evidências no ChatGPT.” Evitar “hedge fund autônomo”, promessa de rentabilidade ou aparência de gestora/investidor famoso.

Recorte distinto mínimo:

1. Upload/arquivo local com `as_of`, moeda, origem/data conhecida, preços e posições/hipóteses; dados fictícios nos exemplos.
2. Contratos estritos e limites, recusando futuro/incompatibilidade de datas, duplicatas e valores não finitos; não inferir qualidade de fonte só por URL/hash.
3. Aritmética determinística para valor da carteira, caixa, concentração e stress definido pelo operador; registrar hipóteses, sem sinal de compra/venda ou ranking artificial de confiança.
4. Relatório derivado para ChatGPT com evidências IDs e perguntas abertas, separando resultado calculado, alegação da fonte, interpretação e lacuna.
5. Guia de projeto ChatGPT e roteiro de segundo operador; nada de chave paga, n8n, feed de cotações ou broker no primeiro marco.
6. Eventual integração ao Evidence Kit deve usar consumidor real e testes. Até lá, documentar somente compatibilidade conceitual. Relatório local com hash não é cadeia autenticada nem revisão independente.

Não acrescer neste marco: outro portal privado, nova biblioteca genérica de governança, servidor MCP, coleta contínua, fund manager autônomo, broker, DeFi/wallet, n8n ativo, fine tuning, RAG ou banco vetorial.

## Fork versus implementação original

| Opção | Quando serve | Custo / risco | Decisão |
|---|---|---|---|
| Fork completo MIT do AI Hedge Fund | Contribuir upstream e estudar o motor paper/backtest preservando histórico | Importa árvore grande, dependências, contratos externos e dois estágios/v1-v2; não significa autoria própria exclusiva | Útil só se houver objetivo explícito de manutenção do upstream, não obrigatório para adaptação ChatGPT |
| Implementação original pequena | Entrada offline, cálculos determinísticos e pacote ChatGPT, com comportamento e testes próprios | Tem menos funcionalidades; precisa declarar que não é o motor original/“AI Hedge Fund completo” | Preferida para o pedido de novo repo e autoria; atribuir upstream como referência de padrões, licenciar só código original e rastrear qualquer trecho copiado |
| Módulo em TradingAgents existente | Evolução das teses/contrapontos e avaliação de LLM com custos/revisão | Menor duplicação, mas não satisfaz literalmente o novo repo pedido | Melhor alternativa técnica se o escopo se reduzir a teses/LLM; comparar antes de aumentar agentes |
| Módulo no Capital Web3 | Diagnóstico privado de carteira DeFi com entrega cliente | Mistura objetivos caso se injete estratégia de ações/backtesting sem requisito | Preservar domínio e roadmap; estudar interfaces futuras, sem alteração nesta tarefa |

## Score de encaixe (avaliação técnica contextual, não ranking global)

Escala 0–10; escores não são benchmark de retorno, segurança ou readiness.

| Dimensão | Nota | Razão |
|---|---:|---|
| Aprendizado de contratos e separação de estágios | 8 | Sinal versus sizing, risco determinístico, registros por sessão, dados temporalmente restritos são referências concretas úteis. |
| Novo recorte ChatGPT offline proposto | 8 | Adequado ao uso leigo/stdlib e reduz custo inicial, se declarar carteira hipotética e limitações. |
| Novidade de um segundo grafo financeiro multiagente | 3 | TradingAgents e Radar de Teses e Riscos já cobrem grande parte. |
| Integração imediata de provedores/brokers em produção | 2 | Autorização, dados/licenças, isolamento, orçamentos e desempenho real não foram homologados aqui. |
| Sinergia conceitual com Evidence Kit | 9 | Identidade de artefato, versão, recusa/pendência e recibo são padrões diretamente úteis, com consumidor ainda a desenvolver. |
| Sinergia como módulo imediato no Capital DeFi | 4 | Compartilha cálculos e revisão, mas domínio de ações/backtest difere do COFRE/DeFi. |

Recomendação de adoção para o upstream: **C — EXTRACT**, condicionada aos achados de segurança/testes da auditoria principal. O experimento novo deve permanecer limitado e explicitamente distinto. Não houve integração entre esses projetos nesta inspeção.

## Método e limites

Metadados públicos, branches, árvores completas da main, PRs abertas de TradingAgents/Capital/Observatory e READMEs/arquivos fixados foram lidos pelo conector GitHub. Arquivos do upstream foram lidos do clone público no commit fixado. Tree API não foi truncada nas sete main inspecionadas. Não executei testes dos sete projetos, não alterei branches, não validei novamente o portal hospedado e não consultei dados financeiros privados. Alegações de CI/homologação dos READMEs são documentação do projeto, não execução nova desta inspeção.
