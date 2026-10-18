# Experiência do caderno educacional offline

## Objetivo e escopo

Permitir que uma pessoa leiga explique o resultado de uma fixture fictícia, os custos, a trajetória de perda e a fronteira temporal. O caderno é um HTML gerado pelo motor local, em português do Brasil, sem servidor, conta, telemetria ou rede. Não recebe carteiras reais, credenciais, ordens ou aprovação financeira.

Esta especificação corresponde ao gerador `src/radar_equity_replay/workbook.py`. Define critérios verificáveis; não constitui homologação visual, teste com participantes ou declaração de conformidade de acessibilidade.

## Entrada, navegação e quatro caminhos

A entrada é feita pela CLI, usando exclusivamente JSON validado pelo contrato. O navegador apresenta uma fotografia do cálculo: não importa nem edita arquivos, não recalcula valores e não segue fontes de evidência. Abrir o HTML localmente é suficiente.

Na abertura, mostrar o nome do laboratório, o caráter fictício e os estados `review_status=pending` e `execution_allowed=false`. Oferecer os quatro caminhos abaixo. As seções pertencem ao mesmo documento e ficam disponíveis em qualquer ordem; não há etapas obrigatórias ou chat.

| Caminho / destino | Pergunta que resolve | Conteúdo prioritário e próxima ação |
| --- | --- | --- |
| 1. Entender uma simulação fictícia / `#entender` | Quanto terminou e sob quais hipóteses? | Capital, moeda, período, saldo final após custos, retorno, drawdown e diferença em p.p.; depois pesos, caixa e benchmark. Abrir fórmulas se necessário. |
| 2. Comparar efeito de custos / `#custos` | O que muda ao zerar taxa e slippage? | Duas condições alternativas do mesmo exemplo, decomposição de entrada/saída e diferença de NAV. Comparar também o benchmark. |
| 3. Examinar perdas e drawdown / `#perdas` | Quanto caiu desde o maior valor anterior? | Curva com tabela numérica equivalente, capital inicial, fechamento de entrada, marcas seguintes e liquidação final. Localizar o pico e a queda. |
| 4. Verificar cronologia / `#cronologia` | A entrada respeitou a informação declarada em T? | Decisão, disponibilidade das evidências, sessão 0, entrada na sessão 1, marcas posteriores e hash. Inspecionar sessões e baixar o JSON calculado. |

Uma navegação persistente repete os quatro destinos; cada seção permite voltar ao início. Usar links nativos e elementos `details`/`summary` para exposição progressiva. Todo conteúdo e o download continuam disponíveis sem JavaScript; o script opcional apenas indica o destino atual da navegação.

## Regras de apresentação financeira

- Usar a moeda declarada, sem conversão. Dinheiro em destaque tem duas casas; tabelas de conferência e JSON preservam oito. Não esconder valores pequenos: explicar que um valor apresentado como zero pode resultar do arredondamento.
- Explicar **1 ponto-base = 0,01 ponto percentual**; 10 bps correspondem a 0,10%. Taxa e slippage são hipóteses aplicadas na entrada e na saída, com incidências distintas.
- O peso é a parcela do capital inicial **incluindo os custos de entrada**. Não é peso ótimo nem peso exato sobre o NAV após custos. Mostrar o caixa residual sem juros e informar que o benchmark aplica 100% do mesmo capital na mesma sessão e com o mesmo modelo de custo.
- Diferença de retorno usa **pontos percentuais**, não porcentagem relativa. Exposição e caixa podem diferir: essa diferença não demonstra alpha, habilidade ou risco equivalente.
- Separar **soma dos custos nominais modelados** de **redução do NAV frente ao cenário sem custos**. A primeira soma taxa/slippage de compra/venda; a segunda inclui a mudança nas unidades compradas e na exposição à trajetória posterior. Os componentes publicados já estão arredondados e podem diferir na última casa de um total calculado antes desse arredondamento.
- O cenário sem custos é uma cópia validada em memória com `fee_bps=0` e `slippage_bps=0`; não representa uma operação adicional. Não somar retornos de cenários.
- Drawdown inclui o capital inicial e a liquidação final. O fechamento e a liquidação no último dia têm rótulos distintos e a mesma posição temporal: não são dois pregões. Valores por linha podem ser derivados da curva publicada a oito casas; o máximo do destaque vem do cálculo do motor antes desse arredondamento.

As fórmulas devem estar acessíveis no próprio documento:

```text
f = fee_bps / 10000; s = slippage_bps / 10000
unidades = C × w / [(1 + f) × P1 × (1 + s)]
caixa = C × (1 − soma dos pesos)
NAV de fechamento = caixa + soma(unidades × preço)
NAV final = caixa + soma(unidades × Pfinal × (1 − s)) × (1 − f)
retorno (%) = 100 × (NAV final / C − 1)
drawdown (%) = 100 × (pico acumulado − NAV) / pico acumulado
```

## Evidência, origem e interpretação

Identificar quatro categorias no conteúdo: **calculado** (métricas e curvas), **declarado no arquivo** (pesos, preços, datas, caráter fictício), **interpretação** (efeitos dessas hipóteses) e **não verificado** (autenticidade e independência de quem escolheu os pesos). O guard verifica `sessão0 ≤ decisão < sessão1` por disponibilidade declarada e recusa evidência posterior. Não autentica datas, calendário de bolsa ou desconhecimento do futuro.

O SHA-256 identifica os **bytes exatos da entrada original usada no caderno**. Não prova verdade, autoria, origem ou autorização; não é o hash da cópia em memória sem custos. O download contém o relatório sanitizado da entrada original. Não ecoar IDs de projeto/ativos/evidências, URLs ou textos de evidência: as posições aparecem apenas como “Ativo fictício 1”, “Ativo fictício 2” etc. Isso não converte ativos reais em fictícios nem garante anonimização universal.

