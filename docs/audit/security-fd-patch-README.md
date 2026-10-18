# Patch candidato: fronteira HTTP do Financial Datasets

Base exata: `virattt/ai-hedge-fund@78b779c1389e2d1452dc29606d2c4126d859b964`.
Arquivo: `security-fd-boundary.patch` (170 linhas, duas alterações: cliente e seis testes de regressão).
SHA256: `fade90fed8e8407813f9f34da13f0c9a5cfc1dc53f50d2356582816ab74fb716`.

O patch foi aplicado somente à cópia `<WORKSPACE>/hedge-fd-patch`, não ao upstream original. `git apply --check` aprovou sobre o checkout original, que permanece limpo. Não houve commit, push, merge nem chamada de API real por este revisor.

Comportamento: requisições com credencial aceitam apenas HTTPS, hostname/porta exatos da origem configurada; userinfo/fragmentos/backslash/controles são recusados; redirects automáticos ficam desabilitados e todo 3xx é erro; paginação detecta URL repetida e impõe teto de100 páginas. Paginação legítima de mesma origem continua funcionando em mock.

Validação com os mesmos108 pins/hashes do lock upstream e guard de sockets, sem chaves:

- Seis novos testes focais aprovados (mais oito entradas malformadas como subcasos de um teste, não somadas ao total).
- Doze testes existentes de contrato aprovados.
- Trinta e cinco testes de integração foram ignorados porque não há chave. Total focado **18 aprovados,35 ignorados** (`security-fd-patch-regressions.log`).
- Não se reexecutou a suíte upstream inteira sobre o patch nem testes reais da API; não chamar o patch de homologado para produção.

Reprodução em clone isolado no commit base, após instalar o lock com hashes:

```bash
git apply --check security-fd-boundary.patch
git apply security-fd-boundary.patch
python -m pytest -q hedge_fund/data/test_client.py hedge_fund/data/test_client_contract.py hedge_fund/data/test_audit_fd_guard.py
```

Executar somente com ambiente sem credenciais e egress bloqueado para reproduzir os testes unitários; integração requer um marco separado e não foi autorizada por este patch.

Limites: não há teto de bytes/linhas, budget global de tempo, correção dos advisories urllib3, sandbox/DNS pinning, cache namespace, PIT local, paths nem locks de ledger. Teto100 é decisão conservadora de experimento, pode interromper feeds legítimos maiores e deve ser revisado antes de adoção. Esta mudança não impede acesso ao host legítimo caso o próprio host/DNS/TLS esteja comprometido. Outros achados permanecem abertos.

Código upstream mantém a licença MIT **Copyright(c)2024 Virat Singh**. Testes novos são originais, MIT, Copyright(c)2026 Carlos Felipe. O arquivo LICENSE upstream foi preservado na cópia de teste; anexar atribuição/licença se distribuir código substancial. Este patch não é herdado pelo motor original offline.
