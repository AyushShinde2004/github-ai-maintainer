import os
import shutil
import random
import time
from git import Repo
from dotenv import load_dotenv
from google import genai
from google.genai import errors as genai_errors
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

    def generate_with_retry(prompt_text, max_attempts=5):
        """
        Calls Gemini with exponential backoff + jitter.
        Handles transient 503/UNAVAILABLE and 429/rate-limit errors,
        which are Google's servers being busy, not a bug in our code.
        """
        for attempt in range(1, max_attempts + 1):
            try:
                return client.models.generate_content(
                    model="gemini-flash-latest",
                    contents=prompt_text
                )
            except genai_errors.ServerError as e:
                # 503 UNAVAILABLE, 500, etc. — worth retrying.
                if attempt == max_attempts:
                    raise
                wait = (2 ** attempt) + random.uniform(0, 1)
                print(f"Gemini server error (attempt {attempt}/{max_attempts}): {e}")
                print(f"Retrying in {wait:.1f}s...")
                time.sleep(wait)
            except genai_errors.ClientError as e:
                # 429 rate limit is retryable; other 4xx errors (bad key,
                # bad request) are not — no point retrying those.
                if "429" in str(e) and attempt < max_attempts:
                    wait = (2 ** attempt) + random.uniform(0, 1)
                    print(f"Rate limited (attempt {attempt}/{max_attempts}). Retrying in {wait:.1f}s...")
                    time.sleep(wait)
                else:
                    raise
        return None

    try:
        response = generate_with_retry(prompt)
    except (genai_errors.ServerError, genai_errors.ClientError) as e:
        # Gemini is still down after all retries. This is not our bug —
        # exit quietly (code 0) so the Action doesn't show as a failed run
        # every time Google has a rough day. Tomorrow's scheduled run
        # will just try again.
        print(f"Gemini unavailable after retries, skipping this run: {e}")
        sys.exit(0)

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