# Execute na pasta do projeto: . .\configurar-ia.exemplo.ps1
# Configura somente este terminal. Não grava a chave em arquivo.
param([switch]$DaAreaDeTransferencia)

$env:IA_PROVEDOR = "gemini"
$env:GEMINI_MODEL = "gemini-3.5-flash-lite"
if ($DaAreaDeTransferencia) {
    # Alternativa para terminais que inserem caracteres de controle no Read-Host.
    $env:GEMINI_API_KEY = ([string](Get-Clipboard -Raw)).Trim()
    Write-Host "Chave lida da área de transferência sem exibir o conteúdo."
} else {
    $chaveGeminiBiblioteca = Read-Host "Chave da API Gemini" -AsSecureString
    try {
        $env:GEMINI_API_KEY = [System.Net.NetworkCredential]::new("", $chaveGeminiBiblioteca).Password
    } finally {
        Remove-Variable chaveGeminiBiblioteca
    }
}
