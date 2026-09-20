"""
Sync and deploy the latest codebase to Hugging Face Spaces.
Usage: python scripts/deploy_to_hf.py
"""

import os
from dotenv import load_dotenv
from huggingface_hub import HfApi

# Load environment variables
load_dotenv()
TOKEN = os.getenv("HF_TOKEN")
REPO_ID = "Bixale55/ResuMate"

if not TOKEN:
    raise ValueError("HF_TOKEN not found in environment or .env file.")

print(f"Deploying latest code to https://huggingface.co/spaces/{REPO_ID}...")
api = HfApi(token=TOKEN)

commit_info = api.upload_folder(
    folder_path=".",
    repo_id=REPO_ID,
    repo_type="space",
    commit_message="Deploy latest updates to Hugging Face Space",
    ignore_patterns=[
        ".git*",
        ".env*",
        "venv*",
        "data*",
        "uploads*",
        "exports*",
        "scripts*",
        "__pycache__*",
        "*.pyc",
    ],
)

print("Deploy successful!")
print(f"Space: https://huggingface.co/spaces/{REPO_ID}")
print("Live App: https://bixale55-resumate.hf.space")
