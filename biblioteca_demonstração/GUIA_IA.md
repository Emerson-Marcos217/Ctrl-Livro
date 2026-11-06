# Recomendações com IA — Gemini e Ollama

## Preparação para hospedagem: Gemini

O provedor é escolhido por `IA_PROVEDOR`. Use `gemini` para hospedagem ou
`ollama` para desenvolvimento local. Não há troca automática de provedor quando
uma chamada falha. Com DEBUG desligado ou na Vercel, o padrão é Gemini; em
desenvolvimento local, o padrão continua Ollama. Configure explicitamente na
hospedagem. Na Vercel, a opção Ollama é recusada, pois o endereço local não aponta
para o computador da biblioteca.

Foi preparada a chamada REST ao Gemini com saída JSON estruturada. A chave vai
somente no cabeçalho HTTPS `x-goog-api-key`; não aparece no navegador, na URL ou
em arquivos do projeto. O modelo padrão configurável é `gemini-3.5-flash-lite`.
Confirme a disponibilidade na sua conta pelo diagnóstico. Configurar o provedor
não garante acesso, cota gratuita nem qualidade das recomendações.

### Ativar e testar no computador

Mantenha o proxy aberto e use o terminal já configurado para o banco Firebase.
Se o terminal foi fechado, execute primeiro `. .\configurar-firebase.exemplo.ps1`.

```powershell
.\.venv\Scripts\python.exe manage.py migrate
. .\configurar-ia.exemplo.ps1
.\.venv\Scripts\python.exe manage.py diagnosticar_ia
```

