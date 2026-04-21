param(
    [string]$ResourceGroup = "raviRG",
    [string]$Location = "australiaeast"
)

$ErrorActionPreference = "Stop"
$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$aciName = "$Prefix-daily"
$logicAppName = "sia-scheduler-9295"
$subId = "<your-subscription-id>"

$definition = @{
    '$schema' = "https://schema.management.azure.com/providers/Microsoft.Logic/schemas/2016-06-01/workflowdefinition.json#"
    contentVersion = "1.0.0.0"
    parameters = @{
        '$connections' = @{
            defaultValue = @{}
            type = "Object"
        }
    }
    triggers = @{
        daily_trigger = @{
            type = "Recurrence"
            recurrence = @{
                frequency = "Day"
                interval = 1
                schedule = @{
                    hours = @(20)
                    minutes = @(0)
                }
                timeZone = "UTC"
            }
        }
    }
    actions = @{
        start_container = @{
            type = "Http"
            inputs = @{
                method = "POST"
                uri = "https://management.azure.com/subscriptions/$subId/resourceGroups/$ResourceGroup/providers/Microsoft.ContainerInstance/containerGroups/$aciName/start?api-version=2023-05-01"
                authentication = @{
                    type = "ManagedServiceIdentity"
                }
            }
            runAfter = @{}
        }
    }
    outputs = @{}
} | ConvertTo-Json -Depth 20

$defPath = Join-Path $scriptRoot "logic_app_definition.json"
$definition | Out-File -FilePath $defPath -Encoding utf8

az extension add --name logic --upgrade --only-show-errors

az logic workflow create `
    --name $logicAppName `
    --resource-group $ResourceGroup `
    --location $Location `
    --definition "@$defPath" `
    --mi-system-assigned true `
    --state Enabled `
    --output none

$logicAppId = az logic workflow show --name $logicAppName --resource-group $ResourceGroup --query identity.principalId -o tsv
if ($logicAppId) {
    $aciResourceId = az container show --name $aciName --resource-group $ResourceGroup --query id -o tsv
    az role assignment create --assignee $logicAppId --role Contributor --scope $aciResourceId --output none
}

Write-Host "Scheduler created: $logicAppName"
Write-Host "Triggers daily at 20:00 UTC (6:00 AM AEST)"
