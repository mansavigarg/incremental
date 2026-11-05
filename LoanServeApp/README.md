# LoanServe application

This folder is a standalone runnable application. The Streamlit UI calls the same FastAPI service exposed in Swagger. It includes the trained classifier and risk model, the policy vector index, the local embedding model, and the cleaned application book required by the assistant. No training data or test suite is needed to run it.

For a fresh install beside the original project, place `setup_loanserve.py` and `LoanServeApp.zip` together, change into the destination directory, and run `python3 /path/to/setup_loanserve.py`. It downloads the v1.0.3 release into `Project/` only if that folder does not already exist, and extracts this app into `LoanServeApp/` only if absent. Existing folders are left untouched.

## Install and run

Python 3.11+ is required. From this folder, install packages into your normal user Python site (no virtual environment):

```bash
chmod +x install.sh start.sh
./install.sh
# Fill GEMINI_API_KEY and GEMINI_MODEL in .env. The installer generates the JWT secret.
./start.sh
```

The installer uses the PyTorch CPU wheel index: `https://download.pytorch.org/whl/cpu`. It uses `pip --user --break-system-packages` because system Python on some Linux distributions blocks user-site installs otherwise.

- Streamlit: http://127.0.0.1:8501
- Swagger: http://127.0.0.1:8000/docs
- Health: http://127.0.0.1:8000/health

Create an account in the UI or through `POST /api/v1/auth/signup`, then sign in. The first account becomes an administrator; later public signups become loan officers. An administrator can create another administrator after signing in. Accounts and application records persist in SQLite. The assistant and policy answer call Gemini; policy search runs locally. If Gemini credentials are absent, the API and local retrieval still run, while live answers return a clear error.

The API server must stay running while using Streamlit. `start.sh` starts both and stops the API when Streamlit exits.
