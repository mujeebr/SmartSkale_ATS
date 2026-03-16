# Remove OpenAI API key from git history

Your **OpenAI API key was committed** in earlier commits. GitHub may block pushes when it detects secrets. Follow these steps to remove the key from **all** history and push safely.

---

## 1. Rotate your API key (do this first)

The old key is exposed, so treat it as compromised.

1. Go to [OpenAI API keys](https://platform.openai.com/api-keys).
2. **Revoke** the key that was in the repo.
3. **Create a new key** and save it somewhere safe.
4. Update:
   - Your local `.env`
   - GitHub Actions secret **`OPENAI_API_KEY`**
   - EC2 (when you run `docker run`, use the new key)

---

## 2. Install git-filter-repo

On your Mac:

```bash
# Option A (Homebrew)
brew install git-filter-repo

# Option B (pip)
pip install git-filter-repo
```

---

## 3. Create a replace-text file (do not commit it)

From your repo root:

```bash
cd /Users/mac/Downloads/assignment
```

Create a file named `expressions.txt` in the repo with **exactly** this line (replaces any OpenAI-style key in history with a placeholder):

```
regex:sk-proj-[A-Za-z0-9_-]{20,}==>sk-REPLACE_WITH_YOUR_OPENAI_API_KEY
```

If your key had a different prefix (e.g. plain `sk-`), use this broader pattern instead:

```
regex:sk-[A-Za-z0-9_-]{20,}==>sk-REPLACE_WITH_YOUR_OPENAI_API_KEY
```

`expressions.txt` is in `.gitignore` so it will not be committed.

---

## 4. Rewrite history

**Warning:** This rewrites all commits. If you already have a shared remote, you will need to force-push (see step 5).

```bash
cd /Users/mac/Downloads/assignment
git filter-repo --replace-text expressions.txt --force
```

`git filter-repo` removes all remotes. That is normal.

---

## 5. Re-add remote and force-push

Replace `YOUR_GITHUB_REPO_URL` with your repo URL (e.g. `https://github.com/username/assignment.git`):

```bash
git remote add origin YOUR_GITHUB_REPO_URL
git push -u origin main --force
```

If your default branch is `master`:

```bash
git push -u origin master --force
```

---

## 6. Clean up

```bash
rm expressions.txt
```

You can delete `SECRETS_REMOVAL.md` after you are done, or keep it for reference.

---

## If you prefer not to use git-filter-repo

**Option B – New repo without history (simplest, but you lose commit history):**

1. Rotate the API key (step 1 above).
2. Copy your project to a new folder; delete the `.git` directory inside it.
3. Run `git init`, add remote, commit everything, and push to a **new** GitHub repo (or orphan branch).
4. Use that new repo / branch as the source of truth from now on.

This avoids rewriting history but discards the old commits.
