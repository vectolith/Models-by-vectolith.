#!/usr/bin/env bash
# train-watch.sh — keep the ASH PRIME / FYR PRIMA runs from being lost.
#
# Two kernels, one T4 each, one batch GPU session each (Kaggle's cap is 2).
#   vectolith/ash-prime-sft-single-t4  -> vectolith/ash-prime-adapters
#   vectolith/fyr-prima-sft-single-t4  -> vectolith/fyr-prima-adapters
#
# QUEUED / RUNNING : nothing to do
# COMPLETE         : pull the output, publish adapters to its Kaggle dataset,
#                    commit them to the models repo, keep a copy on this box
# FAILED / ERROR   : salvage whatever the run produced, publish it, then re-push
#                    that kernel with its adapters dataset mounted so the next
#                    attempt resumes instead of restarting (max 3 re-pushes)
set -uo pipefail

OUTDIR=/home/sprite/work/out
LOG="$OUTDIR/train-watch.log"
REPO=/home/sprite/work/models
mkdir -p "$OUTDIR"
export KAGGLE_API_TOKEN="$(cat "$HOME/.kaggle/access_token")"
log() { echo "[$(date -Is)] $*" | tee -a "$LOG"; }

watch_one() {
  local name="$1" dir="$2" slug="$3" dataset="$4"
  local state="$OUTDIR/train-watch.state.$name"
  local kdir="$REPO/training/kaggle/split/$dir"
  local status
  status=$(kaggle kernels status "$slug" 2>&1 | sed -nE 's/.*status "([^"]+)".*/\1/p' | sed 's/KernelWorkerStatus\.//')
  [ -z "$status" ] && status=UNKNOWN
  log "$name: status=$status"

  case "$status" in
    COMPLETE)
      log "$name: run finished - mirroring artifacts"
      bash /home/sprite/work/mirror-run.sh "$slug" "$dataset" "$name"
      return $?
      ;;
    QUEUED|RUNNING)
      return 0
      ;;
    *)
      log "$name: run ended as $status - salvaging"
      ;;
  esac

  local attempts
  attempts=$(cat "$state" 2>/dev/null || echo 0)
  if [ "$attempts" -ge 3 ]; then
    log "$name: already re-pushed $attempts times; leaving the salvage in place"
    return 1
  fi

  local salvage="$OUTDIR/salvage-$name-$(date -u +%Y%m%d-%H%M)"
  mkdir -p "$salvage"
  if kaggle kernels output "$slug" -p "$salvage" >>"$LOG" 2>&1; then
    log "$name: downloaded kernel output to $salvage"
  else
    log "$name: output not downloadable for a failed run; continuing with what is local"
  fi

  local dsdir="$OUTDIR/dataset/$dataset"
  mkdir -p "$dsdir"
  find "$salvage" -maxdepth 4 \( -name "*adapter*" -o -name "*manifest.json" -o -name "run-summary.json" \) -exec cp -r {} "$dsdir/" \; 2>/dev/null
  if [ -n "$(ls -A "$dsdir" 2>/dev/null)" ]; then
    local owner dname
    owner=$(echo "$dataset" | cut -d/ -f1)
    dname=$(echo "$dataset" | cut -d/ -f2)
    if kaggle datasets list --user "$owner" 2>/dev/null | grep -q "$dname"; then
      kaggle datasets version -p "$dsdir" -m "salvage $(date -u +%Y-%m-%dT%H:%MZ)" --dir-mode tar >>"$LOG" 2>&1 \
        && log "$name: published salvage as a dataset version"
    else
      printf '{"title": "%s adapters", "id": "%s", "licenses": [{"name": "apache-2.0"}]}\n' "$name" "$dataset" > "$dsdir/dataset-metadata.json"
      kaggle datasets create -p "$dsdir" --dir-mode tar >>"$LOG" 2>&1 && log "$name: created adapters dataset from salvage"
    fi
  else
    log "$name: nothing worth publishing from the salvage"
  fi

  cd "$kdir" || return 1
  if jq -e --arg ds "$dataset" '.dataset_sources = (((.dataset_sources // []) + [$ds]) | unique)' \
        kernel-metadata.json > kernel-metadata.json.tmp 2>>"$LOG"; then
    mv kernel-metadata.json.tmp kernel-metadata.json
    log "$name: dataset sources: $(jq -c '.dataset_sources' kernel-metadata.json)"
  else
    log "$name: could not add the resume dataset to the metadata"
    rm -f kernel-metadata.json.tmp
    return 1
  fi

  echo $((attempts + 1)) > "$state"
  log "$name: re-pushing kernel (attempt $((attempts + 1)) of 3) with the resume dataset mounted"
  kaggle kernels push -p . >>"$LOG" 2>&1 \
    && log "$name: re-pushed; the new version resumes from mounted adapters" \
    || log "$name: push failed"
}

rc=0
for run in \
  "ash-prime|ash-prime|vectolith/ash-prime-sft-single-t4|vectolith/ash-prime-adapters" \
  "fyr-prima|fyr-prima|vectolith/fyr-prima-sft-single-t4|vectolith/fyr-prima-adapters"
do
  IFS='|' read -r name dir slug dataset <<<"$run"
  watch_one "$name" "$dir" "$slug" "$dataset" || rc=1
done
exit $rc
