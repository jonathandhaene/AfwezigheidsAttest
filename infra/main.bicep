// Azure Infrastructure as Code - Bicep
// Deploy Azure Static Web App with Function App backend

@description('Location for all resources')
param location string = 'westeurope'

@description('Name of the Static Web App')
param staticWebAppName string = 'swa-afwezigheidsattest'

@description('Name of the Function App')
param functionAppName string = 'func-afwezigheidsattest-${uniqueString(resourceGroup().id)}'

@description('Name of the App Service Plan')
param appServicePlanName string = 'asp-afwezigheidsattest'

@description('Name of the Storage Account')
param storageAccountName string = 'stafwa${uniqueString(resourceGroup().id)}'

@description('SKU for Static Web App')
@allowed([
  'Free'
  'Standard'
])
param sku string = 'Standard'

@description('Azure Content Understanding Endpoint')
@secure()
param azureContentUnderstandingEndpoint string

@description('Azure Content Understanding API Key')
@secure()
param azureContentUnderstandingKey string

@description('Azure Content Understanding Analyzer ID')
param azureContentUnderstandingAnalyzerId string

@description('SQL Server')
param sqlServer string

@description('SQL Database')
param sqlDatabase string

@description('Azure Tenant ID')
param azureTenantId string

// Storage Account for Function App
resource storageAccount 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: storageAccountName
  location: location
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    supportsHttpsTrafficOnly: true
    minimumTlsVersion: 'TLS1_2'
    allowSharedKeyAccess: true
    publicNetworkAccess: 'Enabled'
  }
}

// App Service Plan for Function App
resource appServicePlan 'Microsoft.Web/serverfarms@2023-01-01' = {
  name: appServicePlanName
  location: location
  sku: {
    name: 'Y1'
    tier: 'Dynamic'
  }
  properties: {
    reserved: true
  }
}

// Function App
resource functionApp 'Microsoft.Web/sites@2023-01-01' = {
  name: functionAppName
  location: location
  kind: 'functionapp,linux'
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    serverFarmId: appServicePlan.id
    siteConfig: {
      linuxFxVersion: 'Python|3.11'
      appSettings: [
        {
          name: 'AzureWebJobsStorage__accountName'
          value: storageAccount.name
        }
        {
          name: 'FUNCTIONS_WORKER_RUNTIME'
          value: 'python'
        }
        {
          name: 'FUNCTIONS_EXTENSION_VERSION'
          value: '~4'
        }
        {
          name: 'AzureWebJobsFeatureFlags'
          value: 'EnableWorkerIndexing'
        }
        {
          name: 'AZURE_TENANT_ID'
          value: azureTenantId
        }
        {
          name: 'AZURE_CONTENT_UNDERSTANDING_ENDPOINT'
          value: azureContentUnderstandingEndpoint
        }
        {
          name: 'AZURE_CONTENT_UNDERSTANDING_KEY'
          value: azureContentUnderstandingKey
        }
        {
          name: 'AZURE_CONTENT_UNDERSTANDING_ANALYZER_ID'
          value: azureContentUnderstandingAnalyzerId
        }
        {
          name: 'SQL_SERVER'
          value: sqlServer
        }
        {
          name: 'SQL_DATABASE'
          value: sqlDatabase
        }
      ]
      cors: {
        allowedOrigins: [
          'https://${staticWebApp.properties.defaultHostname}'
        ]
      }
    }
    httpsOnly: true
  }
  tags: {
    'azd-service-name': 'api'
  }
}

// Role assignment: Storage Blob Data Owner for Function App
resource storageBlobDataOwnerRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(storageAccount.id, functionApp.id, 'StorageBlobDataOwner')
  scope: storageAccount
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'b7e6dc6d-f1e8-4753-8033-0f276bb0955b') // Storage Blob Data Owner
    principalId: functionApp.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

// Role assignment: Storage Account Contributor for Function App
resource storageAccountContributorRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(storageAccount.id, functionApp.id, 'StorageAccountContributor')
  scope: storageAccount
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '17d1049b-9a84-46fb-8f53-869881c3d3ab') // Storage Account Contributor
    principalId: functionApp.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

// Role assignment: Storage Queue Data Contributor for Function App
resource storageQueueDataContributorRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(storageAccount.id, functionApp.id, 'StorageQueueDataContributor')
  scope: storageAccount
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '974c5e8b-45b9-4653-ba55-5f855dd0fb88') // Storage Queue Data Contributor
    principalId: functionApp.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

// Static Web App
resource staticWebApp 'Microsoft.Web/staticSites@2023-01-01' = {
  name: staticWebAppName
  location: location
  sku: {
    name: sku
    tier: sku
  }
  properties: {
    buildProperties: {
      appLocation: '/frontend'
      apiLocation: '/api'
      outputLocation: 'dist'
    }
  }
  tags: {
    'azd-service-name': 'web'
  }
}

// Link Static Web App to Function App
resource staticWebAppLinkedBackend 'Microsoft.Web/staticSites/linkedBackends@2023-01-01' = {
  parent: staticWebApp
  name: 'functionapp'
  properties: {
    backendResourceId: functionApp.id
    region: location
  }
}

// Output the Static Web App URL
output staticWebAppUrl string = staticWebApp.properties.defaultHostname
output staticWebAppId string = staticWebApp.id
output functionAppUrl string = functionApp.properties.defaultHostName
output functionAppName string = functionApp.name
