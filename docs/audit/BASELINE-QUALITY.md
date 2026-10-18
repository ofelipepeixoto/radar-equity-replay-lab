# Baseline de qualidade do AI Hedge Fund

Fonte inspecionada: `virattt/ai-hedge-fund`, commit `78b779c1389e2d1452dc29606d2c4126d859b964`. Data UTC: 2026-10-18.

## Inventário e stack

- 115 arquivos versionados; 95 arquivos Python, 27 deles `test_*.py`; 348 funções de teste antes da expansão de parametrizações; cinco YAML (mandato de exemplo + quatro estratégias).
- Python >=3.11; Poetry; Pydantic 2; LangChain e SDKs de provedores; NumPy/Pandas/SciPy; requests; Rich/Textual; CLI `aihf`.
- A interface presente neste commit é uma TUI Textual. Não há frontend web, Dockerfile, servidor MCP, AGENTS.md ou workflow em `.github/workflows/` neste snapshot. Há dois templates de issue.
- `poetry.lock`: 108 pacotes, sem fontes Git/URL especiais. O snapshot traz hashes dos artefatos. O inventário legível por máquina está em `inventory.json`.
- Desenvolvimento: pytest, black, isort, flake8. Não há ferramenta/configuração de type-check explícita; uma verificação estática de tipos não foi executada nem inventada.

## Isolamento dos testes

O conftest original chama `load_dotenv()`; 38 casos live podem consultar Financial Datasets se uma chave estiver presente. Antes da execução, foram inspecionados fixtures e transportes. Nenhum `.env` foi encontrado no diretório do repositório ou em seus ancestrais. A suíte foi executada com `env -i`, HOME exclusivo vazio, sem credenciais herdadas, com plugin autoload desativado, matplotlib Agg e um `sitecustomize` que recusa sockets Internet e DNS. A instrumentação é defesa do processo Python, não um sandbox de sistema.

Os testes de modelos externos constroem clientes com chaves falsas ou substituem chamadas por mocks. Os testes de paper/CLI usam FakeDataClient, SimBroker/PaperBroker em diretórios temporários e não executam paper com dados reais. O módulo foi testado; não se iniciou o aplicativo interativo real, daemon, conta de corretora ou chamada paga.

- **625 aprovados, 38 ignorados, zero falhas**, em 35,15 segundos.
- 35 ignorados: smoke tests Financial Datasets sem chave; três ignorados: um backtest e dois event studies live sem chave.
- **Zero tentativas de socket/DNS** registradas pelo guard durante a suíte. O guard foi confirmado carregado (`socket.socket.connect.__module__ == 'sitecustomize'`).
- `pip check`: **No broken requirements found**.
- Logs: `upstream-install.log`, `upstream-pip-check.log`, `upstream-pytest.log`, `upstream-junit.xml`, `baseline-environment.json`.

## Build e ferramentas de estilo

- Build de **sdist e wheel aprovado** (`aihf-2.5.0.tar.gz`, `aihf-2.5.0-py3-none-any.whl`) usando `build==1.5.0`, `poetry-core==1.9.1`, `--no-isolation`, guard ativo. Não executa o programa. Artefatos em `upstream-dist/` e log em `upstream-build.log`.
- Black 23.12.1 `--check`: **falhou**; 60 arquivos seriam reformatados, 35 não mudariam. Não apliquei alterações.
- isort 5.13.2 `--check-only`: **falhou** em 30 arquivos. Não apliquei alterações.
- flake8 6.1.0: **falhou**, 1.242 ocorrências. 1.196 são E501; a configuração Black aceita linha de 420 caracteres e não há configuração flake8 correspondente. Também há 10 E127, 10 E128, seis E203, um E302, um E303, 14 E306, um F401, um F541 e dois F841. Assim, não interpretar toda ocorrência como defeito funcional, nem declarar lint aprovado.
- Não há CI upstream neste commit. Teste local e build não provam CI remoto upstream.

## Backtesting: distinguir motores e limites

