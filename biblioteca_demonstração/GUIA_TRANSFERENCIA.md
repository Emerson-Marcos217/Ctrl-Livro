# Como usar a biblioteca em outro computador Windows

O pacote ZIP contém o código atualizado, as páginas e uma cópia consistente de
`db.sqlite3`: livros, categorias, usuários e empréstimos existentes no momento
da exportação. Mudanças feitas depois disso não entram no pacote.

O ambiente Python e o modelo do Ollama serão instalados novamente no destino.
As duas cópias da biblioteca terão bancos separados, sem sincronização automática.

## 1. Copie e extraia o projeto

Transfira o ZIP por pendrive ou outro meio de sua escolha. No outro computador,
clique com o botão direito e escolha **Extrair tudo**. Abra a pasta `biblioteca`
extraída: ela deve conter `manage.py`, `db.sqlite3` e os arquivos de requisitos.

Abra o PowerShell nessa pasta. Você pode abrir a pasta no Explorador de Arquivos,
digitar `powershell` na barra de endereço e pressionar Enter.

## 2. Instale os programas no outro computador

- Instale o **Python 3.14**, pelo [site oficial](https://www.python.org/downloads/windows/).
  Este projeto foi verificado com Python 3.14.7.
- Instale o [Ollama para Windows](https://ollama.com/download/windows) e abra-o.
  O Ollama exige Windows 10 22H2 ou mais recente.
- Feche e reabra o PowerShell após instalar os programas.

O modelo escolhido é pequeno para começar em um computador com 16 GB de RAM,
mas a velocidade e a memória disponível variam conforme o hardware e os outros
programas abertos. O Ollama e o modelo precisam de vários GB livres no disco.

## 3. Prepare o Python

Na pasta que contém `manage.py`, execute uma linha por vez:

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-transferencia.txt
.\.venv\Scripts\python.exe manage.py migrate
```

O arquivo `requirements-transferencia.txt` instala as mesmas versões das
dependências usadas na máquina de origem. Não é necessário ativar o ambiente
virtual, pois os comandos já usam o Python dele diretamente.

O banco copiado preserva os usuários e suas senhas. No primeiro acesso, faça
login novamente: esta instalação gera uma nova chave interna do Django.
Essa chave é diferente de uma chave de API; ela é criada automaticamente.

## 4. Baixe o modelo local

Com o Ollama aberto, execute:

```powershell
ollama pull qwen2.5:3b
```

Espere o comando terminar com sucesso. O modelo ocupa aproximadamente 1,9 GB
de download, além do espaço do programa Ollama. Não precisa de chave de API
nem de créditos. A instalação e o download inicial precisam de internet;
a geração das recomendações acontece no próprio computador.

Se `ollama` não for reconhecido em um terminal novo, tente o caminho padrão:

```powershell
& "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe" pull qwen2.5:3b
```

O projeto já escolhe `qwen2.5:3b` por padrão. Se o outro computador tiver uma
variável `OLLAMA_MODEL` apontando para outro modelo, defina neste PowerShell:

```powershell
$env:OLLAMA_MODEL = "qwen2.5:3b"
```

## 5. Teste e inicie

Ainda na pasta do projeto:

```powershell
.\.venv\Scripts\python.exe manage.py diagnosticar_ia
```

Espere a mensagem **Conexão e formato de resposta aceitos**. Em seguida:

```powershell
.\.venv\Scripts\python.exe manage.py runserver 8001
```

Abra [a biblioteca](http://127.0.0.1:8001/), entre com sua conta e use
**Encontre sua leitura**. O formulário tem apenas a pergunta e o botão de enviar.

Mantenha o aplicativo Ollama e o terminal do servidor abertos durante o uso.
Nos próximos dias, basta abrir o Ollama e executar novamente o comando
`manage.py runserver 8001` usando o Python da pasta `.venv`.

## Problemas mais comuns

- **Não encontrou requirements-transferencia.txt:** o PowerShell está em outra
  pasta ou o ZIP ainda não foi extraído. Abra a pasta que contém `manage.py`.
- **Não foi possível conectar ao Ollama:** abra o aplicativo Ollama no computador
  que está executando o Django.
- **Modelo não encontrado:** execute `ollama pull qwen2.5:3b` até concluir.
- **O site não abre:** mantenha o terminal com `runserver 8001` aberto e use
  exatamente `http://127.0.0.1:8001/` nesse mesmo computador.
- **Não lembro a senha:** o pacote mantém as contas existentes. Para criar outro
  bibliotecário local, use `.\.venv\Scripts\python.exe manage.py criar_bibliotecario`.

Mais informações: [guia da IA](GUIA_IA.md),
[Ollama no Windows](https://docs.ollama.com/windows) e
[modelo qwen2.5:3b](https://ollama.com/library/qwen2.5:3b).
