param(
    [string]$ResourceGroup = "raviRG",
    [string]$Location = "australiaeast",
    [string]$Prefix = "sia"
)

$ErrorActionPreference = "Stop"
$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent $scriptRoot
$suffix = "9295"

$acrName = "${Prefix}acr${suffix}"
$aciName = "${Prefix}-daily-${suffix}"
$imageName = "${acrName}.azurecr.io/sia-daily:latest"
$storageName = "siast${suffix}"
$openAIName = "$Prefix-openai"
$commsName = "${Prefix}-comms-${suffix}"

Write-Host "Creating Container Registry..." -ForegroundColor Cyan
az acr create --name $acrName --resource-group $ResourceGroup --location $Location --sku Basic --admin-enabled true --output none

Write-Host "Building and pushing Docker image..." -ForegroundColor Cyan
az acr build --registry $acrName --image sia-daily:latest --file "$scriptRoot\Dockerfile" $scriptRoot

$acrPassword = az acr credential show --name $acrName --query "passwords[0].value" -o tsv
$openAIKey = az cognitiveservices account keys list --name $openAIName --resource-group $ResourceGroup --query key1 -o tsv
$openAIEndpoint = az cognitiveservices account show --name $openAIName --resource-group $ResourceGroup --query properties.endpoint -o tsv
$storageConnStr = az storage account show-connection-string --name $storageName --resource-group $ResourceGroup --query connectionString -o tsv

try {
    $acsConnStr = az communication list-key --name $commsName --resource-group $ResourceGroup --query primaryConnectionString -o tsv 2>$null
    if (-not $acsConnStr) {
        throw "ACS connection string unavailable."
    }
} catch {
    $acsConnStr = "PLACEHOLDER_SET_LATER"
    Write-Warning "ACS not ready yet. Set ACS_CONNECTION_STRING manually later."
}

$storageWebEndpoint = az storage account show --name $storageName --resource-group $ResourceGroup --query primaryEndpoints.web -o tsv

Write-Host "Creating Container Instance..." -ForegroundColor Cyan
az container create `
    --resource-group $ResourceGroup `
    --name $aciName `
    --image $imageName `
    --registry-login-server "${acrName}.azurecr.io" `
    --registry-username $acrName `
    --registry-password $acrPassword `
    --cpu 1 --memory 1 `
    --restart-policy Never `
    --environment-variables `
        AZURE_OPENAI_ENDPOINT="$openAIEndpoint" `
        AZURE_OPENAI_DEPLOYMENT="gpt-4o" `
        AZURE_OPENAI_API_VERSION="2024-10-21" `
        RECIPIENT_EMAIL="your-email@example.com" `
        SIA_DASHBOARD_URL="$storageWebEndpoint" `
        SIA_LOGIN_URL="${storageWebEndpoint}chat" `
        BLOB_CONNECTION_STRING="$storageConnStr" `
        SIA_DATA_CONTAINER="sia-data" `
        SIA_STATIC_CONTAINER='$web' `
    --secure-environment-variables `
        AZURE_OPENAI_KEY="$openAIKey" `
        ACS_CONNECTION_STRING="$acsConnStr" `
    --output none

Write-Host ""
Write-Host "Deployment complete!" -ForegroundColor Green
Write-Host "Container: $aciName"
Write-Host "ACR: $acrName"
Write-Host "Image: $imageName"
Write-Host ""
Write-Host "To run manually: az container start --name $aciName --resource-group $ResourceGroup"
Write-Host "To check logs: az container logs --name $aciName --resource-group $ResourceGroup"
Write-Host ""
Write-Host "For daily scheduling, run .\schedule_daily.ps1 to create the Logic App trigger."
