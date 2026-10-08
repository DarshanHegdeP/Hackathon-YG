import sys
import uvicorn

# Ensure utf-8 encoding on Windows console
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

if __name__ == "__main__":
    print("=" * 65)
    print("[*] Starting PERSON 4 Case & Workflow Orchestrator")
    print("    Intake Endpoint: POST /api/webhook/person3")
    print("    Interactive Dashboard: http://localhost:8000")
    print("    Swagger OpenAPI Docs:  http://localhost:8000/docs")
    print("=" * 65)
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
