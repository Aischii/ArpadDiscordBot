# ArpadBot Azure Deployment Troubleshooting & Setup

## Issue: Bot not running on Azure

If your bot isn't running on Azure, follow these steps:

### Step 1: Check Azure App Settings

Go to **Azure Portal** → **Your Web App** → **Configuration**

Verify these environment variables are set:
```
BOT_TOKEN = YOUR_DISCORD_BOT_TOKEN_HERE
PYTHONUNBUFFERED = 1
SCM_DO_BUILD_DURING_DEPLOYMENT = true
PORT = 8000
```

### Step 2: Set Startup Command

1. In **Configuration**, scroll to **General Settings**
2. Set **Startup Command** to one of these:

**Option A (Recommended - Uses bash script):**
```
bash startup.sh
```

**Option B (Direct Python):**
```
python3 bot.py
```

### Step 3: Enable Logs

1. Go to **App Service Logs** (in left menu under Monitoring)
2. Enable:
   - **Application Logging** (File System) - set to Debug
   - **Web Server Logging** - WAWS
3. Click **Save**

### Step 4: View Logs

1. Click **Log Stream** (in left menu)
2. Watch for any errors
3. You should see:
```
Server started on port 8000 (Dashboard + Bot API combined)
Logged in as ArpadBot#1234
```

### Step 5: Restart Web App

1. Click **Restart** button in the top menu
2. Wait 30-60 seconds
3. Check the log stream again

### Step 6: Access Dashboard

Once running, visit:
```
https://arpadbot-hpcbhwggb5bhc0h8.southeastasia-01.azurewebsites.net
```

You should see the ArpadBot Dashboard.

### Troubleshooting

**Problem: "ModuleNotFoundError"**
- Make sure `requirements.txt` is in the repo root
- Delete the deployment and redeploy

**Problem: "BOT_TOKEN not found"**
- Check Azure Configuration → Application Settings
- The BOT_TOKEN must be set there (not in config.json)
- Restart the app after setting it

**Problem: "Port already in use"**
- Azure provides port 8000 automatically
- Make sure config.json has `"port": 8000`

**Problem: Dashboard loads but bot shows offline**
- Check if BOT_TOKEN is correct in Azure settings
- Check Discord Developers portal - token must be valid
- Check the Log Stream for connection errors

### Config for Azure

Your `config.json` is already updated with:
- Dashboard on port 8000
- Bot API on port 8000
- Bot API URL pointing to your Azure domain

The domain is: `https://arpadbot-hpcbhwggb5bhc0h8.southeastasia-01.azurewebsites.net`

### Next Steps

1. Go to Azure Portal
2. Set BOT_TOKEN in Configuration → Application Settings
3. Set Startup Command to: `bash startup.sh`
4. Click Restart
5. Monitor Log Stream for 1-2 minutes
6. Visit your domain to access the dashboard

If still not working, check the Log Stream for specific error messages and let us know!
