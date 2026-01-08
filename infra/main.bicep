// Azure Infrastructure as Code - Bicep
// Deploy Azure Static Web App with Function App backend

@description('Location for all resources')
param location string = resourceGroup().location

@description('Name of the Static Web App')
param staticWebAppName string = 'swa-afwezigheidsattest'

@description('SKU for Static Web App')
@allowed([
  'Free'
  'Standard'
])
param sku string = 'Free'

// Static Web App
resource staticWebApp 'Microsoft.Web/staticSites@2023-01-01' = {
  name: staticWebAppName
  location: location
  sku: {
    name: sku
    tier: sku
  }
  properties: {
    repositoryUrl: '' // Configure with your GitHub repo
    branch: 'main'
    buildProperties: {
      appLocation: '/frontend'
      apiLocation: '/api'
      outputLocation: 'dist'
    }
  }
}

// Output the Static Web App URL
output staticWebAppUrl string = staticWebApp.properties.defaultHostname
output staticWebAppId string = staticWebApp.id
