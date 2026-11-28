#!/usr/bin/env bash
# train-watch.sh — keep the ASH PRIME / FYR PRIMA run from being lost.
#
# QUEUED / RUNNING : nothing to do
# COMPLETE         : pull the output, publish adapters to the Kaggle dataset,
#                    commit them to the models repo, keep a copy on this box
# FAILED / ERROR   : salvage whatever the run produced, publish it, then re-push
#                    the kernel with the adapters dataset mounted so the next
#                    attempt resumes instead of restarting (max 3 re-pushes)
set -uo pipefail

SLUG=vectolith/ash-prime-fyr-prima-multi-teacher-sft
DATASET=vectolith/ash-prime-fyr-prima-adapters
if [ "$#" -gt 0 ]; then SLUG="$1"; fi
if [ "$#" -gt 1 ]; then DATASET="$2"; fi
OWNER=$(echo "$DATASET" | cut -d/ -f1)
DNAME=$(echo "$DATASET" | cut -d/ -f2)

REPO=/home/sprite/work/models
KAGGLE_DIR="$REPO/training/kaggle"
OUTDIR=/home/sprite/work/out
STATE="$OUTDIR/train-watch.state"
LOG="$OUTDIR/train-watch.log"
mkdir -p "$OUTDIR"
export KAGGLE_API_TOKEN="$(cat "$HOME/.kaggle/access_token")"
log() { echo "[$(date -Is)] $*" | tee -a "$LOG"; }

status=$(kaggle kernels status "$SLUG" 2>&1 | sed -nE 's/.*status "([^"]+)".*/\1/p' | sed 's/KernelWorkerStatus\.//')
if [ -z "$status" ]; then status=UNKNOWN; fi
log "status=$status"

case "$status" in
  COMPLETE)
    log "run finished - mirroring artifacts"
    bash /home/sprite/work/mirror-run.sh "$SLUG" "$DATASET"
    exit $?
    ;;
  QUEUED|RUNNING)
    exit 0
    ;;
  *)
    log "run ended as $status - salvaging"
    ;;
esac

attempts=$(cat "$STATE" 2>/dev/null || echo 0)
if [ "$attempts" -ge 3 ]; then
  log "already re-pushed $attempts times; stopping and leaving the salvage in place"
  exit 1
fi

SALVAGE="$OUTDIR/salvage-$(date -u +%Y%m%d-%H%M)"
mkdir -p "$SALVAGE"
if kaggle kernels output "$SLUG" -p "$SALVAGE" >>"$LOG" 2>&1; then
  log "downloaded kernel output to $SALVAGE"
else
  log "kernel output not downloadable for a failed run; continuing with what is local"
fi

DSDIR="$OUTDIR/dataset/$DATASET"
mkdir -p "$DSDIR"
find "$SALVAGE" -maxdepth 4 \( -name '*adapter*' -o -name '*manifest.json' -o -name 'run-summary.json' \) -exec cp -r {} "$DSDIR/" \; 2>/dev/null
if [ -n "$(ls -A "$DSDIR" 2>/dev/null)" ]; then
  if kaggle datasets list --user "$OWNER" 2>/dev/null | grep -q "$DNAME"; then
    kaggle datasets version -p "$DSDIR" -m "salvage $(date -u +%Y-%m-%dT%H:%MZ)" --dir-mode tar >>"$LOG" 2>&1 \
      && log "published salvage as a dataset version"
  else
    printf '{"title": "ASH PRIME + FYR PRIMA adapters", "id": "%s", "licenses": [{"name": "apache-2.0"}]}\n' "$DATASET" > "$DSDIR/dataset-metadata.json"
    kaggle datasets create -p "$DSDIR" --dir-mode tar >>"$LOG" 2>&1 && log "created adapters dataset from salvage"
  fi
else
  log "nothing worth publishing from the salvage"
fi

cd "$KAGGLE_DIR" || exit 1
if jq -e --arg ds "$DATASET" '.dataset_sources = (((.dataset_sources // []) + [$ds]) | unique)' \
      kernel-metadata.json > kernel-metadata.json.tmp 2>>"$LOG"; then
  mv kernel-metadata.json.tmp kernel-metadata.json
  log "dataset sources: $(jq -c '.dataset_sources' kernel-metadata.json)"
else
  log "could not add the resume dataset to the metadata"
  rm -f kernel-metadata.json.tmp
  exit 1
fi

echo $((attempts + 1)) > "$STATE"
log "re-pushing kernel (attempt $((attempts + 1)) of 3) with the resume dataset mounted"
kaggle kernels push -p . >>"$LOG" 2>&1 && log "re-pushed; the new version resumes from mounted adapters" || log "push failed"
