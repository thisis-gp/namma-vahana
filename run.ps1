param([string]$cmd = "all")
& .\.venv\Scripts\Activate.ps1
switch ($cmd) {
  "pipeline" { python -m src.run_pipeline }
  "db"       { python -m src.db_export }
  "backend"  { python -m backend.main }
  "api"      { python -m backend.main }
  "test"     { $env:PYTHONPATH = "."; pytest -q }
  default    { python -m src.run_pipeline }
}
