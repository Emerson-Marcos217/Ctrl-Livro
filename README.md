# Ctrl-Livro

Sistema de biblioteca em Python e Django, com acervo, reservas, empréstimos e
recomendações por IA. O projeto usa PostgreSQL no Cloud SQL e Firebase SQL
Connect; SQLite permanece disponível para desenvolvimento. A IA pode usar a
API Gemini ou o Ollama local.

O código da aplicação está na pasta **biblioteca_demonstração**. Execute os
comandos de instalação, configuração e inicialização dentro dessa pasta:

```powershell
cd biblioteca_demonstração
```

- [Instalação e execução](biblioteca_demonstração/README.md)
- [Banco Firebase e migração dos dados](biblioteca_demonstração/GUIA_FIREBASE.md)
- [Configuração da IA](biblioteca_demonstração/GUIA_IA.md)
- [Transferência para outro computador](biblioteca_demonstração/GUIA_TRANSFERENCIA.md)

Senhas, chaves, bancos locais, backups e ambientes virtuais não devem ser
versionados. Configure as credenciais no ambiente em que o site será executado.
Esta versão prepara as integrações; a publicação na Vercel é uma etapa separada.
