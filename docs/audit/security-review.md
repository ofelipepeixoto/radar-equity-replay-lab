# Revisão independente — AI Hedge Fund

Data: 2026-10-18. Upstream `virattt/ai-hedge-fund`, commit `78b779c1389e2d1452dc29606d2c4126d859b964`.

O programa atual é uma CLI/TUI Python (`aihf` 2.5.0), com backtest e broker **simulado** persistente. Não é a antiga aplicação web. Nenhum broker real identificado nesta versão. Esta revisão não alterou o checkout upstream e não publicou alterações. `AGENTS.md` não encontrado no checkout ou nos diretórios pesquisados do workspace.

Seis observações reproduzidas por `security_reproductions.py`, com dados fictícios, diretórios temporários e HTTP inteiramente em mock. O próprio script recusa conexões socket. Resultado **6/6 observações confirmadas** (`security-reproductions.log`). Os testes afirmam o comportamento defeituoso observado; não são seis correções nem aprovação de segurança.

## SEC-01 — Paginação aceita origem diferente e preserva chave da API

Componente: `hedge_fund/data/client.py:238–275`. **Mecanismo confirmado em mock; exploração externa não testada.** Prioridade alta para conector com credencial; severidade condicional alta se resposta do provedor/intermediário confiado puder ser controlada.

`next_page_url` é solicitado literalmente. A mesma Session contém `X-API-Key`; não há validação de esquema, origem ou porta, e redirects são automáticos por padrão. Uma primeira resposta fictícia com `next_page_url=http://foreign.invalid/page-2` fez a segunda requisição preparada carregar a chave fictícia para essa origem.

Condições: fornecedor comprometido, fixture/conector não confiável ou resposta adulterada. Não demonstrado que a API legítima retorna tal URL; usuário final não controla diretamente esse campo na CLI. Impacto: divulgação de chave e requisições fora da origem prevista.

Correção: HTTPS e origem exata, sem userinfo/fragmentos/controles; recusar redirects; detectar ciclos e limitar páginas. Limitar também bytes/linhas/tempo permanece necessário. Prefixo textual de URL não é allowlist segura.

## SEC-02 — Temporário previsível segue symlink

Componente: `hedge_fund/paths.py:43–49`, usado por book/ledger/controle. **Confirmado localmente**, severidade média dependente de acesso ao diretório de dados.

`write_atomic(book.json,...)` grava `.book.json.tmp` com write_text, seguindo symlink pré-criado. A reprodução alterou somente arquivo fictício no TemporaryDirectory; depois do replace, book.json também se tornou symlink.

Condição: outro processo/usuário consegue inserir arquivos no diretório. Não é escrita remota nem elevação de privilégio demonstrada. Impacto: corrupção de arquivo fora do destino lógico e inconsistência. Ausência de lock por fundo também é risco estático de concorrência; corrida não reproduzida.

Correção: temporário único com criação exclusiva/modo restrito, rejeição de links, flush/fsync e rename seguro; confinar diretórios e serializar operações compostas por fundo. Rename atômico não é transação de tick.

## SEC-03 — Nome de mandato escapa de research

Componentes: FundSpec.name e `hedge_fund/run.py:208–211`. **Confirmado com `_backtest` e cálculo/transporte em doubles.** Severidade média para YAML importado não confiável; baixa quando toda configuração é do próprio operador.

O nome `../synthetic-escaped` passou na validação e o caminho automático gravou JSON fora de research no diretório temporário pai, sem usar --out. Flag explícita --out é escolha do operador e não é o achado. Nome de implantação paper possui validador próprio; nome de mandato é diferente.

Impacto: escrita fora do diretório previsto; nome absoluto também anula raiz lógica. Sufixo de data/timestamp limita nomes exatos atingíveis. Correção: separar nome humano/ID de arquivo, gerar slug seguro, validar confinamento e recusar sobrescrita.

## SEC-04 — Cache mistura provedores

Componente: `hedge_fund/data/cached.py:116–133,167–171`. **Confirmado com duas fontes falsas.** Severidade média de pesquisa, dependente de reutilizar mesmo diretório entre fontes/versões/tenants.

Dois CachedDataClient no mesmo cache, método e parâmetros iguais, geraram a mesma chave. Fonte B com valor fictício200 recebeu100 da fonte A; B nem foi consultada. CLI padrão tem um FDClient: ocorrência não universal.

Impacto: pesquisa não corresponde à fonte/versão declarada. Correção: namespace explícito não secreto de provedor/origem/contrato/tenant, identidade no envelope, validação e refresh. Não inserir chave secreta no namespace. Cache/hash não comprovam autenticidade.

## SEC-05 — get_market_cap acessa atributo ausente

Componente: `hedge_fund/data/client.py:207–214` e modelo CompanyFacts. **Confirmado**, severidade baixa funcional.

CompanyFacts(ticker='SYNTH') é válido, mas não tem market_cap; helper levanta AttributeError antes de consultar métricas. Campos extras do JSON são ignorados. Snapshot atual evita esse helper; não se afirma que todos os backtests falham.

Correção: usar métrica arquivada filtrada pelo cutoff; não inserir market cap atual em análise histórica. Se facts atuais forem necessários, manter caminho explícito inelegível para PIT.

## SEC-06 — Snapshot não revalida cutoff do provedor

Componente: `hedge_fund/features/snapshot.py:191–225`. **Mecanismo confirmado com fonte falsa; não confirma vazamento de futuro da API legítima.** Severidade média condicional de pesquisa.

Snapshot as_of2020 aceitou quatro linhas com filing_date2030. FDClient envia filing_date_lte à API; fronteira local confia no retorno e em qualquer implementação/cache. Condição: fonte/fixture/adaptador quebra contrato. Setor/indústria atuais são aproximação PIT já documentada.

