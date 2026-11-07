# Atualizar o Ctrl-Livro no GitHub

O repositório é https://github.com/Emerson-Marcos217/Ctrl-Livro.
Ele contém um README na raiz e o código em `biblioteca_demonstração/`.
Mantenha essa estrutura: não coloque uma segunda pasta de projeto dentro dela.

Foi preparada uma cópia Git em `transferencia/github-atualizacao` do projeto
original. A cópia preserva o histórico e tem uma branch separada para a atualização.
O projeto original, fora dessa cópia, não tem `.git`; alterações nele não são
enviadas automaticamente ao GitHub. Escolha uma cópia de trabalho e mantenha-a
atualizada, para não editar versões diferentes sem perceber.

## Revisar antes de enviar

Na raiz da cópia que contém `.git`:

```powershell
git status
git diff
git diff --cached --stat
```

Antes de iniciar uma nova atualização a partir de uma cópia limpa, consulte o
estado remoto com `git fetch origin`. Revise eventuais alterações de outras
pessoas antes de integrar a nova versão. Evite `push --force` e recriar o
repositório: não são necessários para atualizar arquivos.

O `.gitignore` exclui ambiente virtual, cache, banco SQLite, backups, credenciais
e arquivos `.env`. Arquivos já versionados precisam ser retirados do índice com
`git rm --cached` para que essa regra passe a valer. Na atualização preparada,
o banco e os caches antigos foram retirados apenas do índice; as cópias físicas
foram preservadas. Isso não remove arquivos de commits anteriores do GitHub.

As migrations em `livro/migrations/` são código e devem ser versionadas. Os
arquivos `configurar-*.exemplo.ps1` também podem ser enviados: eles pedem as
credenciais no terminal, sem gravá-las no código.

## Registrar e publicar

Depois da revisão, registre os arquivos e crie um commit. A autoria Git precisa
estar configurada com o nome e o e-mail que você escolheu:

```powershell
git add --all
git diff --cached --check
git commit -m "Atualiza integracoes Firebase e Gemini"
git push -u origin HEAD
```

O último comando envia a branch atual e pode pedir login no GitHub. Depois,
abra um Pull Request para comparar essa branch com `main` e incorporar a
atualização revisada. Só a cópia que contém `.git` participa desse fluxo.

Enviar código não publica o site na Vercel, não transfere o banco e não configura
as chaves na hospedagem. Esses passos são feitos separadamente.
