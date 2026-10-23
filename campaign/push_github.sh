#!/usr/bin/env bash
# Create the private GitHub repository and push the campaign.
#
#   GITHUB_TOKEN=<fine-grained PAT with "repo" scope> bash campaign/push_github.sh
#
# The repository is created through the GitHub API (the SSH key can push, but it
# cannot create a repository), so a token is required.  The script is
# idempotent: it only creates the repository when it does not exist yet.
set -uo pipefail

ROOT=${PI05_30_ROOT:-/data/szgx/gaohang/pi05_30}
OWNER=${GITHUB_OWNER:-Herbert-Gao}
NAME=${GITHUB_REPO:-A800-1}
DESCRIPTION="pi0.5 / RoboTwin ALOHA (aloha-agilex) training campaign: source models, fine-tuning matrix, generalization evaluation and delivery docs"
TOKEN=${GITHUB_TOKEN:-${GH_TOKEN:-}}

if [[ -z "$TOKEN" ]]; then
  echo "no token: export GITHUB_TOKEN=<fine-grained PAT with repo scope> and run again" >&2
  exit 2
fi

api() {
  curl -sS -H "Authorization: Bearer $TOKEN" -H "Accept: application/vnd.github+json" \
       -H "X-GitHub-Api-Version: 2022-11-28" "$@"
}

echo "== checking whether $OWNER/$NAME exists"
STATUS=$(api -o /dev/null -w '%{http_code}' "https://api.github.com/repos/$OWNER/$NAME")
if [[ "$STATUS" == "404" ]]; then
  echo "== creating the private repository $OWNER/$NAME"
  api -X POST "https://api.github.com/user/repos" \
      -d "{\"name\":\"$NAME\",\"private\":true,\"description\":\"$DESCRIPTION\",\"auto_init\":false}" \
      -o /tmp/repo_create.json -w 'http %{http_code}\n'
  python3 - <<'PYEOF'
import json
try:
    payload = json.load(open("/tmp/repo_create.json"))
except Exception:
    payload = {}
print("   ->", payload.get("full_name") or payload.get("message") or payload.get("errors"))
PYEOF
else
  echo "   -> exists (http $STATUS)"
fi

cd "$ROOT"
git remote remove github 2>/dev/null
git remote add github "git@github.com:$OWNER/$NAME.git"
git config core.sshCommand "ssh -i /home/szgx/.ssh/gaohang-fanjie-4090 -o IdentitiesOnly=yes"
git branch -M main
git push -u github main 2>&1 | tail -3

# The first push went to the only empty public repository of the account; make
# it private (or remove it) so that nothing stays public.
if [[ "${CLEANUP_PUBLIC_COLAB:-1}" == "1" ]]; then
  echo "== the interim public repository $OWNER/Colab"
  STATUS=$(api -o /dev/null -w '%{http_code}' "https://api.github.com/repos/$OWNER/Colab")
  if [[ "$STATUS" == "200" ]]; then
    api -X PATCH "https://api.github.com/repos/$OWNER/Colab" -d '{"private":true}' \
        -o /dev/null -w '   -> set private: http %{http_code}\n'
  fi
fi
echo "== done: https://github.com/$OWNER/$NAME"
