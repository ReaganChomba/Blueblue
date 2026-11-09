#!/usr/bin/env bash
# Legacy Blueblue by NevermoreSSH (2022); modernized for reaganchomba/blueblue.
set -Eeuo pipefail
echo 'Backups are private local files by default. Optional upload: BLUEBLUE_BACKUP_DEST=your-remote:path backup'
echo '1) Backup 2) Restore 0) Back'
read -rp 'Choice: ' choice
case "$choice" in 1) backup ;; 2) restore ;; 0) exit ;; esac
