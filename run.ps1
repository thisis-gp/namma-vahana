param([string]$cmd = "all")
& .\.venv\Scripts\Activate.ps1
switch ($cmd) {
  "pipeline" { python -m src.run_pipeline }
  "app"      { streamlit run app/Home.py }
  "test"     { pytest -q }
  default    { python -m src.run_pipeline; streamlit run app/Home.py }
}
