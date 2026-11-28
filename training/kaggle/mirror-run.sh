#!/usr/bin/env bash
# Pull a finished Kaggle run and persist the weights durably.
# Copies: (1) private Kaggle dataset, (2) private GitHub artifacts repo, (3) local zip.
# Usage: mirror-run.sh <kernel-slug> [dataset-slug] [artifacts-repo]
set -euo pipefail

SLUG="${1:-vectolith/ash-prime-fyr-prima-multi-teacher-sft}"
DATASET="${2:-vectolith/ash-prime-fyr-prima-adapters}"
ARTREPO="${3:-vectolith/ash-prime-fyr-prima-artifacts}"
export KAGGLE_API_TOKEN="$(cat $HOME/.kaggle/access_token)"
OUT="$HOME/work/out/kaggle-run"
rm -rf "$OUT"; mkdir -p "$OUT"

echo "[1/5] downloading kernel output"
kaggle kernels output "$SLUG" -p "$OUT"

echo "[2/5] results"
ls -la "$OUT" | head -20
test -f "$OUT/run-summary.json" || { echo "NO run-summary.json - run did not finish"; exit 2; }

FIND_EXPR='( -name *adapter* -o -name *.zip -o -name run-summary.json -o -name *manifest.json -o -name *evaluation.json -o -name *sft.jsonl -o -name *.safetensors -o -name *metrics.json )'

echo "[3/5] private kaggle dataset version"
DS="$HOME/work/out/dataset/$DATASET"
rm -rf "$HOME/work/out/dataset"; mkdir -p "$DS"
find "$OUT" -maxdepth 3 \( -name '*adapter*' -o -name '*.zip' -o -name 'run-summary.json' -o -name '*manifest.json' -o -name '*evaluation.json' -o -name '*sft.jsonl' -o -name '*.safetensors' -o -name '*metrics.json' \) -exec cp -r {} "$DS/" \;
ls -la "$DS" | head
if kaggle datasets list --user "${DATASET%%/*}" --page-size 100 | grep -q "${DATASET##*/}"; then
  kaggle datasets version -p "$DS" -m "run $(date -u +%Y-%m-%dT%H:%MZ)" --dir-mode tar
else
  printf '{"title": "ASH PRIME + FYR PRIMA adapters", "id": "%s", "licenses": [{"name": "apache-2.0"}]}\n' "$DATASET" > "$DS/dataset-metadata.json"
  kaggle datasets create -p "$DS" --dir-mode tar
fi

echo "[4/5] private github artifacts repo"
STAMP="$(date -u +%Y%m%d-%H%M)"
TMP="$(mktemp -d)"
if ! gh repo view "$ARTREPO" >/dev/null 2>&1; then
  gh repo create "$ARTREPO" --private --add-readme >/dev/null
fi
git clone -q "https://github.com/$ARTREPO.git" "$TMP/art"
DEST="$TMP/art/runs/kaggle-$STAMP"
mkdir -p "$DEST"
find "$OUT" -maxdepth 3 \( -name '*adapter*' -o -name '*.zip' -o -name 'run-summary.json' -o -name '*manifest.json' -o -name '*evaluation.json' -o -name '*sft.jsonl' -o -name '*.safetensors' -o -name '*metrics.json' \) -exec cp -r {} "$DEST/" \;
du -sh "$DEST"
cd "$TMP/art"
git add -A
git -c user.email=agent@olly.bot -c user.name=olly commit -q -m "artifacts: kaggle run $STAMP" || echo "nothing new to commit"
git push -q origin HEAD && echo "artifacts pushed to $ARTREPO"

echo "[5/5] local zip"
cd "$HOME/work/out"
zip -qr "kaggle-run-$STAMP.zip" kaggle-run 2>/dev/null || true
ls -la "$HOME/work/out"/*.zip 2>/dev/null | head -2
echo "DONE"
