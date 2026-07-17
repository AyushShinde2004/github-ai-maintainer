import os
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
# Clone or update repository
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
# README
# ----------------------------
readme_path = os.path.join(local_folder, "README.md")

if os.path.exists(readme_path):

    with open(readme_path, "r", encoding="utf-8") as f:
        readme = f.read()

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

    PRIMARY_MODEL = "gemini-2.5-flash"
    FALLBACK_MODEL = "gemini-2.5-flash-lite"

    def is_retryable(exc):
        """Returns True if the exception is a temporary server/load issue."""
        if isinstance(exc, genai_errors.ServerError):
            return True

        if isinstance(exc, genai_errors.ClientError):
            msg = str(exc)
            return "429" in msg

        return False

    def try_model(model_name, prompt_text):
        print(f"Trying {model_name}...")

        return client.models.generate_content(
            model=model_name,
            contents=prompt_text
        )

    def generate_with_retry(prompt_text, retries=4):

        # ----------------------------
        # First attempt:
        # Flash -> Flash Lite
        # ----------------------------
        for model in (PRIMARY_MODEL, FALLBACK_MODEL):
            try:
                response = try_model(model, prompt_text)
                print(f"Success with {model}")
                return response

            except Exception as e:
                if is_retryable(e):
                    print(f"{model} temporarily unavailable.")
                else:
                    raise

        # ----------------------------
        # Retry loop with exponential backoff
        # ----------------------------
        for attempt in range(1, retries + 1):

            wait = (2 ** attempt) + random.uniform(0, 1)

            print(
                f"\nRetry round {attempt}/{retries} "
                f"(waiting {wait:.1f}s)..."
            )

            time.sleep(wait)

            for model in (PRIMARY_MODEL, FALLBACK_MODEL):

                try:
                    response = try_model(model, prompt_text)
                    print(f"Recovered using {model}")
                    return response

                except Exception as e:

                    if is_retryable(e):
                        print(f"{model} still unavailable.")
                        continue

                    raise

        raise RuntimeError(
            "All Gemini models were unavailable after retries."
        )

    try:
        response = generate_with_retry(prompt)

    except Exception as e:
        print(f"\nSkipping today's run.")
        print(e)
        sys.exit(0)

    new_readme = response.text

    if new_readme.strip() == readme.strip():
        print("No changes suggested.")
        sys.exit(0)

    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(new_readme)

    print("README updated.")

    repo.git.add("README.md")

    if not repo.is_dirty():
        print("Repository has no changes.")
        sys.exit(0)

    print("Repository changed.")

    message = f"docs: improve README ({datetime.now().strftime('%Y-%m-%d')})"

    repo.config_writer().set_value(
        "user", "name", "github-actions[bot]"
    ).release()

    repo.config_writer().set_value(
        "user",
        "email",
        "41898282+github-actions[bot]@users.noreply.github.com"
    ).release()

    repo.index.commit(message)

    print("Commit created.")

    print("Pushing changes...")
    origin = repo.remote(name="origin")
    origin.push()

    print("Done!")

else:
    print("README.md not found.")
