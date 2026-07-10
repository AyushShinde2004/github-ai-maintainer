import os
import shutil
import random
from git import Repo
from dotenv import load_dotenv
from google import genai
from datetime import datetime
import sys

load_dotenv()

client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)

# ----------------------------
# GitHub Username
# ----------------------------
USERNAME = "AyushShinde2004"

# ----------------------------
# Your repositories
# ----------------------------
repos = [
    "soft-moment-creator",
    "AWS-Resource-Monitor",
    "Health_loss_detection_system"
]

# ----------------------------
# Pick one randomly
# ----------------------------
repo_name = random.choice(repos)

print(f"Today's repository: {repo_name}")

github_token = os.getenv("GITHUB_TOKEN")

repo_url = (
    f"https://x-access-token:{github_token}"
    f"@github.com/{USERNAME}/{repo_name}.git"
)

local_folder = f"repos/{repo_name}"

# ----------------------------
# Delete old repo if exists
# ----------------------------
if not os.path.exists(local_folder):
    print("Cloning repository...")
    repo = Repo.clone_from(repo_url, local_folder)
else:
    print("Repository already exists.")
    repo = Repo(local_folder)

    print("Pulling latest changes...")
    repo.remotes.origin.pull()

# ----------------------------
# Read README
# ----------------------------
readme_path = os.path.join(local_folder, "README.md")

if os.path.exists(readme_path):

    with open(readme_path, "r", encoding="utf-8") as f:
        readme = f.read()

    print("\n========== README ==========\n")
    print("README loaded successfully.")

    prompt = f"""
    You are an expert GitHub maintainer.

    Your task is to make ONE tiny improvement to this README.

    Rules:

    - Maximum 5 changed lines.
    - Never invent new features.
    - Never remove existing information.
    - Improve only grammar, wording, formatting or clarity.
    - Preserve Markdown.
    - Return ONLY the complete updated README.

    README:

    {readme}
    """

    response = client.models.generate_content(
        model="gemini-flash-latest",
        contents=prompt
    )

    new_readme = response.text

    if new_readme.strip() == readme.strip():
        print("No changes suggested.")
        sys.exit()

    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(new_readme)

    print("README updated.")

    repo.git.add("README.md")

    if not repo.is_dirty():
        print("Repository has no changes.")
        sys.exit()

    print("Repository changed.")

    message = f"docs: improve README ({datetime.now().strftime('%Y-%m-%d')})"

    repo.config_writer().set_value(
        "user", "name", "github-actions[bot]"
    ).release()

    repo.config_writer().set_value(
        "user", "email", "41898282+github-actions[bot]@users.noreply.github.com"
    ).release()

    repo.index.commit(message)

    print("Commit created.")

    print("Pushing changes...")
    origin = repo.remote(name="origin")
    origin.push()
    print("Done!")

else:
    print("README.md not found.")
