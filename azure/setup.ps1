param(
    [string]$ResourceGroup = "raviRG",
    [string]$Location = "australiasoutheast",
    [string]$Prefix = "sia",
    [string]$OpenAILocation = "australiaeast",
    [string]$StaticWebAppLocation = "eastasia",
    [string]$RecipientEmail = "ravishankar.nandagopalan@microsoft.com",
    [string]$SenderAddress = "",
    [string]$OpenAIDeployment = "gpt-4o",
    [string]$OpenAIModelName = "gpt-4o",
    [string]$OpenAIModelVersion = "2024-11-20"
)

$ErrorActionPreference = "Stop"

$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent $scriptRoot
$suffix = Get-Random -Minimum 1000 -Maximum 9999

function Exec([string]$Command) {
    Write-Host ">> $Command" -ForegroundColor Cyan
    Invoke-Expression $Command
}

function Get-JsonValue([string]$Command, [string]$Property) {
    $json = Invoke-Expression $Command | ConvertFrom-Json
    return $json.$Property
}

$storageName = ("$Prefix" + "st" + $suffix).ToLower()
$functionAppName = "$Prefix-daily-func-$suffix"
$openAIName = "$Prefix-openai-$suffix"
$commsName = "$Prefix-comms-$suffix"
$staticAppName = "$Prefix-dashboard-$suffix"
$dataContainer = "sia-data"
$staticContainer = '$web'

Exec "az group create --name $ResourceGroup --location $Location --output none"
Exec "az storage account create --name $storageName --resource-group $ResourceGroup --location $Location --sku Standard_LRS --kind StorageV2 --output none"
Exec "az storage blob service-properties update --account-name $storageName --static-website --index-document index.html --404-document 404.html --output none"

