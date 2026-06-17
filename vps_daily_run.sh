#!/bin/bash
# Daily job search — runs on VPS, pushes results to GitHub Pages
# Cron: 13 08 * * 1-5   (8:13 AM ET = 15:13 UTC, Mon-Fri)
# Install: crontab -e

set -e
cd /opt/job_search_bot/repo

git pull --ff-only origin main 2>/dev/null || git pull --ff-only origin master 2>/dev/null || true

USE_RSS=true python3 daily_run.py 2>&1 | tee /opt/job_search_bot/logs/daily_run.log

git config user.name  "vps-cron"
git config user.email "vps@job-search-bot"
git add data/jobs.json
git diff --staged --quiet || git commit -m "Daily search $(date -u '+%Y-%m-%d')"
git push origin HEAD:main 2>/dev/null || git push origin HEAD:master 2>/dev/null
