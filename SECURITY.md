# Segurança e escopo financeiro

Uso educacional, com arquivos sintéticos. Não é fundo, serviço de gestão, recomendação individual, ordem executável ou validação de rentabilidade. Não coletar posições, extratos, dados de clientes, API keys ou credenciais. Não tentar usar IDs fictícios para disfarçar dados reais.

O núcleo não faz rede, chamadas LLM, subprocessos ou operações em broker. JSON tem schema estrito, limites e valores finitos em strings decimais. Texto/URL de evidência é dado, não comando, e não deve aparecer no relatório. O hash fixa bytes, mas não autentica fonte, verdade, data de publicação, autoria ou licença.

O caderno HTML usa o mesmo validador e cálculos Python, sem upload de dados,
requisição externa ou execução de evidências. O JavaScript local apenas marca
a seção atual; tabelas e download continuam disponíveis sem ele. A política
CSP recusa conexões, objetos, formulários e base externa. Os dados financeiros
publicados e o hash continuam visíveis; isso não é anonimização universal.

`tools/run_exercises.py` é ferramenta separada de desenvolvimento: inicia a
CLI local por argumentos fixos, com ambiente reduzido, sem shell. Não faz parte
do caminho de cálculo do núcleo nem aceita comandos de evidências.

Saída sempre pending/execution_allowed=false; não é autorização para consumidor externo. Tampouco é um bloqueio geral de outras ferramentas que o ChatGPT possua. Uma etapa futura requer identidade e controle de acesso no servidor, autorização vinculada à ação, quotas e verificação independente.

CLI requer filesystem POSIX com controles no-follow e arquivo regular. Arquivo existente não é sobrescrito; evitar diretórios compartilhados adversariais. Não é sandbox do disco, API de upload, servidor multiusuário ou garantia universal contra corridas. Windows não homologado.

Ausência de dependências runtime de terceiros reduz superfície, não prova ausência de vulnerabilidades. Manter Python atualizado. Antes de conectar dados reais, revisar licença do feed, temporalidade, vieses, liquidez, impostos e a operação concreta com responsáveis competentes; MIT do código não concede dados, marcas ou serviço de corretagem.

Relatar falhas privadamente ao responsável do repositório sem dados sensíveis. Não há SLA/programa de recompensa prometido. Rollback: reverter PR/descartar relatórios experimentais; nenhuma migração ou conta financeira foi modificada.
