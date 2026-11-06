# Execute no PowerShell com: . .\configurar-firebase.exemplo.ps1
# Configurado para biblioteca-38922. A senha será solicitada ao executar.
# Este script NÃO cria serviços nem publica o projeto.
$env:BIBLIOTECA_BANCO = "firebase"
$env:PGHOST = "127.0.0.1" # Cloud SQL Auth Proxy executando neste computador
$env:PGPORT = "5432"
$env:PGDATABASE = "biblioteca-database"
$env:PGUSER = "biblioteca_django"
$senhaBancoBiblioteca = Read-Host "Senha do usuário PostgreSQL" -AsSecureString
$env:PGPASSWORD = [System.Net.NetworkCredential]::new("", $senhaBancoBiblioteca).Password
Remove-Variable senhaBancoBiblioteca
# O Proxy faz a conexão criptografada com o Google; este trecho é somente loopback.
# Para uma conexão direta remota, use a configuração TLS exigida pelo Cloud SQL.
$env:PGSSLMODE = "disable"
$env:SQL_CONNECT_PROJECT = "biblioteca-38922"
$env:SQL_CONNECT_LOCATION = "us-east4"
$env:SQL_CONNECT_SERVICE = "biblioteca-service"
$env:SQL_CONNECT_CONNECTOR = "biblioteca"
# Conector publicado e leitura validada no projeto biblioteca-38922.
$env:SQL_CONNECT_ATIVO = "1"
