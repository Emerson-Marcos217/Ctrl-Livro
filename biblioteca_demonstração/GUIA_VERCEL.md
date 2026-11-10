# Hospedar o Ctrl-Livro na Vercel

O código está preparado para publicação. A hospedagem real ainda precisa receber
as credenciais, passar pelo primeiro build e ser testada pelo endereço online.
Nenhum serviço é criado e nenhum dado é importado ao abrir este projeto.

## O que ficará em cada lugar

- **Vercel:** executa o Django e entrega as páginas, CSS e JavaScript.
- **Cloud SQL do projeto Firebase `biblioteca-38922`:** guarda usuários, livros,
  exemplares, empréstimos e limites de uso da IA. É o PostgreSQL já usado pelo app.
- **Firebase SQL Connect:** consulta o acervo publicado no conector `biblioteca`.
- **Gemini:** recebe a pergunta e os dados necessários para recomendar livros.

Na Vercel, o conector oficial do Google estabelece a conexão autenticada e
criptografada com o Cloud SQL. O computador e o Cloud SQL Auth Proxy local não
precisam ficar ligados. O Ollama também não participa dessa configuração.
As páginas mostram os dados atuais ao consultar o servidor; hospedar não adiciona,
por si só, atualização automática de uma página que já está aberta.

## 1. Preparar a identidade do servidor no Google

Esta etapa será feita no projeto **biblioteca-38922**. O login pessoal usado no
computador não será copiado para a Vercel.

1. No Google Cloud, abra **IAM e administrador → Contas de serviço** e crie uma
   conta para o site, por exemplo `biblioteca-vercel`.
2. Conceda **Cloud SQL Client** (`roles/cloudsql.client`) para acessar a instância.
3. Para a consulta do acervo, crie um papel personalizado contendo somente
   `firebasedataconnect.connectors.impersonateQuery` e atribua-o à conta de serviço.
   A API usada pelo projeto é `:impersonateQuery`; a consulta permanece com
   `@auth(level: NO_ACCESS)`, acessível pelo servidor autorizado.
4. Em **Chaves**, crie uma chave JSON dessa conta de serviço. Guarde fora do
   projeto. Seu conteúdo completo será a variável protegida
   `GOOGLE_CREDENTIALS_JSON` da Vercel. Não envie esse conteúdo no chat ou ao GitHub.

A permissão IAM conecta ao serviço; o usuário PostgreSQL e sua senha continuam
sendo necessários para acessar as tabelas. Inicialmente usamos o usuário existente
`biblioteca_django`. Não é necessário recriar o banco nem importar o backup.
O servidor não precisa de papéis de proprietário ou administrador do projeto.

O código também pode usar credenciais locais do `gcloud` quando executado fora da
Vercel. Futuramente, a identidade da hospedagem pode ser substituída por federação
de identidade, evitando uma chave permanente; essa integração não está implementada.

## 2. Conferir o código no GitHub

Use o repositório `Emerson-Marcos217/Ctrl-Livro`, preservando sua estrutura atual.
A pasta que a Vercel precisa executar é a que contém `manage.py`, `requirements.txt`
e `vercel.json`.

No formato atual do repositório, selecione **Root Directory**:
`biblioteca_demonstração`. Se posteriormente esses arquivos forem movidos para a
raiz do repositório, a Root Directory deverá acompanhar essa mudança.

As alterações preparadas neste computador ainda precisam ser incluídas na branch
que será publicada. Siga `GUIA_GITHUB.md`; a cópia de trabalho principal e a cópia
Git em `transferencia/github-atualizacao` são pastas diferentes.

Não inclua `.venv`, `db.sqlite3`, backups, `.local-secret`, arquivos `.env`, chaves
Google ou pastas de transferência. `.gitignore` e `.vercelignore` cobrem esses
arquivos e diretórios convencionais; mantenha qualquer credencial fora do código.

## 3. Importar na Vercel e cadastrar as variáveis

Na Vercel, importe o repositório, selecione a pasta acima e o framework **Django**.
Mantenha os comandos de instalação/build e a pasta de saída nos padrões do
framework. A versão Python está definida como **3.14** em `.python-version`.
O `vercel.json` configura até 120 segundos para a função Django.

Cadastre as variáveis **antes do primeiro deploy**, no ambiente que será usado:

| Variável | Valor |
| --- | --- |
| `DJANGO_DEBUG` | `0` |
| `DJANGO_SECRET_KEY` | Uma chave aleatória exclusiva e permanente desta instalação |
| `BIBLIOTECA_BANCO` | `firebase` |
| `BIBLIOTECA_CONEXAO` | `connector` |
| `CLOUD_SQL_CONNECTION_NAME` | `biblioteca-38922:us-east4:biblioteca-38922-instance` |
| `PGDATABASE` | `biblioteca-database` |
| `PGUSER` | `biblioteca_django` |
| `PGPASSWORD` | A senha desse usuário PostgreSQL |
| `GOOGLE_CREDENTIALS_JSON` | O conteúdo completo do JSON da conta de serviço |
| `SQL_CONNECT_ATIVO` | `1` |
| `SQL_CONNECT_PROJECT` | `biblioteca-38922` |
| `SQL_CONNECT_LOCATION` | `us-east4` |
| `SQL_CONNECT_SERVICE` | `biblioteca-service` |
| `SQL_CONNECT_CONNECTOR` | `biblioteca` |
| `IA_PROVEDOR` | `gemini` |
| `GEMINI_API_KEY` | A chave do Gemini validada no diagnóstico |
| `GEMINI_MODEL` | `gemini-3.5-flash-lite` |

