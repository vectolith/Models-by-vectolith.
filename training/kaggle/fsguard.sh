#!/usr/bin/env bash
# fsguard.sh — detect the box's NBD/EXT4 read-only event.
# The host detaches the network block device backing / under load; EXT4 then
# remounts read-only and loses async page writes (that is what zeroed
# node_modules). This cannot stop the host, but it detects the damage so a
# build never "passes" on half-written files.
set -uo pipefail

PROBE=/home/sprite/.fsguard-probe
stamp=""

if ! printf 'probe %s\n' "$(date -Is)" > "$PROBE" 2>/dev/null; then
  echo "FSGUARD: root filesystem is NOT writable (read-only remount)."
  dmesg 2>/dev/null | grep -iE 'EXT4-fs.*(read-only|I/O error)|nbd.*disconnect' | tail -5
  exit 2
fi
stamp=$(cat "$PROBE" 2>/dev/null)
rm -f "$PROBE"
case "$stamp" in
  probe*) : ;;
  *) echo "FSGUARD: write did not read back intact"; exit 3 ;;
esac

hits=$(dmesg 2>/dev/null | grep -ciE 'EXT4-fs.*Remounting filesystem read-only|I/O error while writing superblock')
if [ "$hits" -gt 0 ]; then
  echo "FSGUARD: $hits prior EXT4 read-only/I-O event(s) this boot"
  dmesg 2>/dev/null | grep -iE 'EXT4-fs.*read-only|I/O error while writing superblock|orphan inodes deleted|recovery complete' | tail -6
fi

avail=$(df -Pk /home/sprite | awk 'NR==2{print $4}')
rc=0
if [ "$avail" -lt 2097152 ]; then
  echo "FSGUARD: WARNING under 2 GB free ($((avail/1024)) MB)"
  rc=1
fi
echo "FSGUARD: writable=yes prior_events=$hits free_mb=$((avail/1024))"
exit $rc