1. O caminho principal `backtest_fund`/`advance` separa avaliação T da execução no close subsequente. A suíte cobre timing/reconciliação/risco/ledger com fixtures. Compartilhar o código com paper comprova consistência mecânica sob os mesmos inputs; não comprova ausência universal de vieses ou rentabilidade.
2. O **harness por modelo `BacktestEngine.run_alpha`**, ainda exportado, chama `model.predict(ticker,d,data)` e entra no **mesmo close d**. Isto é otimista quando o sinal só está disponível após esse fechamento. A reprodução `reproduce_backtest_limits.py` confirma data de entrada igual à data do sinal; não acusa o caminho principal de fazer o mesmo.
3. No harness antigo, `run_alpha` ordena por data de entrada e `_build_equity_curve` soma P&L fechado nessa ordem. Uma amostra sintética produz `[1000,1100,900]` pela entrada versus `[1000,800,900]` pelo encerramento. Nenhuma dessas curvas é mark-to-market diário; o harness não controla exposição simultânea/capital entre tickers. `backtest-limits.json` registra os dois achados.
4. `SimBroker` usa preenchimento integral ao preço de referência. Slippage/custos e margem estão explicitamente ausentes/futuros. Essas simplificações reduzem a utilidade econômica de comparações com mercado real.
5. `FDClient.get_financial_metrics` envia `filing_date_lte`, mas a resposta não é refiltrada localmente. A prova atual do teste é sobre os parâmetros HTTP/mock; disponibilidade histórica, restatements e integridade do provedor real não foram validados.
6. `build_snapshot` usa `company_facts` mais recentes para setor/indústria; o próprio código documenta isto como aproximação PIT. O market cap usado pelo snapshot vem dos metrics, não do helper `get_market_cap` latest-only.
7. O modo cego esconde ticker, datas e valores absolutos e reduz memorização do LLM, mas o próprio `snapshot.py` reconhece que perfis distintos podem identificar a empresa. Não garante que um modelo treinado depois do período desconheça o futuro.
8. CPCV/PBO e promoção automática/validação de pesquisa são itens planejados no ROADMAP; não devem aparecer como funcionalidades homologadas. O comentário sobre Sharpe PEAD 0,33 é uma declaração do código, não resultado reproduzido nesta auditoria.
9. Qualidade de dados reais, ajuste por eventos corporativos, delistings/survivorship, correções posteriores e validade de inferência por personas exigem avaliação própria. Não foram medidos retornos reais, ganho de tempo, demanda ou alpha.

## Deriva documental

`hedge_fund/README.md` ainda descreve v2 não conectada e diretórios `src/`/`app/` de v1 que não existem neste commit. O ROADMAP menciona um scaffold de frontend web ausente do snapshot. O README principal reflete melhor a TUI atual. Registrar a divergência; não apresentar componentes ausentes como presentes.

## Reprodução

A exportação `upstream-locked-requirements.txt` é derivada de cada pin e dos hashes de `poetry.lock`; não atualiza dependências e foi usada com `pip install --require-hashes --only-binary=:all: --no-deps`. O `pip check` confirmou consistência dos 108 pins.

```bash
# Em venv de auditoria, sem instalar a aplicação nem iniciá-la:
python -m pip install --require-hashes --only-binary=:all: --no-deps -r upstream-locked-requirements.txt
python -m pip check
# Deve-se preservar env -i, HOME isolado e offline-guard do harness da auditoria.
python -m pytest hedge_fund/ -q --junitxml=upstream-junit.xml
python -m build --no-isolation --outdir upstream-dist
python -m black --check hedge_fund
python -m isort --check-only hedge_fund
python -m flake8 hedge_fund --count --statistics
```

Nenhum arquivo versionado do upstream foi modificado. Nenhum remoto foi escrito nesta subauditoria.

## Consulta de dependências

`pip-audit==2.10.1`, instalado em outra venv, consultou o serviço padrão de advisories PyPI para os **108 pins** exatos sem instalar nem resolver dependências do aplicativo: `python -m pip_audit --disable-pip --no-deps --require-hashes -r upstream-locked-requirements.txt --format json --output upstream-dependency-audit.json`. A consulta terminou com saída 1 por alertas: **18 registros em oito pacotes; 13 IDs de advisory distintos após remover repetições do mesmo ID**. Tabela e GHSA em `DEPENDENCY-ALERTS.md`; JSON normalizado em `dependency-audit-summary.json`. As ferramentas do scanner ficam fora da venv do baseline.

Pacotes sinalizados: black 23.12.1 e pytest 7.4.4 (desenvolvimento); langchain-anthropic 0.3.5, langchain-core 0.3.86, langchain-openai 0.3.35, multidict 6.7.1, python-dotenv 1.0.0 e urllib3 2.7.0 (runtime/transitivos). Versão afetada não é prova de exploração. Não foram instaladas atualizações nem reproduzidos exploits externos. A passagem para LangChain 1.x pode exigir migração funcional e regressão.

A inspeção compartilhada de segurança informa: app não usa `dotenv.set_key/unset_key`, nem middleware de filesystemsearch, contagem de tokens de imagens ou operações de união/subtração em items do multidict. Seus alertas específicos não foram demonstrados nestes fluxos. urllib3 é alcançado por requests e downloads; cenários streaming/proxy dependem de servidor/configuração hostis ou comprometidos e não foram explorados. Não classificar a ausência dessas rotas como ausência de todo risco do pacote.
