# Firebase SQL Connect na biblioteca

## O que está preparado

Esta integração usa **um único PostgreSQL no Cloud SQL**, associado ao Firebase
SQL Connect. Não usa Firestore nem sincroniza duas cópias do acervo.

- Django grava livros, categorias, exemplares, usuários, reservas e empréstimos
  nesse PostgreSQL, preservando suas migrations, permissões e transações.
- Django aplica os filtros e a paginação. Com `SQL_CONNECT_ATIVO=1`, os dados dos
  livros da página são lidos pela API do SQL Connect, com credenciais do servidor.
- Detalhes, painel, autenticação e IA continuam consultando o mesmo banco pelo
  Django. Não foi reescrita toda a aplicação para usar GraphQL.
- `dataconnect/schema/schema.gql` define uma consulta de leitura das tabelas
  existentes. O conector não oferece operações públicas nem gravações que possam
  contornar as regras de empréstimos.
- SQLite continua disponível para desenvolvimento. A escolha de Firebase é
  explícita; uma falha de configuração não faz a aplicação voltar ao SQLite.

Para uma nova instalação, crie o projeto, o banco e publique o conector seguindo
as etapas abaixo. Os testes locais não comprovam as permissões ou o funcionamento
de uma conta Firebase real.
Esta etapa também não publica o site, não hospeda Ollama e não implementa
atualização automática da página já aberta.

## 1. Criar os recursos

No console Firebase, crie o projeto e configure SQL Connect com uma instância
**Cloud SQL for PostgreSQL**. Confira a cobrança apresentada antes de confirmar
recursos. O banco temporário de demonstração não serve para esta integração.

Anote: ID do projeto, região, ID do serviço SQL Connect, ID da instância e nome do
banco. Crie um usuário PostgreSQL para o Django. O usuário que executar migrations
precisa poder criar tabelas, índices e restrições.

Instale as ferramentas oficiais Firebase CLI, Google Cloud CLI e Cloud SQL Auth
Proxy. Use autenticação pessoal no desenvolvimento e credenciais de serviço
adequadas na hospedagem. Nunca envie senhas ou JSON de credenciais para o GitHub.

## 2. Preparar as ferramentas e fazer uma cópia dos dados

Na pasta do `manage.py`:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Pare o servidor local e mantenha-o parado durante a exportação e a troca do banco.
Em um terminal ainda configurado para SQLite, exporte os dados:

```powershell
$env:BIBLIOTECA_BANCO = "sqlite"
$env:SQL_CONNECT_ATIVO = "0"
New-Item -ItemType Directory -Force backups | Out-Null
$arquivoExportacao = "backups/migracao-" + (Get-Date -Format "yyyyMMdd-HHmmss") + ".json"
.\.venv\Scripts\python.exe -X utf8 manage.py dumpdata --natural-foreign --natural-primary --exclude contenttypes --exclude auth.permission --exclude admin.logentry --exclude sessions.session --output $arquivoExportacao
```

Confira se o comando concluiu sem erros e guarde esse arquivo em local protegido.
Ele contém dados de usuários e hashes de senhas. O `db.sqlite3` original permanece
intacto. Não volte a cadastrar dados na versão SQLite depois da migração: os bancos
não são sincronizados. As sessões antigas não são transferidas; faça login de novo.

## 3. Conectar ao PostgreSQL

Autentique as ferramentas, usando a conta com acesso ao projeto:

```powershell
gcloud auth application-default login
firebase login
```

O Cloud SQL Auth Proxy precisa de permissão `Cloud SQL Client`. Inicie-o em outro
terminal, ligado apenas ao endereço local. Substitua a identificação completa:

```powershell
cloud-sql-proxy --address 127.0.0.1 --port 5432 PROJETO:REGIAO:INSTANCIA
```

Preencha os nomes no arquivo `configurar-firebase.exemplo.ps1` e execute:

```powershell
. .\configurar-firebase.exemplo.ps1
.\.venv\Scripts\python.exe manage.py migrate
```

O script pede a senha sem exibi-la. As variáveis valem para esse terminal e seus
processos. Na hospedagem, elas precisam ser cadastradas nas configurações do
serviço; não use a configuração de Proxy local como se fosse um endereço remoto.

