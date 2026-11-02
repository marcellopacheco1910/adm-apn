# Azure App Service · preparação, sem publicação

Python 3.12 em Linux. Startup command `bash deploy/start-azure.sh`; instalar requirements.txt no build. Usar uma instância com armazenamento persistente em /home e APN_DATA_DIR=/home/apn-data. Definir APN_PUBLIC_ORIGIN=https://<aplicativo>.azurewebsites.net e APN_ENV=production. HTTPS obrigatório.

Login Microsoft institucional com Entra ID, tenant único da Pestalozzi, autenticação obrigatória no App Service, usuários/grupos explicitamente atribuídos. Confirmar domínio e Tenant ID com o administrador; nunca solicitar senhas no chat. Configurar MFA/políticas do tenant. Somente depois da autenticação da plataforma configurada e verificada definir APN_AZURE_AUTH_ENABLED=1. O cabeçalho X-MS-CLIENT-PRINCIPAL-ID só é confiável atrás da autenticação Azure que elimina cabeçalhos forjados; a checagem na aplicação é uma proteção adicional, não um login independente.

Validar: acesso anônimo bloqueado, usuário institucional atribuído permitido, conta pessoal/outro tenant e usuário não atribuído bloqueados. Confirmar persistência após reinício e backup/restauração do banco. Sem esses testes, não liberar dados contábeis online. /healthz é verificação sem dados financeiros; compatibilizar com a autenticação da plataforma.

SQLite deve permanecer em uma única instância. Antes de escalar horizontalmente, migrar para banco de dados adequado. Configurar backup automático fora da instância com cópia consistente pela API SQLite. Não há perfis internos de leitura/edição ainda. Todos os usuários autorizados têm capacidade de importar.
