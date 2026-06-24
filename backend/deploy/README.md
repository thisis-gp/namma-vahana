# Deploy database

`backend/deploy/parkpulse.db` is committed so Render always ships analytics data.

Regenerate locally:

```powershell
.\run.ps1 pipeline   # if artifacts/ missing
.\run.ps1 db         # writes data/parkpulse.db
Copy-Item data\parkpulse.db backend\deploy\parkpulse.db -Force
git add backend/deploy/parkpulse.db
```

Render also runs `python -m src.db_export` at build time and hydrates on startup if empty.
