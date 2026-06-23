# Deploy database (not committed — regenerate from pipeline artifacts)

```powershell
.\run.ps1 pipeline   # if artifacts/ missing
.\run.ps1 db         # writes data/parkpulse.db locally
Copy-Item data\parkpulse.db backend\deploy\parkpulse.db
```

On Render, `render.yaml` runs `python -m src.db_export` at build time from committed `artifacts/`.
