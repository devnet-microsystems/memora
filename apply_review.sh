#!/usr/bin/env bash
# Applies the Memora repository review to YOUR local clone, on a new branch (main is not touched).
# Usage: put memora-review.patch next to this script, then from the ROOT of your memora clone run:
#   bash apply_review.sh
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
git diff --quiet && git diff --cached --quiet || { echo "Commit or stash your local changes first."; exit 1; }
git checkout main && git pull --ff-only
git checkout -b claude/review-fixes
git apply --index --whitespace=nowarn "$HERE/memora-review.patch"
# files that must not be public (Strix reports contain a private key, logs, exploit PoCs, shadow modules, junk)
while IFS= read -r f; do git rm -q --ignore-unmatch -- "$f"; done <<'LIST'
.coverage
Archivio.zip
_tavily.py
backend.log
dashboard.log
dashboard/static/.!67792!apple-touch-icon.png
dashboard/static/.!67794!apple-touch-icon.png
fix_html.py
fix_html_xss.py
fix_inner.py
inject_xss.py
memora_fix_1.patch
mocks/dotenv.py
mocks/fastapi.py
mocks/openai.py
mocks/pydantic.py
mocks/tenacity.py
patch_xss.sh
poc_auth_bypass.py
poc_data_exposure.py
poc_data_exposure2.py
poc_data_exposure3.py
poc_injection.py
poc_prompt_injection.py
poc_ssrf.py
poc_ssrf2.py
poc_xss.py
rm_extract.py
scripts/start_backend.sh
seed.log
src/dotenv.py
src/openai.py
start_all.sh
strix-report-nvidiahackaton_4952.pdf
strix-report-nvidiahackaton_d618 (1).pdf
test_headers.py
test_prompt.py
LIST
python3 -m pytest -q 2>/dev/null | tail -1 || true
git commit -q -m "Review: fix update_node corruption, SOS/alerts flow, stats, dashboard JS syntax, proxy; new theme; repo cleanup"
echo "Done. Now run:  git push -u origin claude/review-fixes   and open the Pull Request on GitHub."
