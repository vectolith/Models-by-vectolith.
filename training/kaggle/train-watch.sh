#!/usr/bin/env bash
# train-watch.sh — keep the ASH PRIME / FYR PRIMA run from being lost.
#
# One kernel, one queue slot, both T4s: ASH PRIME (4B) trains on cuda:0 and
# FYR PRIMA (1.7B) on cuda:1, each in its own process, so the wall clock is the
# slower student instead of the sum.
#
#   vectolith/ash-prime-fyr-prima-multi-teacher-sft -> vectolith/ash-prime-fyr-prima-adapters
#
# QUEUED / RUNNING : nothing to do
# COMPLETE         : pull the output, publish adapters to the private dataset,
#                    commit them to the models repo, keep a local copy
# FAILED / ERROR   : salvage what survived, publish it, then re-push once with
#                    that dataset mounted so finished students are reused
#                    (max 3 re-pushes, then it reports instead of looping)
set -uo pipefail

SLUG=vectolith/ash-prime-fyr-prima-multi-teacher-sft
DATASET=vectolith/ash-prime-fyr-prima-adapters
LABEL=ash-prime-fyr-prima
OUTDIR=/home/sprite/work/out
LOG="$OUTDIR/train-watch.log"
REPO=/home/sprite/work/models
KDIR="$REPO/training/kaggle"
STATE="$OUTDIR/train-watch.state"
mkdir -p "$OUTDIR"
export KAGGLE_API_TOKEN="$(cat "$HOME/.kaggle/access_token")"
log() { echo "[$(date -Is)] $*" | tee -a "$LOG"; }

status=$(kaggle kernels status "$SLUG" 2>&1 | sed -nE 's/.*status "([^"]+)".*/\1/p' | sed 's/KernelWorkerStatus\.//')
[ -z "$status" ] && status=UNKNOWN
log "status=$status"

case "$status" in
  COMPLETE)
    log "run finished - mirroring artifacts"
    bash /home/sprite/work/mirror-run.sh "$SLUG" "$DATASET" "$LABEL"
    exit $?
    ;;
  QUEUED|RUNNING)
    exit 0
    ;;
esac

log "run ended as $status - salvaging"
attempts=$(cat "$STATE" 2>/dev/null || echo 0)
if [ "$attempts" -ge 3 ]; then
  log "already re-pushed $attempts times; leaving the salvage in place"
  exit 1
fi

salvage="$OUTDIR/salvage-$LABEL-$(date -u +%Y%m%d-%H%M)"
mkdir -p "$salvage"
if kaggle kernels output "$SLUG" -p "$salvage" >>"$LOG" 2>&1; then
  log "downloaded kernel output to $salvage"
else
  log "output not downloadable for a failed run; continuing with what is local"
fi

dsdir="$OUTDIR/dataset/$DATASET"
mkdir -p "$dsdir"
find "$salvage" -maxdepth 4 \( -name "*adapter*" -o -name "*manifest.json" -o -name "run-summary.json" \) -exec cp -r {} "$dsdir/" \; 2>/dev/null
if [ -n "$(ls -A "$dsdir" 2>/dev/null)" ]; then
  owner=$(echo "$DATASET" | cut -d/ -f1)
  dname=$(echo "$DATASET" | cut -d/ -f2)
  if kaggle datasets list --user "$owner" --page-size 100 2>/dev/null | grep -q "$dname"; then
    kaggle datasets version -p "$dsdir" -m "salvage $(date -u +%Y-%m-%dT%H:%MZ)" --dir-mode tar >>"$LOG" 2>&1 \
      && log "published salvage as a dataset version"
  else
    printf '{"title": "ASH PRIME + FYR PRIMA adapters", "id": "%s", "licenses": [{"name": "apache-2.0"}]}\n' "$DATASET" > "$dsdir/dataset-metadata.json"
    kaggle datasets create -p "$dsdir" --dir-mode tar >>"$LOG" 2>&1 && log "created adapters dataset from salvage"
  fi
else
  log "nothing worth publishing from the salvage"
fi

cd "$KDIR" || exit 1
if jq -e --arg ds "$DATASET" '.dataset_sources = (((.dataset_sources // []) + [$ds]) | unique | .[:5])' \
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
kaggle kernels push -p . >>"$LOG" 2>&1 \
  && log "re-pushed; the new version resumes finished students from mounted adapters" \
  || log "push failed"
