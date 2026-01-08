# Azure Content Understanding Setup Guide

This guide will help you set up Azure Content Understanding (part of Azure AI Foundry) for your AfwezigheidsAttest application.

## Step 1: Create Azure AI Foundry Resource

Azure Content Understanding is part of Azure AI Foundry (formerly Azure AI Studio).

1. **Go to Azure Portal**: https://portal.azure.com
2. **Create a new resource**:
   - Search for "Azure AI Foundry" or "Azure AI hub"
   - Click "Create"
3. **Configure the resource**:
   - **Subscription**: Select your Azure subscription
   - **Resource Group**: Create new or use existing
   - **Region**: Choose a region (e.g., West Europe, East US)
   - **Name**: Choose a unique name (e.g., `afwezigheidsattest-foundry`)
   - **Pricing Tier**: Select appropriate tier
4. **Review and Create**

## Step 2: Get Your Credentials

1. After deployment, go to your Azure AI Foundry resource
2. In the left menu, click **"Keys and Endpoint"**
3. Copy the following:
   - **Endpoint**: Should end with `.services.ai.azure.com/` (e.g., `https://your-resource-name.services.ai.azure.com/`)
   - **Key 1** or **Key 2**: Your API key

## Step 3: Configure Local Development

1. **Copy the example settings file**:
   ```powershell
   Copy-Item api\local.settings.json.example api\local.settings.json
   ```

2. **Edit `api/local.settings.json`** and add your credentials:
   ```json
   {
     "IsEncrypted": false,
     "Values": {
       "AzureWebJobsStorage": "UseDevelopmentStorage=true",
       "FUNCTIONS_WORKER_RUNTIME": "python",
       "AzureWebJobsFeatureFlags": "EnableWorkerIndexing",
       "AZURE_CONTENT_UNDERSTANDING_ENDPOINT": "https://your-resource-name.services.ai.azure.com/",
       "AZURE_CONTENT_UNDERSTANDING_KEY": "your-actual-api-key-here"
     }
   }
   ```

3. **Install updated Python dependencies**:
   ```powershell
   cd api
   .venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```

## Step 4: Test the Integration

1. **Start the Azure Function**:
   ```powershell
   cd api
   func start
   ```

2. **In another terminal, start the frontend**:
   ```powershell
   cd frontend
   npm run dev
   ```

3. **Open your browser**: http://localhost:5173
4. **Upload a test document** (PDF, JPG, or PNG)

## What the Application Does

The Azure Function will:
1. ✅ Receive the uploaded file
2. ✅ Send it to Azure Content Understanding for analysis
3. ✅ Extract dates and check for signatures
4. ✅ Validate the document:
   - **Invalid** if it contains dates in the future
   - **Invalid** if it's missing a signature
5. ✅ Return a clear message explaining why it's valid or invalid

## Validation Rules

- **Future Dates**: Documents with dates after today are rejected
- **Missing Signature**: Documents without signatures are rejected
- **Valid Document**: Must have all dates in the past/present AND contain a signature

## Understanding Azure Content Understanding

Azure Content Understanding provides advanced document analysis capabilities:

- **Layout Analysis**: Extracts text, tables, and document structure
- **Prebuilt Models**: Ready-to-use analyzers for common document types
- **API Details**:
  - API Version: 2025-11-01 (GA)
  - Endpoint Pattern: `/contentunderstanding/analyzers/{analyzerId}:analyzeBinary`
  - Analyzer Used: `prebuilt-layout` (extracts text and layout)
  - Authentication: API Key via `Ocp-Apim-Subscription-Key` header

## Troubleshooting

### Error: "Azure Content Understanding is niet geconfigureerd"
- Check that your `local.settings.json` has the correct endpoint and key
- Verify endpoint ends with `.services.ai.azure.com/`
- Restart the Azure Function after updating settings

### Error: "Unauthorized" or "Access Denied"
- Verify your API key is correct
- Check that your Azure subscription is active
- Ensure the key hasn't been regenerated

### Error: "Analyzer not found"
- Ensure you're using a valid analyzer ID (e.g., `prebuilt-layout`)
- Check that your Foundry resource has the necessary models deployed

### No dates or signatures detected
- Try using a clearer document
- Ensure the document has visible text and signatures
- PDF format typically works best

## For Production Deployment

When deploying to Azure, add these Application Settings to your Function App:
- `AZURE_CONTENT_UNDERSTANDING_ENDPOINT`
- `AZURE_CONTENT_UNDERSTANDING_KEY`

You can set these in the Azure Portal under:
**Function App → Configuration → Application Settings**

## Additional Resources

- [Azure AI Foundry Documentation](https://learn.microsoft.com/azure/ai-studio/)
- [Azure Content Understanding Documentation](https://learn.microsoft.com/azure/ai-services/content-understanding/)
- [Azure Functions Python Developer Guide](https://learn.microsoft.com/azure/azure-functions/functions-reference-python)
- [Azure Content Understanding Python Samples](https://github.com/Azure-Samples/azure-ai-content-understanding-python)
