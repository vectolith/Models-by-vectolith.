#!/usr/bin/env bash
# Pull a finished Kaggle run and persist the weights durably.
# Copies: (1) private Kaggle dataset, (2) private GitHub artifacts repo, (3) local zip.
# Usage: mirror-run.sh <kernel-slug> [dataset-slug] [label]
set -uo pipefail

SLUG="${1:-vectolith/ash-prime-sft-single-t4}"
DATASET="${2:-vectolith/ash-prime-adapters}"
LABEL="${3:-run}"
ARTREPO="vectolith/ash-prime-fyr-prima-artifacts"
export KAGGLE_API_TOKEN="$(cat $HOME/.kaggle/access_token)"
OUT="$HOME/work/out/kaggle-run-$LABEL"
BAD=0

echo "[1/5] downloading kernel output for ${LABEL}"
rm -rf "$OUT"; mkdir -p "$OUT"
kaggle kernels output "$SLUG" -p "$OUT" || echo "WARN: kernel output download failed"

echo "[2/5] results"
ls -la "$OUT" | head -20
if [ ! -f "$OUT/run-summary.json" ]; then
  echo "NO run-summary.json - run did not finish cleanly"
  BAD=1
fi

echo "[3/5] private kaggle dataset version"
DS="$HOME/work/out/dataset/$DATASET"
rm -rf "$HOME/work/out/dataset/$DATASET"; mkdir -p "$DS"
find "$OUT" -maxdepth 3 \( -name '*adapter*' -o -name '*.zip' -o -name 'run-summary.json' -o -name '*manifest.json' -o -name '*evaluation.json' -o -name '*sft.jsonl' -o -name '*.safetensors' -o -name '*metrics.json' \) -exec cp -r {} "$DS/" \; 2>/dev/null
ls -la "$DS" | head
if [ -n "$(ls -A "$DS" 2>/dev/null)" ]; then
  if kaggle datasets list --user "${DATASET%%/*}" --page-size 100 | grep -q "${DATASET##*/}"; then
    kaggle datasets version -p "$DS" -m "$LABEL run $(date -u +%Y-%m-%dT%H:%MZ)" --dir-mode tar || echo "WARN: dataset version failed"
  else
    printf '{"title": "%s adapters", "id": "%s", "licenses": [{"name": "apache-2.0"}]}\n' "$LABEL" "$DATASET" > "$DS/dataset-metadata.json"
    kaggle datasets create -p "$DS" --dir-mode tar || echo "WARN: dataset create failed"
  fi
else
  echo "nothing to publish for $LABEL"
fi

echo "[4/5] private github artifacts repo"
STAMP="$(date -u +%Y%m%d-%H%M)"
TMP="$(mktemp -d)"
if ! gh repo view "$ARTREPO" >/dev/null 2>&1; then
  gh repo create "$ARTREPO" --private --add-readme >/dev/null
fi
if git clone -q "https://github.com/$ARTREPO.git" "$TMP/art"; then
  DEST="$TMP/art/runs/$LABEL-$STAMP"
  mkdir -p "$DEST"
  find "$OUT" -maxdepth 3 \( -name '*adapter*' -o -name '*.zip' -o -name 'run-summary.json' -o -name '*manifest.json' -o -name '*evaluation.json' -o -name '*sft.jsonl' -o -name '*.safetensors' -o -name '*metrics.json' \) -exec cp -r {} "$DEST/" \; 2>/dev/null
  du -sh "$DEST"
  cd "$TMP/art" || exit 1
  git add -A
  git -c user.email=agent@olly.bot -c user.name=olly commit -q -m "artifacts: $LABEL kaggle run $STAMP" || echo "nothing new to commit"
  git push -q origin HEAD && echo "artifacts pushed to $ARTREPO" || echo "WARN: artifacts push failed"
else
  echo "WARN: could not clone $ARTREPO"
fi

echo "[5/5] local zip"
cd "$HOME/work/out" || exit 1
zip -qr "kaggle-$LABEL-$STAMP.zip" "kaggle-run-$LABEL" 2>/dev/null || true
ls -la $HOME/work/out/*.zip 2>/dev/null | tail -3
echo "DONE"
exit $BAD