$storageConnectionString = az storage account show-connection-string --name $storageName --resource-group $ResourceGroup --query connectionString -o tsv
$storageWebEndpoint = az storage account show --name $storageName --resource-group $ResourceGroup --query primaryEndpoints.web -o tsv
Exec "az storage container create --name $dataContainer --connection-string `"$storageConnectionString`" --output none"

$existingOpenAI = az cognitiveservices account list --resource-group $ResourceGroup --query "[?kind=='OpenAI'].name | [0]" -o tsv
if ([string]::IsNullOrWhiteSpace($existingOpenAI)) {
    Exec "az cognitiveservices account create --name $openAIName --resource-group $ResourceGroup --location $OpenAILocation --kind OpenAI --sku S0 --yes --output none"
} else {
    $openAIName = $existingOpenAI
    Write-Host "Using existing Azure OpenAI resource: $openAIName" -ForegroundColor Yellow
}

$existingDeployment = az cognitiveservices account deployment list --name $openAIName --resource-group $ResourceGroup --query "[?name=='$OpenAIDeployment'].name | [0]" -o tsv
if ([string]::IsNullOrWhiteSpace($existingDeployment)) {
    Exec "az cognitiveservices account deployment create --name $openAIName --resource-group $ResourceGroup --deployment-name $OpenAIDeployment --model-name $OpenAIModelName --model-version $OpenAIModelVersion --model-format OpenAI --sku-name Standard --sku-capacity 10 --output none"
}

$openAIKey = az cognitiveservices account keys list --name $openAIName --resource-group $ResourceGroup --query key1 -o tsv
$openAIEndpoint = az cognitiveservices account show --name $openAIName --resource-group $ResourceGroup --query properties.endpoint -o tsv

$existingComms = az communication list --resource-group $ResourceGroup --query "[?name=='$commsName'].name | [0]" -o tsv
if ([string]::IsNullOrWhiteSpace($existingComms)) {
    Exec "az communication create --name $commsName --resource-group $ResourceGroup --location global --data-location australia --output none"
}
$acsConnectionString = az communication list-key --name $commsName --resource-group $ResourceGroup --query primaryConnectionString -o tsv

Exec "az functionapp create --resource-group $ResourceGroup --consumption-plan-location $Location --runtime python --runtime-version 3.11 --functions-version 4 --name $functionAppName --storage-account $storageName --output none"
Exec "az staticwebapp create --name $staticAppName --resource-group $ResourceGroup --location $StaticWebAppLocation --sku Free --output none"

$staticHostName = az staticwebapp show --name $staticAppName --resource-group $ResourceGroup --query defaultHostname -o tsv
$dashboardUrl = if ([string]::IsNullOrWhiteSpace($storageWebEndpoint)) { "https://$staticHostName" } else { $storageWebEndpoint.TrimEnd("/") }
$loginUrl = "$dashboardUrl/chat"

if ([string]::IsNullOrWhiteSpace($SenderAddress)) {
    Write-Warning "SenderAddress was not provided. Set SIA_EMAIL_SENDER manually after creating a verified sender/domain in Azure Communication Services."
}

$settings = @(
    "AZURE_OPENAI_ENDPOINT=$openAIEndpoint",
    "AZURE_OPENAI_KEY=$openAIKey",
    "AZURE_OPENAI_DEPLOYMENT=$OpenAIDeployment",
    "AZURE_OPENAI_API_VERSION=2024-10-21",
    "ACS_CONNECTION_STRING=$acsConnectionString",
    "SIA_EMAIL_SENDER=$SenderAddress",
    "RECIPIENT_EMAIL=$RecipientEmail",
    "BLOB_CONNECTION_STRING=$storageConnectionString",
    "SIA_DATA_CONTAINER=$dataContainer",
    "SIA_STATIC_CONTAINER=$staticContainer",
    "SIA_DASHBOARD_URL=$dashboardUrl",
    "SIA_LOGIN_URL=$loginUrl"
)

az functionapp config appsettings set --name $functionAppName --resource-group $ResourceGroup --settings $settings | Out-Null

$buildRoot = Join-Path $scriptRoot "build"
$packageRoot = Join-Path $buildRoot "functionapp"
$zipPath = Join-Path $buildRoot "functionapp.zip"

if (Test-Path $packageRoot) {
    Remove-Item -Path $packageRoot -Recurse -Force
}
if (Test-Path $zipPath) {
    Remove-Item -Path $zipPath -Force
}

New-Item -Path $packageRoot -ItemType Directory -Force | Out-Null
Copy-Item -Path (Join-Path $scriptRoot "function_app\function_app.py") -Destination (Join-Path $packageRoot "function_app.py")
Copy-Item -Path (Join-Path $scriptRoot "function_app\host.json") -Destination (Join-Path $packageRoot "host.json")
Copy-Item -Path (Join-Path $scriptRoot "daily_run.py") -Destination (Join-Path $packageRoot "daily_run.py")
Copy-Item -Path (Join-Path $scriptRoot "auth_middleware.py") -Destination (Join-Path $packageRoot "auth_middleware.py")
Copy-Item -Path (Join-Path $scriptRoot "requirements.txt") -Destination (Join-Path $packageRoot "requirements.txt")

Compress-Archive -Path (Join-Path $packageRoot "*") -DestinationPath $zipPath -Force
Exec "az functionapp deployment source config-zip --name $functionAppName --resource-group $ResourceGroup --src `"$zipPath`" --output none"

Exec "az storage blob upload --connection-string `"$storageConnectionString`" --container-name `"$staticContainer`" --name robots.txt --file `"$scriptRoot\static\robots.txt`" --overwrite true --content-type text/plain --output none"
Exec "az storage blob upload --connection-string `"$storageConnectionString`" --container-name `"$staticContainer`" --name staticwebapp.config.json --file `"$scriptRoot\staticwebapp.config.json`" --overwrite true --content-type application/json --output none"

Write-Host ""
Write-Host "Provisioning complete." -ForegroundColor Green
Write-Host "Function App: $functionAppName"
Write-Host "Azure OpenAI: $openAIName"
Write-Host "Communication Services: $commsName"
Write-Host "Static Web App: https://$staticHostName"
Write-Host "Storage static site: $dashboardUrl"
Write-Host ""
Write-Host "If SenderAddress was blank, set it after verifying a sender/domain in ACS:"
Write-Host "az functionapp config appsettings set --name $functionAppName --resource-group $ResourceGroup --settings SIA_EMAIL_SENDER=<verified-sender>"
