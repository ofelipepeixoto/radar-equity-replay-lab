# Reproduzir e interpretar evidências

Base upstream: virattt/ai-hedge-fund@78b779c1389e2d1452dc29606d2c4126d859b964. Ler BASELINE-QUALITY.md, baseline-commands.txt e security-review.md antes de rodar algo. Não executar o app `aihf`, dados live ou usar chaves reais para reproduzir esta auditoria.

Logs copiados tiveram o prefixo local `<WORKSPACE>` e espaços finais normalizados; o patch é preservado byte a byte e seu SHA256 está no README específico. Instalação/hashes do lock e isolamento usados estão descritos na baseline; não instalar a aplicação num ambiente com credenciais para repetir testes. Egress guard Python não é sandbox completo de sistema.

Com dependências do lock em ambiente isolado e PYTHONPATH apontando para o checkout fixado, executar os scripts de observação pelo caminho desta PR:

```sh
python3 security_reproductions.py
python3 reproduce_backtest_limits.py
```

Eles usam módulos do upstream, doubles e arquivos fictícios. Seis observações de segurança aprovadas e duas observações do harness significam comportamentos atuais reproduzidos; não são correções, aprovação financeira ou exploração de API real.

Para o patch de origem HTTPS FD, seguir security-fd-patch-README.md. Aplicar somente numa cópia descartável do commit base, sem credenciais, preservando licença MIT de Virat Singh. Foram18aprovados/35ignorados focais; a suíte625não foi reexecutada sobre o patch. As cinco outras falhas e dependências não são corrigidas por esse artefato.

A implementação original do replay está em PR independente. Em seu checkout, disponibilizar `src` e executar os25testes independentes:

```sh
PYTHONPATH=/path/to/radar-equity-replay-lab/src python3 /path/to/audit/independent_replay_review.py
```

Não misturar os30testes próprios com os625upstream ou com18do patch como se provassem uma integração. SHA dos módulos revisados está em independent-reviewed-source-sha256.json. A branch de auditoria não contém o runtime.

Os arquivos inventory.json,public-ecosystem.json,dependency-audit-summary.json,JUnit e logs são saídas geradas; não precisam de leitura linha por linha para revisar o código. Começar pelos resumos, depois scripts/patch e apenas os logs pertinentes. Benchmarks, contas reais, homologação ChatGPT e rentabilidade não fazem parte dessas evidências.
