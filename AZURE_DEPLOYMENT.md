# Azure Deployment Guide for Students 🎓

This guide is specifically for deploying ArpadBot using **Azure for Students** (free $100 credit).

## Prerequisites

✅ Azure for Students account verified
✅ GitHub account with your bot repo
✅ Discord bot token ready

---

## Method 1: Azure Portal (Easiest - No Code)

### Step 1: Activate Azure for Students

1. Go to [azure.microsoft.com/students](https://azure.microsoft.com/students)
2. Sign in with your school email
3. Verify student status
4. Get $100 free credit (no credit card needed!)

### Step 2: Create Web App

1. Go to [portal.azure.com](https://portal.azure.com)
2. Click **"Create a resource"**
3. Search for **"Web App"**
4. Click **Create**

**Configuration:**
- **Subscription**: Azure for Students
- **Resource Group**: Click "Create new" → name it `ArpadBotRG`
- **Name**: `arpadbot` (or your preferred name - must be unique)
- **Publish**: Code
- **Runtime stack**: Python 3.11
- **Operating System**: Linux
- **Region**: East US (or closest to you)
- **Pricing Plan**: 
  - Click "Create new" → name it `ArpadBotPlan`
  - Size: **B1** (Basic - $13/month, but covered by your free credit!)

5. Click **Review + Create**
6. Click **Create** (takes 1-2 minutes)

### Step 3: Configure Environment Variables

1. Once deployed, click **"Go to resource"**
2. In left menu, find **"Configuration"** under Settings
3. Click **"New application setting"** for each:
   - Name: `BOT_TOKEN` → Value: `YOUR_DISCORD_BOT_TOKEN`
   - Name: `PYTHONUNBUFFERED` → Value: `1`
   - Name: `SCM_DO_BUILD_DURING_DEPLOYMENT` → Value: `true`

4. Click **Save** at the top
5. Click **Continue** when prompted

### Step 4: Deploy from GitHub

1. In left menu, find **"Deployment Center"**
2. Select **GitHub** as source
3. Click **Authorize** (log in to GitHub)
4. Select:
   - **Organization**: Your GitHub username
   - **Repository**: `ArpadDiscordBot`
   - **Branch**: `main`
5. Click **Save** at the top

**Azure will now:**
- Connect to your GitHub repo
- Install dependencies from `requirements.txt`
- Start your bot automatically
- Auto-deploy whenever you push to `main` branch 🎉

### Step 5: Enable Bot API & Dashboard

1. In left menu, click **"Configuration"**
2. Add these settings:
   - Name: `WEBSITES_PORT` → Value: `8080`
3. Click **Save**

Your bot will now run at:
- Bot: Running on Discord
- Dashboard: `https://arpadbot.azurewebsites.net` (replace with your app name)
- Bot API: `https://arpadbot.azurewebsites.net:8081`

### Step 6: Update Config

Create a startup file to enable both bot API and dashboard:

1. In your local repo, update `config.json`:
```json
{
  "bot_api": {
    "enabled": true,
    "port": 8081,
    "url": "https://arpadbot.azurewebsites.net:8081"
  },
  "dashboard": {
    "enabled": true,
    "port": 8080
  }
}
```

2. Commit and push:
```bash
git add config.json
git commit -m "Configure for Azure deployment"
git push origin main
```

Azure will auto-deploy in ~2 minutes!

### Step 7: Check Logs

1. In Azure Portal → Your Web App
2. Left menu → **"Log stream"**
3. Watch your bot start up
4. Look for: `"Logged in as YourBotName"`

---

## Method 2: Azure CLI (For Advanced Users)

### Install Azure CLI

**Windows:**
```powershell
winget install Microsoft.AzureCLI
```

**macOS:**
```bash
brew install azure-cli
```

**Linux:**
```bash
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash
```

### Deploy with CLI

```bash
# Login
az login

# Create resource group
az group create --name ArpadBotRG --location eastus

# Create app service plan (B1 = Basic, covered by student credit)
az appservice plan create \
  --name ArpadBotPlan \
  --resource-group ArpadBotRG \
  --sku B1 \
  --is-linux

# Create web app
az webapp create \
  --name arpadbot \
  --resource-group ArpadBotRG \
  --plan ArpadBotPlan \
  --runtime "PYTHON:3.11"

# Set environment variables
az webapp config appsettings set \
  --name arpadbot \
  --resource-group ArpadBotRG \
  --settings \
    BOT_TOKEN="YOUR_DISCORD_TOKEN" \
    PYTHONUNBUFFERED="1" \
    SCM_DO_BUILD_DURING_DEPLOYMENT="true"

# Deploy from local directory
az webapp up \
  --name arpadbot \
  --resource-group ArpadBotRG \
  --runtime "PYTHON:3.11"

# OR deploy from GitHub
az webapp deployment source config \
  --name arpadbot \
  --resource-group ArpadBotRG \
  --repo-url https://github.com/YOUR_USERNAME/ArpadDiscordBot \
  --branch main \
  --manual-integration
```

---

## Separate Bot & Dashboard Deployment

### Deploy Bot Only

**App 1: Discord Bot**
```bash
az webapp create --name arpadbot-bot --resource-group ArpadBotRG --plan ArpadBotPlan --runtime "PYTHON:3.11"

az webapp config appsettings set --name arpadbot-bot --resource-group ArpadBotRG --settings \
  BOT_TOKEN="YOUR_TOKEN" \
  bot_api_enabled="true" \
  bot_api_port="8081" \
  dashboard_enabled="false"
```

**App 2: Dashboard**
```bash
az webapp create --name arpadbot-dashboard --resource-group ArpadBotRG --plan ArpadBotPlan --runtime "PYTHON:3.11"

az webapp config appsettings set --name arpadbot-dashboard --resource-group ArpadBotRG --settings \
  dashboard_enabled="true" \
  dashboard_port="8080" \
  bot_api_url="https://arpadbot-bot.azurewebsites.net:8081"

# Set startup command for dashboard only
az webapp config set --name arpadbot-dashboard --resource-group ArpadBotRG \
  --startup-file "uvicorn dashboard:app --host 0.0.0.0 --port 8080"
```

---

## Cost Breakdown (Covered by Student Credit)

| Service | Tier | Cost/Month | Your Cost |
|---------|------|------------|-----------|
| App Service Plan B1 | Basic | $13.14 | **$0** (free credit) |
| Bandwidth | First 5GB | Free | **$0** |
| Storage | 10GB | Included | **$0** |
| **Total** | | $13.14/month | **FREE for 7+ months!** |

Your $100 credit lasts ~7 months with one B1 app.

---

## Monitoring & Logs

### View Live Logs
1. Azure Portal → Your Web App
2. **Monitoring** → **Log stream**
3. Or use CLI:
```bash
az webapp log tail --name arpadbot --resource-group ArpadBotRG
```

### Check Bot Status
Visit: `https://arpadbot.azurewebsites.net/api/health`

Should return:
```json
{
  "status": "ok",
  "bot_name": "ArpadBot",
  "latency": 0.05
}
```

### Restart Bot
**Portal:**
1. Your Web App → **Overview**
2. Click **Restart** at top

**CLI:**
```bash
az webapp restart --name arpadbot --resource-group ArpadBotRG
```

**Dashboard:**
1. Go to `https://arpadbot.azurewebsites.net`
2. Click **Bot Control** tab
3. Click **Restart Bot** button

---

## Troubleshooting

### Bot not starting?

**Check logs:**
```bash
az webapp log tail --name arpadbot --resource-group ArpadBotRG
```

**Common issues:**
1. ❌ `BOT_TOKEN` not set → Add in Configuration
2. ❌ `config.json` missing → Ensure it's in repo (not in `.gitignore`)
3. ❌ Wrong Python version → Change to 3.11 in Configuration → General Settings
4. ❌ Port conflict → Azure uses port 8080 by default, set `WEBSITES_PORT=8080`

### Dashboard not accessible?

1. Ensure `dashboard.enabled: true` in config
2. Check `WEBSITES_PORT=8080` is set
3. Allow a few minutes for deployment to complete
4. Try `https://YOUR-APP-NAME.azurewebsites.net` (not http)

### Auto-deploy not working?

1. Portal → Deployment Center → **Logs**
2. Check for build errors
3. Ensure `requirements.txt` exists
4. Re-sync: Deployment Center → **Sync** button

### "Bot is offline" in dashboard?

1. Ensure bot API is enabled: `bot_api.enabled: true`
2. Check bot API URL matches your actual Azure URL
3. Verify bot is running: check Log stream
4. Wait 30 seconds for auto-health-check

---

## Scaling (When Your Bot Grows)

### Upgrade Plan
**Portal:**
1. Your Web App → **Scale up (App Service plan)**
2. Choose:
   - **B2**: $26/month (more memory)
   - **S1**: $70/month (production-ready)

**CLI:**
```bash
az appservice plan update --name ArpadBotPlan --resource-group ArpadBotRG --sku B2
```

### Add Custom Domain
1. Your Web App → **Custom domains**
2. Click **Add custom domain**
3. Follow wizard (requires domain ownership)

---

## Security Best Practices

### 1. Never commit secrets
```bash
# Ensure config.json is in .gitignore
echo "config.json" >> .gitignore
git add .gitignore
git commit -m "Ignore config.json"
```

### 2. Use Key Vault (Optional, Advanced)
Store bot token in Azure Key Vault instead of config:
```bash
az keyvault create --name arpadbotkeys --resource-group ArpadBotRG --location eastus
az keyvault secret set --vault-name arpadbotkeys --name BOT-TOKEN --value "YOUR_TOKEN"
```

### 3. Enable HTTPS only
1. Your Web App → **TLS/SSL settings**
2. Turn ON **HTTPS Only**

---

## Clean Up (Stop Charges)

If you want to delete everything:

**Portal:**
1. Go to **Resource Groups**
2. Click `ArpadBotRG`
3. Click **Delete resource group** at top

**CLI:**
```bash
az group delete --name ArpadBotRG --yes
```

⚠️ This removes EVERYTHING (bot, logs, config). Backup first!

---

## Alternative: Azure Container Instances (Cheaper)

For even lower cost (~$10/month):

```bash
# Build Docker image
docker build -t arpadbot .

# Push to Azure Container Registry
az acr create --name arpadbotregistry --resource-group ArpadBotRG --sku Basic
az acr login --name arpadbotregistry
docker tag arpadbot arpadbotregistry.azurecr.io/arpadbot:latest
docker push arpadbotregistry.azurecr.io/arpadbot:latest

# Deploy to Container Instance
az container create \
  --name arpadbot \
  --resource-group ArpadBotRG \
  --image arpadbotregistry.azurecr.io/arpadbot:latest \
  --cpu 1 --memory 1 \
  --environment-variables BOT_TOKEN="YOUR_TOKEN"
```

---

## Quick Reference

| Action | Command |
|--------|---------|
| View logs | `az webapp log tail --name arpadbot --resource-group ArpadBotRG` |
| Restart bot | `az webapp restart --name arpadbot --resource-group ArpadBotRG` |
| Check status | Visit `https://arpadbot.azurewebsites.net/api/health` |
| Update code | Push to GitHub (auto-deploys) |
| Access dashboard | `https://arpadbot.azurewebsites.net` |

---

## Support

- **Azure Docs**: [docs.microsoft.com/azure](https://docs.microsoft.com/azure)
- **Student Support**: [Azure for Students FAQ](https://azure.microsoft.com/en-us/free/students)
- **Bot Issues**: Check your GitHub repo issues

---

## Summary: Easiest Path

1. ✅ Go to [portal.azure.com](https://portal.azure.com)
2. ✅ Create Web App (Python 3.11, B1 tier)
3. ✅ Add `BOT_TOKEN` in Configuration
4. ✅ Connect GitHub in Deployment Center
5. ✅ Push code → Auto-deploys
6. ✅ Visit `https://YOUR-APP.azurewebsites.net` 🎉

**Total time: 10 minutes**
**Cost: $0 (covered by student credit)**

Enjoy your bot! 🤖
