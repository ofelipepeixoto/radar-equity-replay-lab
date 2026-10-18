"""Offline educational workbook for a validated, synthetic replay.

All financial calculations stay in Python Decimal. No supplied text, URL or
identifier is copied to the HTML. The browser only navigates a local document.
Original implementation by Carlos Felipe, MIT.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import html
import json
import sys
from decimal import Context, Decimal, ROUND_HALF_EVEN, localcontext

from .core import InvalidInput, analyze
from .io import read_input, write_report


def _escape(value: str) -> str:
    return html.escape(value, quote=True)


def _decimal_text(value: str | Decimal, places: int = 2) -> str:
    number = Decimal(value)
    rounded = number.quantize(Decimal(1).scaleb(-places))
    if rounded == 0:
        rounded = abs(rounded)
    integer, _, fraction = format(rounded, f",.{places}f").partition(".")
    return integer.replace(",", ".") + ("," + fraction if places else "")


def _money(value: str | Decimal, currency: str, places: int = 2) -> str:
    return _escape(currency) + " " + _decimal_text(value, places)


def _percent(value: str | Decimal, places: int = 4) -> str:
    return _decimal_text(value, places) + "%"


def _sum_costs(portfolio: dict) -> Decimal:
    return sum((Decimal(value) for value in portfolio["costs"].values()), Decimal(0))


def _drawdown_rows(portfolio: dict) -> list[dict]:
    """Presentation drawdowns use the published eight-decimal curve values."""
    initial = portfolio["initial_capital"]
    rows = [{"date": "—", "phase": "initial_capital", "nav": initial}]
    rows.extend(portfolio["curve"])
    peak = Decimal(initial)
    result = []
    for row in rows:
        nav = Decimal(row["nav"])
        peak = max(peak, nav)
        result.append({**row, "drawdown": (peak - nav) / peak * 100})
    return result


def _chart(portfolio: dict, benchmark: dict) -> str:
    """SVG coordinates come only from sanitized report numbers, never JavaScript."""
    groups = []
    for item in (portfolio, benchmark):
        groups.append([(Decimal(0), Decimal(item["initial_capital"]))] + [
            (Decimal(row["session_index"]), Decimal(row["nav"])) for row in item["curve"]
        ])
    values = [value for group in groups for _, value in group]
    low, high = min(values), max(values)
    padding = (high - low) / 8 if high > low else max(high / 20, Decimal("0.01"))
    low, high = low - padding, high + padding
    last_index = groups[0][-1][0]
    lines = []
    for group, color in zip(groups, ("#126a62", "#5163a6")):
        points = []
        for index, value in group:
            x = Decimal(56) + index / last_index * 808
            y = Decimal(200) - (value - low) / (high - low) * 164
            points.append(f"{x:.3f},{y:.3f}")
        lines.append(f'<polyline fill="none" stroke="{color}" stroke-width="3" stroke-linejoin="round" points="{" ".join(points)}"/>')
    return '<svg class="curve-chart" viewBox="0 0 920 238" role="img" aria-labelledby="chart-title chart-description"><title id="chart-title">Curva da carteira e do benchmark</title><desc id="chart-description">Valores calculados no Python. A liquidação ocupa a mesma posição horizontal da última sessão; ela não é um pregão adicional. A tabela a seguir contém os valores.</desc><path d="M56 24V201H864" stroke="#ced8d8" fill="none"/><path d="M56 112H864" stroke="#e7eceb" stroke-dasharray="4 5"/>' + "".join(lines) + '<text x="56" y="226" fill="#526569" font-size="13">Capital inicial</text><text x="864" y="226" text-anchor="end" fill="#526569" font-size="13">Última sessão + liquidação</text></svg>'


def _render(raw: bytes, report: dict, free_report: dict, value: dict) -> str:
    portfolio, benchmark = report["portfolio"], report["benchmark"]
    free_portfolio, free_benchmark = free_report["portfolio"], free_report["benchmark"]
    currency = report["currency"]
    money = lambda amount, places=2: _money(amount, currency, places)
    initial = Decimal(portfolio["initial_capital"])
    cash = Decimal(portfolio["unallocated_cash"])
    invested_pct = (initial - cash) / initial * 100
    drag = Decimal(free_portfolio["final_nav"]) - Decimal(portfolio["final_nav"])
    benchmark_drag = Decimal(free_benchmark["final_nav"]) - Decimal(benchmark["final_nav"])
    p_rows, b_rows = _drawdown_rows(portfolio), _drawdown_rows(benchmark)
    curve_rows = []
    for index, (p_row, b_row) in enumerate(zip(p_rows, b_rows)):
        phase = p_row["phase"]
        if phase == "initial_capital":
            label, session = "Capital inicial", "—"
        elif phase == "final_liquidation":
            label, session = "Liquidação hipotética", p_row["session_index"]
        else:
            label = "Fechamento de entrada T+1" if index == 1 else "Marcação no fechamento"
            session = p_row["session_index"]
        curve_rows.append(f'<tr class="{"settlement" if phase == "final_liquidation" else ""}"><th scope="row">{label}<small>{_escape(p_row["date"])}</small></th><td>{_escape(session)}</td><td>{money(p_row["nav"], 8)}</td><td>{_percent(p_row["drawdown"], 8)}</td><td>{money(b_row["nav"], 8)}</td><td>{_percent(b_row["drawdown"], 8)}</td></tr>')
    cost_names = (("entry_fee", "Taxa de entrada"), ("exit_fee", "Taxa de saída"), ("entry_slippage_vs_close", "Slippage na entrada"), ("exit_slippage_vs_close", "Slippage na saída"))
    cost_rows = "".join(f'<tr><th scope="row">{label}</th><td>{money(portfolio["costs"][key], 8)}</td><td>{money(benchmark["costs"][key], 8)}</td></tr>' for key, label in cost_names)
    cost_rows += f'<tr class="total"><th scope="row">Soma dos componentes publicados (arredondados)</th><td>{money(_sum_costs(portfolio), 8)}</td><td>{money(_sum_costs(benchmark), 8)}</td></tr>'
    allocation_rows = "".join(f'<tr><th scope="row">Ativo fictício {index + 1}</th><td>{_percent(Decimal(value["target_weights"][asset]) * 100)}</td><td>{money(value["sessions"][1]["prices"][asset], 6)}</td></tr>' for index, asset in enumerate(value["assets"]))
    session_rows = "".join(f'<tr><th scope="row">{index}</th><td>{_escape(item["date"])}</td><td>{_escape(item["available_at"])}</td><td>{"Última sessão antes da decisão" if index == 0 else "Entrada hipotética no fechamento" if index == 1 else "Somente marcação e avaliação"}</td></tr>' for index, item in enumerate(value["sessions"]))
    evidence_dates = [item["available_at"] for item in value["evidence"]]
    encoded = base64.b64encode((json.dumps(report, ensure_ascii=True, indent=2, sort_keys=True) + "\n").encode("utf-8")).decode("ascii")
    checksum = hashlib.sha256(raw).hexdigest()
    # The only serialized input-derived payload is the motor's sanitized report.
    # An encoded download avoids executable JSON/script contexts altogether.
    return f'''<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; base-uri 'none'; form-action 'none'; connect-src 'none'; object-src 'none'">
<meta name="color-scheme" content="light"><title>Radar Equity Replay Lab · Caderno educacional</title>
<style>
:root{{--ink:#18343a;--muted:#526569;--paper:#f4f4ed;--card:#fff;--line:#d8e2de;--green:#126a62;--purple:#5163a6;--orange:#9b482d;--soft:#e8f2ed;--radius:18px}}*{{box-sizing:border-box}}html{{scroll-padding-top:94px}}body{{margin:0;background:var(--paper);color:var(--ink);font:16px/1.6 system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}}a{{color:var(--green);text-underline-offset:4px}}a:focus-visible,summary:focus-visible{{outline:3px solid #b54d25;outline-offset:5px}}.skip{{position:absolute;left:20px;top:-80px;z-index:9;padding:12px;background:white}}.skip:focus{{top:12px}}.wrap{{max-width:1220px;margin:auto;padding:0 36px}}header{{background:#18343a;color:#fff;padding:46px 0 42px}}.brand{{font-size:.78rem;letter-spacing:.14em;font-weight:750;text-transform:uppercase;color:#b6d8ca}}.hero-grid{{display:grid;grid-template-columns:1.6fr 1fr;gap:70px;align-items:center}}h1{{font-size:clamp(2.25rem,4.7vw,4rem);line-height:1.07;letter-spacing:-.045em;max-width:740px;margin:21px 0}}.lead{{max-width:720px;color:#d4e4e0;font-size:1.08rem}}.status-box{{border:1px solid #547273;border-radius:var(--radius);padding:23px;background:#234249}}.status-box p{{margin:12px 0 0;color:#d4e4e0}}.pill{{display:inline-block;border-radius:99px;padding:5px 11px;font-size:.76rem;font-weight:750;letter-spacing:.03em;background:#d3e8b9;color:#273b20}}.states{{font:12px/1.9 ui-monospace,SFMono-Regular,Consolas,monospace;overflow-wrap:anywhere}}nav{{position:sticky;top:0;background:#fffffff2;backdrop-filter:blur(12px);border-bottom:1px solid var(--line);z-index:3}}.nav-inner{{display:flex;align-items:center;justify-content:space-between;gap:18px;padding-top:14px;padding-bottom:14px}}nav a{{font-size:.9rem;text-decoration:none;padding:7px 10px;border-radius:7px}}nav a[aria-current]{{background:var(--soft);font-weight:750}}.nav-brand{{font-weight:800;white-space:nowrap}}.nav-links{{display:flex;gap:7px;flex-wrap:wrap}}main{{padding:38px 0 46px}}.eyebrow{{font-size:.76rem;font-weight:800;color:var(--green);text-transform:uppercase;letter-spacing:.12em}}h2{{font-size:clamp(1.7rem,3vw,2.4rem);line-height:1.2;letter-spacing:-.03em;margin:10px 0 16px}}h3{{font-size:1.15rem;line-height:1.35;margin:0 0 12px}}p{{margin:0 0 16px}}.muted,small{{color:var(--muted)}}small{{display:block;font-size:.76rem;font-weight:400}}.choices{{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin:24px 0 44px}}.choice{{display:block;background:var(--card);border:1px solid var(--line);border-radius:var(--radius);padding:21px;text-decoration:none;color:var(--ink)}}.choice:hover{{border-color:var(--green)}}.number{{display:block;font:600 12px ui-monospace,monospace;color:var(--green);margin-bottom:25px}}.choice strong{{font-size:1.05rem;display:block;line-height:1.3;margin-bottom:10px}}.choice span:last-child{{font-size:.86rem;color:var(--muted)}}section{{scroll-margin-top:100px;border-top:1px solid var(--line);padding:35px 0 12px;margin:22px 0 0}}section:target h2{{text-decoration:underline;text-decoration-color:#acc8b5;text-underline-offset:8px}}.section-heading{{display:flex;justify-content:space-between;align-items:start;gap:20px}}.back{{font-size:.8rem;white-space:nowrap;margin-top:10px}}.section-copy{{max-width:820px;color:var(--muted)}}.kpis{{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin:26px 0}}.kpi{{padding:22px;background:white;border:1px solid var(--line);border-radius:var(--radius)}}.kpi.primary{{background:var(--green);border-color:var(--green);color:white}}.kpi.primary .kpi-label,.kpi.primary small{{color:#d5ebe5}}.kpi-label{{font-size:.8rem;color:var(--muted)}}.kpi strong{{display:block;font-size:clamp(1.35rem,2.3vw,1.9rem);line-height:1.3;letter-spacing:-.025em;margin:10px 0}}.grid-2{{display:grid;grid-template-columns:1fr 1fr;gap:20px;margin:22px 0}}.panel{{background:white;border:1px solid var(--line);border-radius:var(--radius);padding:25px;min-width:0}}.note{{padding:20px 23px;background:var(--soft);border-radius:12px;margin:20px 0}}.note.warm{{background:#faeee5;color:#623923}}.note strong{{display:block;margin-bottom:4px}}.note p{{margin:0;font-size:.92rem}}.table-wrap{{overflow:auto;border:1px solid var(--line);border-radius:12px;background:white;margin:18px 0 22px}}.table-wrap:focus-visible{{outline:3px solid #b54d25}}table{{border-collapse:collapse;width:100%;font-size:.88rem}}caption{{text-align:left;padding:18px 20px;font-weight:750;font-size:.95rem}}th,td{{padding:13px 18px;border-top:1px solid var(--line);text-align:right;vertical-align:top;font-variant-numeric:tabular-nums;white-space:nowrap}}th:first-child,td:first-child{{text-align:left}}thead th{{background:#f5f8f5;color:var(--muted);font-size:.77rem;font-weight:650}}tbody th{{font-weight:600}}.settlement,.total{{background:#edf5ef}}.table-note{{font-size:.8rem;color:var(--muted)}}.formula{{font:12px/1.9 ui-monospace,SFMono-Regular,Consolas,monospace;white-space:normal;overflow-wrap:anywhere;display:block;background:#f2f6f2;border-radius:8px;padding:15px}}.curve-chart{{width:100%;height:auto;display:block}}.legend{{display:flex;gap:20px;font-size:.85rem;flex-wrap:wrap}}.legend span::before{{content:"";display:inline-block;width:18px;height:3px;background:var(--green);vertical-align:middle;margin-right:8px}}.legend span:last-child::before{{background:var(--purple)}}.timeline{{display:grid;grid-template-columns:repeat(3,1fr);gap:20px;margin:24px 0}}.timeline article{{border-top:3px solid #a9bfb6;padding:15px 0}}.timeline article:nth-child(2){{border-color:var(--green)}}.timeline article:nth-child(3){{border-color:var(--purple)}}.time{{font:12px/1.8 ui-monospace,monospace;overflow-wrap:anywhere;color:var(--muted)}}ul,ol{{padding-left:22px}}li{{margin:9px 0}}details{{margin:16px 0;border:1px solid var(--line);border-radius:12px;background:white;padding:18px 22px}}summary{{cursor:pointer;font-weight:700}}details[open] summary{{margin-bottom:16px}}.hash{{display:block;overflow-wrap:anywhere;font:12px/1.8 ui-monospace,monospace;background:#edf2ed;border-radius:7px;padding:13px}}.download{{display:inline-block;background:var(--green);color:white;text-decoration:none;border-radius:9px;padding:12px 18px;font-weight:700;font-size:.9rem;margin:4px 0 12px}}footer{{background:#e5ece6;border-top:1px solid #cad8ce;padding:28px 0;color:var(--muted);font-size:.8rem}}footer p{{margin-bottom:9px}}.nojs{{margin:0;padding:12px 24px;background:#faeee5;color:#623923}}@media(max-width:900px){{.hero-grid{{grid-template-columns:1fr;gap:23px}}header{{padding:32px 0}}.choices,.kpis{{grid-template-columns:repeat(2,1fr)}}.nav-brand{{display:none}}.nav-inner{{justify-content:center}}.grid-2{{grid-template-columns:1fr}}.timeline{{gap:15px}}}}@media(max-width:560px){{.wrap{{padding-left:19px;padding-right:19px}}.choices,.kpis,.timeline{{grid-template-columns:1fr}}.choices{{gap:10px}}.number{{margin-bottom:12px}}.choice{{padding:18px}}.nav-links{{gap:1px}}nav a{{padding:6px;font-size:.75rem}}.section-heading{{display:block}}.back{{display:inline-block;margin:0 0 12px}}.panel{{padding:20px}}h1{{font-size:2.35rem}}.kpi strong{{font-size:1.7rem}}}}@media(prefers-reduced-motion:no-preference){{html{{scroll-behavior:smooth}}}}@media print{{nav,.skip,.back,.download{{display:none}}header{{background:white;color:var(--ink);padding:15px 0}}.lead,.brand,.status-box p{{color:var(--muted)}}.hero-grid{{grid-template-columns:1fr}}.status-box{{background:white;border-color:#bbb}}.choices{{display:none}}.wrap{{padding:0}}.panel,.kpi{{break-inside:avoid}}.table-wrap{{overflow:visible}}body{{font-size:11px;background:white}}section{{break-before:auto}}}}
</style></head><body><a class="skip" href="#conteudo">Pular para o conteúdo</a><noscript><p class="nojs">Todo o caderno está disponível sem JavaScript. Use os links para navegar e baixar o JSON.</p></noscript>
<header id="inicio"><div class="wrap hero-grid"><div><div class="brand">Radar Equity Replay Lab · Caderno 01</div><h1>O que uma simulação<br>realmente mostra?</h1><p class="lead">Explore números fictícios com custos, perdas e datas à vista. Os pesos foram fornecidos pelo operador; o motor calculou o replay.</p></div><aside class="status-box" aria-label="Escopo e estado do relatório"><span class="pill">EXCLUSIVAMENTE EDUCACIONAL</span><p>Dados declarados fictícios. Sem seleção de ativos ou operação financeira.</p><p class="states">synthetic_only=true<br>review_status=pending<br>execution_allowed=false</p></aside></div></header>
<nav aria-label="Seções do caderno"><div class="wrap nav-inner"><a class="nav-brand" href="#inicio">REPLAY / LAB</a><div class="nav-links"><a href="#entender">01 · Entender</a><a href="#custos">02 · Custos</a><a href="#perdas">03 · Perdas</a><a href="#cronologia">04 · Cronologia</a></div></div></nav>
<main id="conteudo" class="wrap"><div class="eyebrow">Escolha por onde começar</div><p class="section-copy">As quatro leituras usam a mesma entrada validada. Você pode percorrer todas, na ordem que preferir.</p><div class="choices"><a class="choice" href="#entender"><span class="number">01 / RESULTADO</span><strong>Entender uma simulação fictícia</strong><span>Capital, pesos, caixa e comparação.</span></a><a class="choice" href="#custos"><span class="number">02 / ATRITO</span><strong>Comparar o efeito dos custos</strong><span>Taxa, slippage e cenário sem custos.</span></a><a class="choice" href="#perdas"><span class="number">03 / TRAJETÓRIA</span><strong>Examinar perdas e drawdown</strong><span>O caminho entre a entrada e a saída.</span></a><a class="choice" href="#cronologia"><span class="number">04 / MÉTODO</span><strong>Verificar a cronologia</strong><span>O que estava declarado disponível em T.</span></a></div>

<section id="entender" aria-labelledby="entender-title"><div class="section-heading"><div><div class="eyebrow">01 · Entender a simulação fictícia</div><h2 id="entender-title">Comece pelo saldo. Depois, pelo método.</h2></div><a class="back" href="#inicio">Voltar ao início ↑</a></div><p class="section-copy">Capital inicial de <strong>{money(initial)}</strong>, em {_escape(currency)}, com {report['asset_count']} ativos fictícios e {report['session_count']} sessões fornecidas. A entrada acontece no fechamento de {_escape(report['execute_on'])}; a liquidação hipotética, em {_escape(report['last_session'])}.</p>
<div class="kpis"><article class="kpi primary"><div class="kpi-label">Saldo final após custos modelados</div><strong>{money(portfolio['final_nav'])}</strong><small>Carteira + caixa residual</small></article><article class="kpi"><div class="kpi-label">Retorno da carteira</div><strong>{_percent(portfolio['return_pct'])}</strong><small>Sobre o capital inicial</small></article><article class="kpi"><div class="kpi-label">Maior queda desde um pico</div><strong>{_percent(portfolio['max_drawdown_pct'])}</strong><small>Drawdown calculado pelo motor</small></article><article class="kpi"><div class="kpi-label">Diferença versus benchmark</div><strong>{_decimal_text(report['excess_return_percentage_points'],4)} p.p.</strong><small>Não ajustada ao risco</small></article></div>
<div class="grid-2"><article class="panel"><h3>Pesos declarados, caixa preservado</h3><p>{_percent(invested_pct)} do capital foi destinado às parcelas de compra, já incluindo custos de entrada. O caixa residual de <strong>{money(cash)}</strong> não rende juros.</p><p class="muted">Os pesos são hipóteses do operador. O programa não escolhe ativos, otimiza a carteira ou avalia uma tese.</p></article><article class="panel"><h3>Benchmark com a mesma regra de custos</h3><p>O benchmark aplica 100% do mesmo capital, na mesma sessão T+1. Seu saldo final é <strong>{money(benchmark['final_nav'])}</strong>, com retorno de <strong>{_percent(benchmark['return_pct'])}</strong>.</p><p class="muted">A carteira pode manter caixa e assumir uma exposição diferente. A diferença de retorno não demonstra habilidade ou alpha.</p></article></div>
<details><summary>Ver os pesos e preços de entrada, sem identificadores</summary><p>Os rótulos abaixo indicam apenas a posição no arquivo validado. Nenhum ativo real foi renomeado pelo caderno.</p><div class="table-wrap" role="region" aria-label="Pesos e preços de entrada" tabindex="0"><table><thead><tr><th scope="col">Posição no exemplo</th><th scope="col">Peso declarado</th><th scope="col">Preço no fechamento T+1</th></tr></thead><tbody>{allocation_rows}</tbody></table></div></details>
<details><summary>Ver as fórmulas e a precisão</summary><p>Com capital C, peso w, preço de entrada P₁, f = taxa em pontos-base ÷ 10.000 e s = slippage em pontos-base ÷ 10.000:</p><code class="formula">parcela = C × w<br>unidades = parcela ÷ [(1 + f) × P₁ × (1 + s)]<br>NAV no fechamento = caixa + Σ(unidades × preço)<br>saldo liquidado = caixa + Σ(unidades × Pfinal × (1 − s)) × (1 − f)<br>retorno (%) = 100 × (saldo liquidado ÷ C − 1)</code><p>O motor usa Decimal com 50 dígitos de precisão e arredondamento half-even. As curvas e o JSON exibem oito casas decimais; os destaques de dinheiro usam duas. Custos minúsculos podem arredondar para zero.</p></details>
<div class="note warm"><strong>Resultado calculado ≠ resultado executável.</strong><p>Esta fixture não demonstra retorno histórico real, risco futuro, adequação pessoal, significância estatística ou lucro que seria possível executar no mercado.</p></div></section>

<section id="custos" aria-labelledby="custos-title"><div class="section-heading"><div><div class="eyebrow">02 · Comparar o efeito dos custos</div><h2 id="custos-title">Uma mesma hipótese, duas condições de custo.</h2></div><a class="back" href="#inicio">Voltar ao início ↑</a></div><p class="section-copy">O motor executou a entrada validada e uma cópia em memória com taxa e slippage zerados. Capital, preços, datas e pesos permaneceram iguais. São cenários alternativos; seus resultados não devem ser somados.</p>
<div class="grid-2"><article class="panel"><h3>Taxa: {_decimal_text(report['fee_bps'],6)} pontos-base</h3><p>Incide sobre o notional efetivo na compra e na venda hipotéticas.</p></article><article class="panel"><h3>Slippage: {_decimal_text(report['slippage_bps'],6)} pontos-base</h3><p>Aumenta o preço de compra e reduz o preço de venda. Não mede spread ou liquidez reais.</p></article></div><div class="note"><strong>Um ponto-base = 0,01 ponto percentual.</strong><p>Por exemplo, 10 pontos-base correspondem a 0,10%. Cada taxa é aplicada em cada lado da operação.</p></div>
<div class="table-wrap" role="region" aria-label="Comparação de cenários de custos" tabindex="0"><table><caption>Mesmo capital, mesma sessão de entrada e mesmos preços</caption><thead><tr><th scope="col">Métrica</th><th scope="col">Com custos declarados</th><th scope="col">Sem taxa e slippage</th></tr></thead><tbody><tr><th scope="row">Saldo final da carteira</th><td>{money(portfolio['final_nav'],8)}</td><td>{money(free_portfolio['final_nav'],8)}</td></tr><tr><th scope="row">Retorno da carteira</th><td>{_percent(portfolio['return_pct'],8)}</td><td>{_percent(free_portfolio['return_pct'],8)}</td></tr><tr><th scope="row">Drawdown máximo da carteira</th><td>{_percent(portfolio['max_drawdown_pct'],8)}</td><td>{_percent(free_portfolio['max_drawdown_pct'],8)}</td></tr><tr><th scope="row">Saldo final do benchmark</th><td>{money(benchmark['final_nav'],8)}</td><td>{money(free_benchmark['final_nav'],8)}</td></tr><tr><th scope="row">Retorno do benchmark</th><td>{_percent(benchmark['return_pct'],8)}</td><td>{_percent(free_benchmark['return_pct'],8)}</td></tr><tr><th scope="row">Caixa residual da carteira</th><td>{money(cash,8)}</td><td>{money(free_portfolio['unallocated_cash'],8)}</td></tr></tbody></table></div>
<div class="note"><strong>Efeito no saldo final da carteira: {money(drag,8)}.</strong><p>É a diferença entre o saldo sem custos e o saldo com custos. No benchmark, a diferença é {money(benchmark_drag,8)}. Esse efeito inclui a mudança nas unidades compradas e, por isso, pode diferir da soma dos custos contabilizados abaixo.</p></div>
<div class="table-wrap" role="region" aria-label="Custos separados da carteira e do benchmark" tabindex="0"><table><caption>Custos modelados, em {_escape(currency)}</caption><thead><tr><th scope="col">Componente</th><th scope="col">Carteira</th><th scope="col">Benchmark</th></tr></thead><tbody>{cost_rows}</tbody></table></div><p class="table-note">Os totais desta tabela somam os componentes já arredondados do relatório. O modelo não inclui impostos, dividendos, juros de caixa, câmbio, empréstimo de ações, restrições de liquidez ou impacto real de mercado.</p></section>

<section id="perdas" aria-labelledby="perdas-title"><div class="section-heading"><div><div class="eyebrow">03 · Examinar perdas e drawdown</div><h2 id="perdas-title">O saldo final não conta toda a trajetória.</h2></div><a class="back" href="#inicio">Voltar ao início ↑</a></div><p class="section-copy">Drawdown é a queda em relação ao maior valor alcançado até cada ponto. O cálculo inclui capital inicial, marcação de entrada, fechamentos seguintes e liquidação final. A maior queda da carteira foi {_percent(portfolio['max_drawdown_pct'],8)}; a do benchmark, {_percent(benchmark['max_drawdown_pct'],8)}.</p>
<article class="panel"><div class="legend"><span>Carteira + caixa</span><span>Benchmark 100% investido</span></div><p class="table-note">NAV em {_escape(currency)} · escala vertical ajustada aos valores observados, sem início obrigatório em zero. Consulte os valores exatos na tabela abaixo.</p>{_chart(portfolio, benchmark)}<p class="table-note">O eixo horizontal acompanha a ordem das sessões fornecidas. O capital inicial é um estado anterior à compra. A liquidação ocupa a mesma posição horizontal do último fechamento e não cria outro pregão.</p></article>
<div class="table-wrap" role="region" aria-label="Curva e drawdown ponto a ponto" tabindex="0"><table><caption>Curva calculada · todos os valores em {_escape(currency)}</caption><thead><tr><th scope="col">Estado / data</th><th scope="col">Índice de sessão</th><th scope="col">Carteira</th><th scope="col">Queda da carteira</th><th scope="col">Benchmark</th><th scope="col">Queda do benchmark</th></tr></thead><tbody>{''.join(curve_rows)}</tbody></table></div><p class="table-note">As quedas por linha são calculadas em Python sobre os valores publicados da curva, arredondados a oito casas. O drawdown máximo dos destaques vem do motor antes desse arredondamento. A liquidação é uma segunda avaliação na mesma data final, com custos de saída; não é uma sessão ou período independente.</p>
<div class="grid-2"><article class="panel"><h3>O que foi medido</h3><code class="formula">pico = maior NAV observado até o ponto<br>queda (%) = 100 × (pico − NAV) ÷ pico<br>drawdown máximo = maior queda da curva</code></article><article class="panel"><h3>O que permanece desconhecido</h3><p>Não há estimativa de recuperação, probabilidade de ganho ou risco futuro. A amostra é curta e fictícia; o caderno não anualiza retorno nem inventa Sharpe, CAGR ou validação fora da amostra.</p></article></div></section>

<section id="cronologia" aria-labelledby="cronologia-title"><div class="section-heading"><div><div class="eyebrow">04 · Verificar a cronologia</div><h2 id="cronologia-title">A entrada vem depois da decisão.</h2></div><a class="back" href="#inicio">Voltar ao início ↑</a></div><p class="section-copy">Todos os horários abaixo usam UTC; “Z” indica esse fuso. T+1 significa a sessão seguinte fornecida no arquivo, sem validação de calendário de bolsa ou feriados.</p>
<div class="timeline"><article><div class="eyebrow">T · Informação declarada</div><h3>Fronteira da decisão</h3><p class="time">{_escape(report['decision_at'])}</p><p>{report['evidence_count']} evidência(s) declarada(s) disponível(is) até a decisão. Evidência posterior é recusada.</p></article><article><div class="eyebrow">T+1 · Entrada hipotética</div><h3>Fechamento da sessão 1</h3><p class="time">{_escape(value['sessions'][1]['available_at'])}</p><p>Os preços da sessão anterior não podem ser usados como preço de entrada.</p></article><article><div class="eyebrow">Depois · Avaliação</div><h3>Marcação e liquidação</h3><p class="time">Até {_escape(report['last_session'])}</p><p>Os preços posteriores servem à avaliação dos pesos fornecidos, sem escolha de entrada ou de ativos no código.</p></article></div>
<div class="note warm"><strong>O guard temporal verifica declarações, não a sua autenticidade.</strong><p>As datas não foram autenticadas e a origem dos pesos não foi verificada. O arquivo não prova que o operador ou um LLM desconhecia os preços futuros quando declarou os pesos.</p></div>
<details><summary>Inspecionar todas as sessões e disponibilidades UTC</summary><p>Disponibilidade declarada das evidências: de <span class="time">{_escape(min(evidence_dates))}</span> até <span class="time">{_escape(max(evidence_dates))}</span>. IDs, URLs e textos não são exibidos.</p><div class="table-wrap" role="region" aria-label="Sessões e disponibilidades declaradas" tabindex="0"><table><thead><tr><th scope="col">Índice</th><th scope="col">Data</th><th scope="col">Disponibilidade UTC</th><th scope="col">Uso no replay</th></tr></thead><tbody>{session_rows}</tbody></table></div></details>
<div class="grid-2"><article class="panel"><h3>Cálculo, declaração e interpretação</h3><ul><li><strong>Calculado:</strong> unidades, caixa, curvas, custos, retorno, drawdown e benchmark.</li><li><strong>Declarado no arquivo:</strong> caráter fictício, pesos, preços e disponibilidades.</li><li><strong>Interpretação:</strong> exemplos de efeitos dessas hipóteses, sem recomendação.</li><li><strong>Não verificado:</strong> fonte, verdade das datas e independência de quem escolheu os pesos.</li></ul></article><article class="panel"><h3>Reproduzir e conferir</h3><p>O SHA-256 abaixo identifica os bytes exatos da entrada usada neste caderno. Não autentica fonte, autoria, verdade ou autorização.</p><code class="hash">{checksum}</code><a class="download" href="data:application/json;base64,{encoded}" download="radar-equity-replay-report.json">Baixar JSON calculado</a><p class="table-note">Download do relatório original sanitizado do motor. O cenário sem custos foi gerado em memória apenas para a comparação deste caderno. Nenhuma rede, conta, serviço ou feed é utilizado.</p></article></div>
<details><summary>Limites e até três próximos experimentos educacionais</summary><p>Este modelo de comprar e manter usa unidades fracionárias, pesos fixos e uma entrada. Não há rebalanceamento, short, alavancagem, dividendos, juros, impostos, câmbio, empréstimo de ações, liquidez ou impacto de mercado. Uma comparação com benchmark não iguala o risco.</p><ol><li>Comparar fixtures com taxas e slippage diferentes, mantendo preços, capital, datas e pesos.</li><li>Examinar a fixture de perda e localizar o pico anterior à maior queda.</li><li>Alterar em uma cópia fictícia a disponibilidade de evidência para depois de T e conferir a recusa do contrato.</li></ol><p>Os dados brutos não são editáveis nem carregáveis pelo navegador. Cada nova fixture deve passar pelo contrato estrito e pelo motor local.</p></details><div class="note"><strong>Revisão humana pendente.</strong><p>review_status=pending · execution_allowed=false. Este estado não é uma aprovação e não controla outras ferramentas do ChatGPT. Qualquer operação futura exige projeto, autorização e controles próprios.</p></div></section>
</main><footer><div class="wrap"><p><strong>Radar Equity Replay Lab</strong> · Motor e caderno originais de Carlos Felipe · MIT.</p><p>Padrões estudados no AI Hedge Fund, de Virat Singh, MIT. O commit de referência está em third_party/ai-hedge-fund/SOURCE.json. Não há endosso do autor upstream ou de investidores famosos.</p><p>TradingAgents preserva seu laboratório de teses e contrapontos; Capital Web3 preserva o domínio DeFi. Evidence Kit, Hub e Router são integrações futuras, ainda não implementadas aqui.</p></div></footer>
<script>"use strict";(()=>{{const links=Array.from(document.querySelectorAll(".nav-links a"));function mark(){{const hash=window.location.hash;for(const link of links){{if(link.getAttribute("href")===hash){{link.setAttribute("aria-current","location");}}else{{link.removeAttribute("aria-current");}}}}}}window.addEventListener("hashchange",mark);mark();}})();</script></body></html>'''


def render_workbook(raw: bytes) -> str:
    """Validate exact input bytes and return a self-contained offline workbook.

    Validation always runs before deserializing any display inputs. Only strict
    numerical/date fields are read from the validated object; untrusted labels,
    source URLs and evidence text have no route to the generated document.
    """
    report = analyze(raw)
    value = json.loads(raw.decode("utf-8"))
    cost_free = dict(value)
    cost_free["fee_bps"] = "0"
    cost_free["slippage_bps"] = "0"
    # Preserve UTF-8 rather than expanding valid Unicode evidence to \uXXXX:
    # the internal cost-free copy must not exceed the byte limit merely due to
    # an encoding change. Strict validation has already rejected surrogates.
    free_raw = json.dumps(cost_free, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    free_report = analyze(free_raw)
    with localcontext(Context(prec=50, rounding=ROUND_HALF_EVEN)):
        return _render(raw, report, free_report, value)


class _SafeParser(argparse.ArgumentParser):
    def error(self, _message):
        self.exit(2, "Argumentos recusados. Use --help para a sintaxe local do caderno.\n")


def main(argv=None):
    parser = _SafeParser(description="Gerar caderno HTML offline com replay exclusivamente fictício.")
    parser.add_argument("input")
    parser.add_argument("--output", required=True)
    arguments = parser.parse_args(argv)
    try:
        content = render_workbook(read_input(arguments.input))
        write_report(arguments.output, content.encode("utf-8"))
    except InvalidInput:
        print("Entrada ou saída recusada. Use o contrato sintético e um arquivo de saída novo.", file=sys.stderr)
        return 2
    print("Caderno educacional offline criado; revisão humana pendente.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
