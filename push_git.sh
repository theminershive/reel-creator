#!/bin/bash

# ==== USER CONFIG ====
REPO_NAME="reel-creator"  # <-- change to your GitHub repo name if different
TOKEN_FILE="token.txt"
USERNAME="theminershive"
LOCAL_DIR="./"

# ==== READ TOKEN ====
if [ ! -f "$TOKEN_FILE" ]; then
  echo "❌ Token file '$TOKEN_FILE' not found."
  exit 1
fi

TOKEN=$(<"$TOKEN_FILE")

# ==== INIT REPO ====
cd "$LOCAL_DIR" || { echo "❌ Directory '$LOCAL_DIR' not found."; exit 1; }

git init
git add .
git commit -m "Initial commit of Reel Creator App"
git branch -M main

# ==== SET REMOTE ====
REMOTE_URL="https://${USERNAME}:${TOKEN}@github.com/${USERNAME}/${REPO_NAME}.git"
git remote add origin "$REMOTE_URL"

# ==== PUSH ====
git push -u origin main

# ==== CLEANUP ====
git remote set-url origin "https://github.com/${USERNAME}/${REPO_NAME}.git"
echo "✅ Push complete. Remote URL cleaned up to hide token."