Marque os valores secretos como sensíveis/protegidos onde a interface permitir.
Não use prefixos de variáveis públicas do navegador. Não copie asteriscos no lugar
das chaves reais. `VERCEL=1` é fornecido pela plataforma, não precisa ser cadastrado.

Para gerar a chave do Django, execute localmente e guarde o resultado como segredo:

```powershell
.\.venv\Scripts\python.exe -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Os domínios fornecidos por `VERCEL_URL` e `VERCEL_PROJECT_PRODUCTION_URL` são aceitos
automaticamente. Para um domínio próprio, adicione `DJANGO_ALLOWED_HOSTS` com os
nomes exatos, separados por vírgulas, sem `https://` ou caminhos. Exemplo:
`biblioteca.exemplo.com,www.biblioteca.exemplo.com`.

Os formulários na mesma origem não precisam de configuração adicional de CSRF.
Se houver outra origem legítima, configure `DJANGO_CSRF_TRUSTED_ORIGINS` com as URLs
completas HTTPS separadas por vírgulas. Nunca use `*` para liberar todos os domínios.

**Não cadastre `PGHOST=127.0.0.1`, `PGPORT` ou `PGSSLMODE` na Vercel.** Essas opções
pertencem ao modo de conexão local; o conector controla o transporte hospedado.
A instância precisa ter IP público disponível e a Cloud SQL Admin API habilitada.
O conector usa autenticação IAM e TLS; não é necessário liberar todas as redes
(`0.0.0.0/0`) na instância.

## 4. Verificar o banco antes de publicar

No computador, mantenha o proxy aberto e, em outro PowerShell na pasta do projeto:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
. .\configurar-firebase.exemplo.ps1
.\.venv\Scripts\python.exe manage.py showmigrations
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py diagnosticar_firebase
. .\configurar-ia.exemplo.ps1
.\.venv\Scripts\python.exe manage.py diagnosticar_ia
```

Confira que está no banco online antes de executar migrações. `migrate` aplica
apenas as migrações pendentes; não carrega novamente o backup. Esta preparação da
hospedagem não acrescentou uma migração de dados. Migrações não rodam no build da
Vercel, evitando alterações concorrentes em cada publicação.

Para testar o novo transporte também no computador, depois de configurar o banco:

```powershell
$env:BIBLIOTECA_CONEXAO = "connector"
$env:CLOUD_SQL_CONNECTION_NAME = "biblioteca-38922:us-east4:biblioteca-38922-instance"
.\.venv\Scripts\python.exe manage.py diagnosticar_firebase
```

Esse teste usa seu login Google local e a senha já informada, sem utilizar o proxy.
Ele não valida a conta de serviço da Vercel, que deverá ser testada no deploy.
Para voltar ao modo anterior, use `$env:BIBLIOTECA_CONEXAO = "proxy"`.

## 5. Publicar e conferir o endereço online

Após conferir as variáveis, publique. A Vercel instala as dependências, prepara os
arquivos estáticos com `collectstatic` e disponibiliza uma URL HTTPS.
Abra essa URL e confira:

- login de leitor e bibliotecário, logout e envio de formulários;
- carregamento do catálogo e das categorias;
- cadastro de um livro de teste pelo bibliotecário e sua exibição para o leitor;
- solicitação e processamento de um empréstimo de teste;
- recomendação do Gemini e mensagens de limite/erro;
- aparência do site e acesso pelo celular.

Ao usar estas variáveis, um deploy de Preview acessa **o mesmo banco real**.
Use registros de teste identificados e não forneça credenciais de produção a
branches de terceiros. Para testes isolados, configure outro banco e outro
conector no ambiente de Preview antes de usar esse ambiente.

Feche o proxy e desligue o servidor local ao conferir a URL online: ela deverá
continuar funcionando. Alterações futuras no GitHub podem gerar novas publicações
automáticas, conforme a branch de produção escolhida na Vercel.

## Verificações técnicas e limites

- A configuração hospedada recusa SQLite, DEBUG ligado, segredo Django ausente e
  conexão pelo proxy do computador.
- As credenciais só são carregadas quando há acesso ao Google; preparar arquivos
  estáticos não consulta nem modifica o acervo.
- Cookies usam HTTPS; o Django reconhece o HTTPS encaminhado pela Vercel.
- HSTS está habilitado por uma hora. As opções de incluir todos os subdomínios e
  entrar na lista de preload não estão ativadas: exigem controle desses domínios.
  `check --deploy` pode apresentar os avisos opcionais W005 e W021 sobre isso.
- Os limites de IA e as sessões permanecem no PostgreSQL. Não dependem da memória
  de uma única função. Conexões de banco fecham ao terminar cada requisição.
- Não há armazenamento persistente de uploads na função. Se forem adicionadas
  capas por upload, será necessário um serviço de armazenamento de arquivos.
- O build real e a conexão com a identidade da Vercel só estarão confirmados
  depois da publicação e dos testes online. Testes locais não substituem isso.
- Confira os limites e a cobrança dos serviços antes da publicação. O teste do
  Cloud SQL não equivale a um banco gratuito permanente.

Referências oficiais:
[Django na Vercel](https://vercel.com/docs/frameworks/full-stack/django),
[Python na Vercel](https://vercel.com/docs/functions/runtimes/python),
[Cloud SQL Python Connector](https://github.com/GoogleCloudPlatform/cloud-sql-python-connector),
[IAM do SQL Connect](https://firebase.google.com/docs/sql-connect/iam-configuration).
