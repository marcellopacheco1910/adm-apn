# Gestão ADM · Pestalozzi de Niterói

Aplicação web modular recuperada a partir dos anexos e requisitos desta conversa. Este é um código reconstruído: preserva os dados e funções verificadas; não é uma restauração byte a byte dos arquivos do ambiente anterior.

## Testar sem instalar

Abra `Gestao-ADM-Previa.html` no navegador, extraído do pacote entregue. É uma cópia autossuficiente dos dados iniciais, sem servidor, importação ou sincronização. Contém dados reais e deve ser compartilhada apenas com pessoas autorizadas.

## Servidor local

Python 3.12. Instale `python -m pip install -r requirements-local.txt` (preferencialmente em ambiente virtual). Inicie `python app.py --port 8000` na raiz. O servidor escuta apenas no próprio computador. A futura versão online não exigirá instalação no computador dos usuários.

Testes: `python -m unittest discover -s tests -v` e `node tests/test_ui.js`.

## Módulos

- Dados Contábeis: competência com mês/ano; acumulado com ano e todos os meses disponíveis; trimestre com trimestre/ano. Plano de contas como botão interno, 965 contas, posições patrimoniais e consulta.
- Importações contábeis: prévia, conferência, confirmação e histórico de revisões, sem duplicar a versão ativa.
- Faturamento e produção: janeiro–setembro/2026, reabilitação DI/DF, Oficina Ortopédica/OPM, SUS × Não SUS e Particular × Convênio. Não SUS = Particular + Convênio; Convênio inclui CLIN.
- Relatório anual: produção assistencial, com impressão/PDF. Não é um relatório financeiro.

Balancetes de janeiro a agosto são preliminares. Dados faltantes não equivalem a zero. Pacientes acumulados são soma de registros mensais, não pessoas únicas. Itens OPM não compõem atendimentos e não comprovam entrega física. Divergências da origem são preservadas.

## Persistência e fontes

`data/initial.json`: balancetes extraídos e hash de cada fonte. `data/plan.json`: plano completo. `data/faturamento.json`: bases, conferências e registros de importação originais da planilha anual. O primeiro início cria o banco SQLite em `data/balancetes.sqlite3`; pode ser movido via `APN_DATA_DIR`. Não apagar esse banco para atualizar o aplicativo.

`save` substitui integralmente o mês ativo preservando versões. `scripts/recover_data.py` reconstrói dados dos anexos disponíveis em `/workspace/attachments` usando xlrd/openpyxl. É script de recuperação; não é uma rotina que deve sobrescrever novas cargas. Não alterar fontes originais.

`python scripts/export_preview.py` gera a prévia inicial. `python scripts/package.py` produz o ZIP e hashes. A prévia representa os dados iniciais, não alterações do banco em uso. Um novo mapa de produção ainda não pode ser importado pela interface.

## Logo

A logomarca original está incorporada em `static/logo-pestalozzi.png`, extraída sem alteração do HTML enviado pelo usuário. Ela aparece automaticamente no topo do menu, em fundo branco, preservando as proporções. A prévia autossuficiente incorpora os mesmos bytes PNG. Selecionar logomarca permite testar outra imagem no navegador; Baixar prévia com logo inclui a imagem escolhida na cópia HTML.

## Azure e acesso

Veja `deploy/azure.md`. Preparação WSGI para Gunicorn, armazenamento persistente e Microsoft Entra ID institucional. Não houve publicação. A autenticação real e a instalação do servidor de produção dependem de validação no Azure.

## Recuperação e GitHub

Os dados são confidenciais: usar somente repositório privado. Não incluir senhas, tokens ou banco operacional no Git. O ambiente anterior está indisponível e o GitHub ainda pode estar inacessível pelo proxy. Cópia local e ZIP não comprovam envio remoto.

## Particulares

Módulo separado de Faturamento e Produção. Consulta janeiro–setembro/2026 do arquivo `Gestao_Particular_APN_2026.xlsx`, com fonte direta e convênios sem CLIN/SUS. A receita gerencial conjunta é R$ 80.051,31; pessoal R$ 112.817,61; saldo após pessoal −R$ 32.766,30. Conferido contra Financeiro e Mensal da planilha. Não são arrecadação recebida nem lucro líquido.

Quatro abas: Financeiro, Pacientes e produtividade, Convênios e glosas, Carregamentos mensais. Seleção única de período mensal, trimestral ou anual. Custos em `data/private_costs.json` com vigência explícita. Folha técnica e administrativo compartilhados são considerados uma única vez; rateio administrativo mensal por quantidade. Sem custo vigente ou uma das fontes, não há resultado conjunto completo. O custo conjunto permanece mesmo sem atendimentos; rateio por especialidade fica indisponível.

Carga mensal disponível no servidor: envie o gerencial XLSX atualizado com Base, Base Convenios, Status Convenios, Conferencia e Custos no formato recebido. Escolha fonte e competência, confira prévia e confirme. Não são aceitas ainda planilhas operacionais em outros formatos. Cada fonte/competência é substituída integralmente preservando o histórico; reenvio idêntico não duplica. A prévia HTML é somente consulta e não carrega arquivos.

As fórmulas do XLSX precisam ter valores calculados salvos. O importador verifica os valores gerenciais contra quantidade × valor e preserva divergências. Cabeçalhos e recebimento por fonte são validados. Atualização salarial não ocorre por importação de arquivo: a referência vigente é preservada e precisa de nova versão após fevereiro/2027.

`data/private_initial.json` guarda uma extração sem nomes, prontuários ou recibos, com identificadores técnicos para deduplicação. Esses identificadores não tornam o conjunto anônimo: tratar como dados restritos. A fonte original é preservada localmente em `APN_DATA_DIR/source-archives` (ou `data/source-archives`), sem acesso por URL, excluída do Git e do pacote distribuído. Backup do ambiente deve incluir esse diretório e o banco. Os detalhes nominais e a edição de salários ainda não têm interface. `scripts/import_particulares.py` é para migração inicial, não para sobrescrever uma base em uso.

Validação realizada: totais financeiros e pacientes por especialidade/mês conferidos com a planilha; vigência vencida, fonte ausente, mês sem movimento, rateio, substituição e reenvio idêntico testados. Aparência e upload real em navegador ainda precisam de homologação pelo usuário. Os totais de atendimento do módulo Particulares seguem o detalhado; não são forçados a coincidir com os consolidados usados pelo módulo de Produção.
