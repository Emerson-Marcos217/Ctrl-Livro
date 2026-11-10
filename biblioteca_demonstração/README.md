
Projeto em Python e Django 5.2. Usa SQLite no desenvolvimento e tem integração
preparada com Firebase SQL Connect e seu PostgreSQL no Cloud SQL.
Requer Python 3.11 ou superior; a hospedagem está configurada para Python 3.14.

Para preparar a publicação na Vercel com Cloud SQL e Gemini, siga
[GUIA_VERCEL.md](GUIA_VERCEL.md). A configuração hospedada usa o conector oficial
do Google, sem depender do proxy aberto em um computador.

Para configurar o banco online, transferir os dados e ativar a consulta do acervo
pelo Firebase, siga [GUIA_FIREBASE.md](GUIA_FIREBASE.md).

O assistente está no menu **Encontre sua leitura**. Para hospedagem, usa a API
**Gemini**, com chave apenas no servidor. **Ollama** permanece como opção local.
Veja o passo a passo de configuração e a explicação do código em [GUIA_IA.md](GUIA_IA.md).

Cada livro deve ter de 1 a 3 categorias, escolhidas nas caixas de seleção do
cadastro ou da edição. O catálogo permite filtrar por várias categorias:
mostra livros de qualquer uma das categorias marcadas. Sem marcações,
considera todas. Os filtros podem ser combinados com a busca e a disponibilidade.

Ao atualizar uma instalação existente, execute `manage.py migrate` com o Python
do ambiente virtual. A migração de categorias preserva a categoria anterior de
cada livro. Ela não pode ser revertida automaticamente para uma única categoria;
faça uma cópia de segurança do banco antes da atualização.

Abra o PowerShell na pasta que contém o arquivo `manage.py`.

Se ainda não preparou o ambiente:

```powershell rodar um por vez
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe manage.py migrate
```

Para criar um bibliotecário:

```powershell
.\.venv\Scripts\python.exe manage.py criar_bibliotecario
```

Informe e-mail, nome, senha e confirmação da senha. A senha não aparece enquanto é digitada.

Para iniciar o site:

```powershell
.\.venv\Scripts\python.exe manage.py runserver 8001
```

Acesse http://127.0.0.1:8001/ e mantenha o terminal aberto.
Para parar, pressione Ctrl+C.