Importe **uma vez, em banco de destino novo**, usando o caminho real gerado na
etapa anterior:

```powershell
.\.venv\Scripts\python.exe manage.py loaddata $arquivoExportacao
```

Não importe sobre um banco já utilizado sem revisar possíveis conflitos. Se abriu
outro terminal, atribua a `$arquivoExportacao` o caminho do arquivo exportado.

## 4. Publicar a consulta do SQL Connect

Edite `dataconnect/dataconnect.yaml` com região, serviço, instância e banco reais.
O banco deve ser exatamente o mesmo de `PGDATABASE`. Mantenha
`schemaValidation: COMPATIBLE`: o Django também tem tabelas que não aparecem no
conector. Não use `STRICT` nem deixe o Firebase remover essas tabelas.

No Firebase, associe o serviço à instância e ao banco criados. Depois:

```powershell
firebase dataconnect:sql:setup --project SEU_ID_DO_PROJETO
```

Quando perguntar se o SQL Connect deve gerenciar as migrations SQL, **recuse**.
Neste projeto, as migrations são responsabilidade do Django. Configure o acesso
de leitura do serviço às tabelas existentes, seguindo o fluxo da ferramenta.

```powershell
firebase dataconnect:sql:diff --project SEU_ID_DO_PROJETO
```

Revise a saída antes de publicar. Esta integração expõe uma view de leitura e não
precisa substituir as tabelas do Django. Se aparecerem remoções ou alterações nas
tabelas, pare e revise o banco e o esquema selecionados.

```powershell
firebase deploy --only dataconnect --project SEU_ID_DO_PROJETO
```

O servidor Django precisa de uma identidade Google com autorização IAM para
executar a consulta do conector. Não é uma chave de API de navegador. O nível
`NO_ACCESS` impede chamadas comuns do navegador; a API é chamada com OAuth/IAM
pelo servidor no endpoint `impersonateQuery`, com a permissão
`firebasedataconnect.connectors.impersonateQuery`. Use permissões restritas, sem conceder
Owner à aplicação. Em produção, configure Application Default Credentials pela
identidade do ambiente ou por `GOOGLE_APPLICATION_CREDENTIALS` apontando para um
arquivo de credenciais protegido fora do repositório.

## 5. Diagnosticar e ativar

No terminal onde configurou PostgreSQL e os identificadores do SQL Connect:

```powershell
.\.venv\Scripts\python.exe manage.py diagnosticar_firebase
```

O diagnóstico verifica o PostgreSQL, faz uma consulta autenticada e compara uma
amostra de até 12 livros, sem imprimir informações pessoais ou credenciais.

Depois de passar:

```powershell
$env:SQL_CONNECT_ATIVO = "1"
.\.venv\Scripts\python.exe manage.py runserver 8001
```

Teste login, cadastro, filtros, reserva e devolução. Em outra conta, abra o acervo
e confirme que o livro cadastrado aparece. Atualizar sem F5 será uma etapa separada.

## Referências oficiais

- [Banco existente e migrations próprias](https://firebase.google.com/docs/sql-connect/manage-services-and-databases#integrate-existing-cloud-sql-for-postgresql-databases)
- [Arquivos de configuração](https://firebase.google.com/docs/sql-connect/configuration-reference)
- [API REST impersonateQuery (servidor)](https://firebase.google.com/docs/reference/sql-connect/rest/v1/projects.locations.services.connectors/impersonateQuery)
- [Cloud SQL Auth Proxy](https://cloud.google.com/sql/docs/postgres/connect-auth-proxy)

## Verificação local do código

```powershell
.\.venv\Scripts\python.exe manage.py test --noinput
```

Execute em ambiente de desenvolvimento. Os testes da API simulam respostas;
`diagnosticar_firebase` é a validação necessária contra o serviço real. O teste de
Ollama continua opcional e não faz parte da migração de banco.

Para compilar apenas o esquema e a consulta localmente, sem criar recursos:

```powershell
npx --yes firebase-tools dataconnect:compile --non-interactive
```

Sem um projeto Firebase criado, não acrescente `--project` a essa compilação
local. A compilação valida GraphQL e configuração, mas não executa a consulta SQL
contra as tabelas: isso será conferido por `diagnosticar_firebase` após a criação
do banco.