A nova migration `0003_usoia` cria somente o contador de uso por leitor. Não
reimporte os livros. O script pede a chave sem exibi-la e a guarda apenas no
ambiente deste terminal. Obtenha a chave no [Google AI Studio](https://aistudio.google.com/apikey)
e não a envie no chat ou em capturas de tela. Não confunda a chave do Gemini com
credenciais de acesso ao banco Firebase.

Se a colagem no campo oculto falhar, prepare no terminal o comando
`. .\configurar-ia.exemplo.ps1 -DaAreaDeTransferencia`, mas ainda não pressione
Enter. Copie a chave pelo botão do AI Studio, volte ao terminal e pressione
Enter: o script lê a área de transferência sem imprimir seu conteúdo. Não copie
outro texto entre copiar a chave e executar o comando. Para verificar apenas o
formato, sem chamar a API, execute `manage.py diagnosticar_ia --configuracao`
com o Python do ambiente virtual. Essa verificação não comprova a validade da chave.

O diagnóstico faz duas chamadas com dados fictícios: interpretação do pedido e
seleção em um catálogo vazio. Não lê os livros nem as contas reais. Ele pode
consumir cota da API. Após o sucesso, reinicie o site no mesmo terminal:

```powershell
.\.venv\Scripts\python.exe manage.py runserver 8001
```

### Configuração que levaremos para a Vercel

| Variável no servidor | Valor |
| --- | --- |
| `IA_PROVEDOR` | `gemini` |
| `GEMINI_MODEL` | `gemini-3.5-flash-lite` (pode ser substituído por modelo compatível disponível na conta) |
| `GEMINI_API_KEY` | Chave secreta da API Gemini |

Cadastre a chave nas variáveis protegidas da hospedagem, sem prefixos públicos.
Não use o script PowerShell dentro da Vercel. As variáveis do banco, credenciais
Google do SQL Connect e configurações Django de produção também serão necessárias.
A conexão do banco na hospedagem não pode depender do proxy do computador.
Esta etapa prepara a IA; ainda não publica o site nem conclui sua configuração
de produção.

### Limites e falhas

- Cada pergunta pode usar até duas chamadas Gemini. Cada chamada tem timeout de
  rede de 20 segundos, no máximo 4096 tokens de saída e resposta de até 256 KB.
  O timeout de rede não é um prazo total rígido da página. Ao publicar, ajuste a
  duração da função para acomodar as duas chamadas e as consultas ao banco.
- Há intervalo de 5 segundos e limite de 20 tentativas por leitor a cada janela
  de uma hora, guardados no PostgreSQL para compartilhar o controle entre
  instâncias. Pedidos que falham também contam. Limpar a conversa ou trocar de
  navegador não reinicia esse contador. O diagnóstico não usa esse limite.
- Esse limite por leitor não é um teto financeiro global: configure também as
  cotas disponíveis na conta do provedor e acompanhe o consumo.
- Não há tentativas automáticas que multipliquem chamadas e custos. Erros de
  chave, configuração, cota, rede e serviço indisponível retornam uma mensagem
  tratada. Respostas bloqueadas, incompletas ou fora do formato não viram sugestões.
- Permanecem os limites atuais de 20 livros ativos, sinopses de até 2000 caracteres
  por livro e entrada de até 12000 bytes por chamada. A seleção ainda é
  conservadora; esta adaptação não implementa busca semântica em acervos grandes.

Com Gemini, são enviados o pedido, as mensagens anteriores relevantes do leitor e,
quando necessário, os dados dos livros candidatos. Não são enviados os campos de
conta, senha ou empréstimos. Dados pessoais digitados na pergunta fazem parte do
texto enviado. A tela informa o uso do Google; reveja as condições de tratamento
de dados e os limites do plano antes do uso público.

Referências: [API GenerateContent](https://ai.google.dev/api/generate-content),
[modelos](https://ai.google.dev/gemini-api/docs/models) e
[preços e tratamento de dados](https://ai.google.dev/gemini-api/docs/pricing).

## Opção local: Ollama

Para escolher o modo local no terminal de desenvolvimento:

```powershell
$env:IA_PROVEDOR = "ollama"
```

No modo local, o menu **Encontre sua leitura** usa o Ollama no mesmo computador que executa
o Django. O modelo padrão é **qwen2.5:3b**, uma opção pequena para começar em um PC
com 16 GB de RAM. A velocidade depende do processador, da placa de vídeo e dos
outros programas abertos. Não precisa de chave, créditos ou conta da OpenAI/Gemini.

## 1. Instale o Ollama e baixe o modelo

Instale o [Ollama para Windows](https://ollama.com/download/windows). Depois da
instalação, abra o aplicativo Ollama e um **novo PowerShell**. Execute:

```powershell
ollama pull qwen2.5:3b
```

Espere terminar o download: o modelo tem aproximadamente 1,9 GB. Você precisa de
internet para instalar e baixar o modelo; as recomendações depois são locais.
O Ollama também ocupa espaço em disco além do modelo. Não precisa abrir uma
conversa no aplicativo nem executar `ollama run` para usar o site.

Para desativar também os recursos de nuvem do próprio Ollama, execute uma vez:

```powershell
[Environment]::SetEnvironmentVariable("OLLAMA_NO_CLOUD", "1", "User")
```

Feche o Ollama pelo ícone ao lado do relógio e abra-o novamente para aplicar.
A biblioteca verifica se o modelo é local antes de enviar a conversa.

Se `ollama` não for reconhecido mesmo em um terminal novo, use o caminho padrão:

```powershell
& "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe" pull qwen2.5:3b
```

## 2. Teste a conexão

Abra o PowerShell na pasta da biblioteca, onde está `manage.py`, e execute:

```powershell
.\.venv\Scripts\python.exe manage.py diagnosticar_ia
```

O comando usa somente dados fictícios. A primeira chamada precisa carregar o
modelo e pode demorar alguns minutos. Aguarde a mensagem **Conexão e formato de
resposta aceitos**. Um teste automático com respostas simuladas não substitui
esse diagnóstico real.

## 3. Inicie o site

Se o servidor antigo estiver rodando, pare com **Ctrl+C**. Execute:

```powershell
.\.venv\Scripts\python.exe manage.py runserver 8001
```

Abra [a biblioteca](http://127.0.0.1:8001/), entre na sua conta e clique em
**Encontre sua leitura**. Use **Começar nova conversa** se houver uma conversa
antiga. Experimente: “Gosto de fantasia e viagens. Qual livro você recomenda?”.

Mantenha o Ollama aberto e o terminal do Django em execução. Se o Ollama não
iniciar pelo aplicativo, você pode abrir outro PowerShell e manter nele:

```powershell
$env:OLLAMA_NO_CLOUD = "1"
ollama serve
```

Se aparecer que a porta já está em uso, provavelmente o Ollama já está aberto:
não inicie outra cópia. Use o diagnóstico para confirmar a conexão.

## Como os livros chegam à IA

1. O Django lê os livros ativos do banco configurado (PostgreSQL ou SQLite). O formulário do assistente tem apenas
   o campo de pergunta; gênero, tema e ambientação devem ser descritos na mensagem.
2. A consulta usa o provedor escolhido: API Gemini ou Ollama local em
   `http://127.0.0.1:11434`. A seleção pode enviar título, autor, sinopse, categorias
   e quantidade disponível. Não envia contas, senhas ou registros de empréstimo.
3. O modelo extrai trechos curtos do pedido e das mensagens anteriores do leitor, identificando
   gênero, ambientação, temas, autores, títulos e exclusões. Respostas anteriores
   da IA não são usadas como fonte de preferências ou fatos. Gêneros inferidos
   que não foram escritos pelo leitor não viram restrições. Uma mudança explícita
   como “agora quero fantasia” inicia a interpretação de um novo pedido.
4. O Django confere os requisitos objetivos: categoria pelo cadastro; ambientação
   pela sinopse; título e autor pelos campos correspondentes. Requisitos separados
   precisam ser atendidos juntos.
5. Se houver temas, uma segunda chamada ao modelo avalia a relação com as sinopses
   dos candidatos e devolve trechos literais como evidência. Sem sinopse, um livro
   não participa da busca por tema ou ambientação.
6. A justificativa exibida é montada pelo sistema com categorias e trechos reais do
   cadastro. Texto livre produzido pelo modelo não é exibido. Os IDs, os dados e a
   disponibilidade são conferidos novamente antes de montar os cartões.

Por exemplo, “romance na Inglaterra rural” exige categoria Romance e menção à
Inglaterra rural na sinopse. Não permite substituir por uma aventura ou por uma
história em outro lugar. Se não houver comprovação, a página informa que não
houve correspondência, sem preencher a lista com alternativas aleatórias.

Essa conferência é conservadora: ambientações precisam aparecer no cadastro,
com os termos identificados no pedido (ignorando acentos e maiúsculas). Ela pode
deixar de encontrar uma correspondência descrita com sinônimos ou implícita.
A interpretação das preferências e dos temas ainda depende do modelo local e
pode falhar; conferir uma citação não prova sozinho sua relevância semântica.
Não é feita uma verificação externa da exatidão das sinopses cadastradas.

A IA não executa SQL e não altera livros ou empréstimos. Pode interpretar mal
uma preferência; cadastre sinopses e categorias para melhorar as sugestões.
O modelo pequeno pode ser menos preciso que serviços maiores.

Para caber na memória e no contexto do modelo, a consulta aceita até **20 livros**
e até **12.000 bytes de entrada**, incluindo instruções e histórico. Se a conversa ultrapassar o limite de texto, o site pede uma nova conversa.
Acervos acima de 20 livros ainda exigem ampliar a seleção desta versão; nesse caso,
o site orienta a explorar o catálogo. Não descarta silenciosamente os excedentes. As sinopses enviadas
têm no máximo 2.000 caracteres por livro.

## Problemas comuns

- **Não foi possível conectar:** abra o Ollama no mesmo computador do Django.
- **Modelo não encontrado / HTTP 404:** execute `ollama pull qwen2.5:3b`.
- **Pouca memória / HTTP 500:** feche jogos e programas pesados; execute o
  diagnóstico para conferir a causa exata. Ter 16 GB instalados não significa
  que toda essa memória esteja disponível.
- **Demorou demais:** a geração tem limite de espera de 180 segundos. Espere o
  computador terminar o trabalho atual, peça apenas um livro e comece uma nova conversa.
- **Ainda mostra Gemini ou pede chave:** pare o servidor antigo e inicie novamente
  usando esta pasta. `GEMINI_API_KEY` e `OPENAI_API_KEY` não são lidas pelo assistente.

Para trocar de modelo local, baixe-o primeiro e configure, no terminal do Django:

```powershell
$env:OLLAMA_MODEL = "nome-do-modelo-local:tag"
```

Reinicie o Django. O modelo precisa suportar respostas estruturadas em JSON e
caber na memória disponível. Para voltar ao padrão:

```powershell
Remove-Item Env:OLLAMA_MODEL -ErrorAction SilentlyContinue
```

## Arquivos principais e testes

- `livro/recomendacoes.py`: interpretação, seleção do catálogo e escolha do provedor.
- `livro/gemini.py`: chamada HTTPS, resposta estruturada e tratamento das falhas do Gemini.
- `livro/limites_ia.py`: controle de tentativas por leitor, compartilhado pelo banco.
- `livro/catalogo.py`: consulta dos livros ativos e contagem de exemplares disponíveis, usada pelo catálogo e pelo assistente.
- `livro/preferencias.py`: conferência dos requisitos e montagem dos motivos a partir de evidências.
- `livro/views_ia.py`: formulário e histórico da conversa.
- `biblioteca/settings.py`: provedor, modelo e leitura da chave pelas variáveis do servidor.
- `templates/livro/assistente.html`: página de recomendações.

```powershell
.\.venv\Scripts\python.exe manage.py test --noinput
```

Para testar também o formulário com o modelo real (é necessário manter o Ollama
aberto e o modelo instalado):

```powershell
$env:TESTAR_OLLAMA = "1"
.\.venv\Scripts\python.exe manage.py test livro.test_ollama_real --noinput
Remove-Item Env:TESTAR_OLLAMA
```

Esse teste usa livros fictícios em um banco de teste, sem alterar o acervo real.
Ele verifica pedidos simples, gênero junto com ambientação, ausência de
correspondência, continuidade e mudança de preferência na conversa.

Referências: [API de conversa](https://docs.ollama.com/api/chat),
[respostas estruturadas](https://docs.ollama.com/capabilities/structured-outputs),
[modelo Qwen 2.5 3B](https://ollama.com/library/qwen2.5:3b) e
[configuração local e privacidade](https://docs.ollama.com/faq).