O HTML é estático. Não detecta alterações posteriores da fixture nem atualiza resultados: para outra entrada, gerar um novo arquivo e conferir seu hash. Não apresentar um estado artificial de “sincronizado”.

## Estados e recuperação

| Estado atual | Evento / condição | Próximo estado e efeito | Recuperação e texto |
| --- | --- | --- | --- |
| CLI pronta | JSON e saída nova válidos | Sucesso; HTML offline criado, revisão humana pendente | Abrir o arquivo localmente. Não abrir rede ou navegador automaticamente. |
| CLI pronta | Sintaxe de argumentos inválida | Recusa, código 2; nenhum dado sensível ecoado | Usar `--help`; não imprimir o argumento recusado. |
| CLI pronta | Contrato, cronologia ou caminho recusado; saída já existe | Recusa, código 2; mensagem genérica | “Entrada ou saída recusada. Use o contrato sintético e um arquivo de saída novo.” Conferir o contrato local e escolher saída nova. |
| Escrita iniciada | Falha de escrita | Falha; nenhum sucesso anunciado | Investigar eventual arquivo parcial antes de repetir; não prometer atomicidade nem sobrescrever. |
| HTML aberto | Link de caminho ou retorno ao início | Âncora correspondente; foco e destino perceptíveis | Conteúdo permanece disponível com JavaScript desabilitado. |
| HTML aberto | Abrir detalhes ou baixar JSON | Expansão nativa ou download local do relatório | Não enviar dados, pedir login ou autorizar execução. |

Não há estado de carregamento remoto, lista vazia, acesso por conta ou aprovação. Uma entrada sem dados suficientes falha no contrato antes de gerar o caderno; não produzir dashboard vazio nem indicador de progresso inventado. A entrada original e qualquer relatório anterior permanecem intactos.

## Semântica, foco e layout

- Documento `lang="pt-BR"`, um `h1`, hierarquia de títulos, `header`, navegação com nome acessível, `main` e `footer`; link inicial “Pular para o conteúdo”.
- Navegação por teclado em ordem do documento, foco visível em links, resumos e regiões de tabela; foco/âncora não encobertos pela navegação fixa. O destaque de destino não depende exclusivamente de cor.
- Tabelas com legenda ou nome de região, cabeçalhos de coluna e linha, números legíveis e região horizontal focável quando necessário. Não substituir a tabela por gráfico.
- SVG com título e descrição acessíveis. A legenda deve nomear carteira e benchmark; o texto/tabela permite compreender a informação sem distinguir as cores das curvas.
- Layout de quatro escolhas em telas largas, duas em largura intermediária e uma em telas estreitas. Cartões e textos quebram sem corte; hashes e horários longos podem quebrar linha. Rolagem horizontal fica restrita às tabelas necessárias.
- Verificar alvos acionáveis, contraste de texto/foco, zoom, reflow e ausência de conteúdo encoberto. Estes são requisitos para inspeção, sem alegação de certificação WCAG ou teste assistivo já realizado.

## Critérios de aceite

1. A abertura oferece os quatro caminhos e deixa explícitos dados fictícios, ausência de operação financeira e revisão pendente. Nenhum caminho exige conta, upload no navegador ou conexão.
2. Os números do HTML correspondem ao relatório produzido pelo motor para os mesmos bytes; o SHA-256 é conferível e o JSON baixado conserva `pending`/`false`. Uma entrada com evidência posterior é recusada, sem caderno de sucesso.
3. O caso principal explica 60%/30% de parcelas e 10% de caixa; o benchmark explica 100% aplicado. As duas condições de custo preservam capital, preços, datas e pesos.
4. A interface diferencia taxas/slippage nominais da mudança do NAV, porcentagem de p.p. e fechamento de liquidação. “T+1” significa sessão seguinte fornecida, não liquidação financeira D+1.
5. A tabela e a narrativa permitem conferir a curva sem o gráfico; o acesso às quatro seções, detalhes e download funciona sem JavaScript.
6. HTML não incorpora URLs/textos/IDs de evidência, recursos remotos ou instruções executáveis da entrada. Não há telemetria, servidor, feed, envio de ordens ou chamada paga.
7. Testes de teclado, zoom/reflow e leitura assistiva são registrados com ambiente e resultado antes de qualquer declaração de acessibilidade homologada. Inspeção do código, teste automatizado e teste humano permanecem categorias distintas.

## Validação humana pendente

Plano formativo para pessoa leiga, sem coleta automática de eventos: o moderador registra manualmente sucesso, erro crítico e dificuldade observada. Metas propostas não são resultados medidos.

| Tarefa | Evidência de compreensão proposta | Estado |
| --- | --- | --- |
| Explicar saldo final, hipótese de pesos e caixa versus benchmark | Localiza valores e não interpreta excesso como recomendação ou risco equivalente | Pendente com participante humano |
| Distinguir soma de custos da redução do saldo final | Aponta as duas medidas e menciona unidades/exposição; explica bps com o exemplo disponível | Pendente com participante humano |
| Encontrar maior queda e interpretar o último dia | Identifica pico/queda e reconhece duas avaliações no mesmo dia | Pendente com participante humano |
| Conferir entrada T+1, hash e limites de autenticidade | Usa sessão 1, identifica horário UTC e não atribui autenticidade ao hash | Pendente com participante humano |
| Percorrer os quatro caminhos apenas com teclado e zoom | Destinos/foco perceptíveis, tabelas acessíveis e conteúdo sem corte impeditivo | Pendente em navegador e tecnologia assistiva |

Não há resultados de usuários reais neste documento. Recomendações de melhoria decorrentes dessas tarefas só podem ser chamadas de validadas após execução e registro das observações.
