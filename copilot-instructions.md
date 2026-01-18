# Copilot Instructions — ArpadDiscordBot

These instructions tell GitHub Copilot to keep runtime data stable across new chats and deployments, and to use the Azure setup below.

## Persistence Rules
- **DATA_DIR**: Always use a persistent directory for runtime files.
  - Default local: `data`
  - Azure App Service: `/home/site/data`
- **Database**: SQLite lives at `DATA_DIR/data.db` (see [db.py](db.py)). Do not move it into the repo tree.
- **Embeds**: Dashboard templates are stored at `DATA_DIR/embeds.json` (see [bot.py](bot.py)).
- **Config**: Prefer environment `CONFIG_JSON` for bot settings (token, `GUILD_ID`, feature flags). Treat [config.json](config.json) as example-only; do not overwrite on deploy.

## Azure Environment (Production)
- **Resource Group**: ArpadBotRG
- **App Service**: arpadbot (Linux)
- **App Service Plan**: ASP-ArpadBotRG-a6b3
- **Region**: Southeast Asia (app/plan), Japan East (RG meta)
- **Mount Path**: `/home/site/data` (persistent)
- **Required App Settings**:
  - `DATA_DIR=/home/site/data`
  - `CONFIG_JSON=<JSON with BOT_TOKEN, GUILD_ID, dashboards>`
  - Optionally: `PORT=8000` if needed

### Azure CLI Snippets
```bash
az webapp config appsettings set -g ArpadBotRG -n arpadbot --settings DATA_DIR=/home/site/data
az webapp config appsettings set -g ArpadBotRG -n arpadbot --settings CONFIG_JSON='{"BOT_TOKEN":"...","GUILD_ID":1234567890,"dashboard":{"enabled":true,"port":8000},"bot_api":{"enabled":true}}'
az webapp restart -g ArpadBotRG -n arpadbot
```

## Copilot Behavior
- **When committing/pushing**: Stage code changes only; never commit runtime files (`data.db`, `embeds.json`, `.env`, Azure credentials). Respect [.gitignore](.gitignore).
- **When asked to deploy**: Ensure `DATA_DIR` and `CONFIG_JSON` app settings are present; avoid writing secrets to files.
- **When reading/writing embeds**: Use `EMBEDS_PATH` in [bot.py](bot.py) which points to `DATA_DIR/embeds.json`.
- **When answering new chats**: Assume the above Azure environment and persistence settings unless the user states otherwise.

## Sensitive Files to Ignore
- `.env`, `.venv/`, `data/`, `*.db`, `config.json`, `embeds.json`
- Azure local artifacts: `.azure/`, `azure.env`, `azure-*.json`

## Quick Checks After Deploy
- SSH/Kudu: `ls -la /home/site/data` should show `data.db` and `embeds.json`.
- Discord: Trigger XP/birthday; verify state persists after redeploy.