Correção: validar ticker, período, data de publicação conhecida <=as_of; recusar futuro/data ausente; ordenar/deduplicar e identificar revisão da fonte. Rotular aproximações e risco de memória do LLM.

## Controles e limitações

- Jev tem endpoint fixo, redirects desabilitados, duas tentativas, timeout finito e redação de chave ecoada. Falha contratual abstém; API não chamada.
- Credenciais recebem0600 e shell tem precedência. Entrypoint lê .env local explicitamente; recorte educacional deve eliminá-lo. Nenhum segredo do operador lido.
- apply_limits recusa NaN/Inf; validate_targets revalida mandato, contribuição, long-only, short e neutralidade; execute_decision confere exposição projetada antes dos fills.
- SimBroker recusa preço não finito/não positivo. Margem, slippage, impacto, comissões, aluguel e liquidez não modelados, conforme código. Isso limita interpretação financeira e não é perda real demonstrada.
- Sessões separam assessment/execução e conferem book/ledger. Nenhuma lucratividade/validade de estratégia inferida.
- Ledger encadeado detecta edição simples, mas não tem assinatura/âncora externa. Dono do disco pode regravar registros e recalcular cadeia. Hash não prova autoria/autenticidade/imutabilidade.
- Sem testes reais de broker, dados completos, providers, GPU, multiusuário, produção ou navegador nesta revisão.

## Advisories oficiais focais

Consulta focal, não contagem final nem scanner completo. Outro revisor consulta108 pins.

- https://github.com/langchain-ai/langchain/security/advisories/GHSA-gr75-jv2w-4656 declara langchain-anthropic<=1.4.5, correção1.4.6, para file-search/config loaders. Lock0.3.5 cai no intervalo declarado. Aplicativo não expõe esses componentes; alcance não comprovado; não se afirma existência de todas essas APIs na versão antiga.
- https://github.com/langchain-ai/langchain/security/advisories/GHSA-r7w7-9xr2-qq2r declara langchain-openai<1.1.14, correção>=1.1.14, para token counting de imagens. Lock0.3.35 no intervalo; upstream usa mensagens textuais e não chama essa contagem. Alerta de faixa, não exploração confirmada.
- https://github.com/langchain-ai/langchain/security/advisories/GHSA-pjwx-r37v-7724 afeta legado até0.3.84; lock langchain-core0.3.86 não deve receber esse aviso focal.

Não usar CVSS próprio ou transformar alerta de dependência em exploração. Upgrade LangChain exige compatibilidade conjunta; major isolada não é drop-in. Adaptação offline não necessita dessas dependências.

## Licença, dados e marcas

LICENSE: **MIT, Copyright(c)2024 Virat Singh**, conferido literalmente. Atribuição e licença acompanham cópias/partes substanciais. README declara finalidade educacional, não trading real; registrar finalidade sem emitir conclusão jurídica.

MIT do código não licencia automaticamente feeds financeiros, APIs, Kenneth French, exports de clientes ou serviços/modelos. Verificar termos antes de coletar/redistribuir/comercializar. Nenhum dado real baixado nesta revisão.

Personas de investidores não indicam endosso, afiliação, aconselhamento ou reprodução fiel. Na adaptação original, usar papéis genéricos, casos fictícios e atribuição quando houver código copiado; não reutilizar imagem/marca como própria.

## Recorte seguro ChatGPT

Motor original pequeno offline, biblioteca padrão, sem credenciais/env de provedores, rede ou broker. JSON estrito/limitado; símbolos fictícios; published_at<=as_of; Decimal para dinheiro; recusa duplicatas/NaN/Inf/datas inválidas; métricas descritivas verificáveis. Nenhuma compra/venda, peso-alvo ou recomendação de investimento real. Saída com identidade/hash/limitações e revisão humana. Testes unitários não são resultado financeiro.

Ensinar rastreabilidade de cenários/avaliação de hipóteses no Capital Web3 Advisor existente. Não criar novo gestor autônomo, conectar conta, operar ativos, ativar n8n ou chamar APIs pagas.

## Adendo: patch parcial e alcance de dependências

Patch candidato FD preparado em cópia isolada, sem aplicar ao checkout original: `security-fd-boundary.patch`. **18 testes focais aprovados e35 ignorados** (12 existentes+6 novos; casos de URL malformada são subcasos, não oito testes adicionais). `git apply --check` passou. Não corrige outros cinco achados, limite de bytes, dependências ou produção. Ver `security-fd-patch-README.md`.

python-dotenv set_key/unset_key não são chamados pelo aplicativo: GHSA correspondente é alerta de dependência, não confirmado no caminho atual de salvar credenciais. Black/pytest são ferramentas dev; multidict items-view unions/subtractions não encontrados no aplicativo (não há servidor aiohttp próprio). Upgrade e hardening dev ainda recomendados.

urllib3: fontes oficiais https://github.com/urllib3/urllib3/security/advisories/GHSA-vxq7-64xx-v4gw e https://github.com/urllib3/urllib3/security/advisories/GHSA-gh4c-6fx4-qh6g confirmam condições chunked/deflate e correção2.8.0. Lock2.7.0 está nos intervalos. Inspeção de requests2.34.2 instalado confirma que Response.content usa iter_content e raw.stream(decode_content=True), mesmo com stream=False no request; clientes FD/ZIP portanto podem atingir a fronteira indiretamente se receberem resposta maliciosa. Isso é alcançabilidade estática, não exploração reproduzida. https://github.com/urllib3/urllib3/security/advisories/GHSA-8988-9cw3-xx77 exige modos de HTTPS proxy/políticas TLS específicos; upstream não fornece contexts customizados, configuração real não verificada. Nenhum segredo/proxy do operador inspecionado.
