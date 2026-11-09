# Operations and recovery

No commands in this document were executed against a VPS during development. No tests or installation runs were performed. Runtime configuration checks are implemented in the installers/account transactions to fail before applying an invalid configuration when an operator later executes them.

## Upgrade sequence and backups

`upgrade-existing.sh` resolves a complete source bundle if necessary, then `lib/upgrade.sh`:

1. Checks the OS/systemd and reads the effective Xray unit. Multi-file layouts are refused.
2. Acquires the account-management lock. Captures the current binary, configurations, installed commands, managed unit files, cron data, Stunnel config and service state in a timestamped snapshot.
3. Parses legacy commented JSON without executing it. Imports known account/expiry markers, preserving protocol credentials. Conflicting UUIDs/passwords for the same named identity cause a refusal.
4. Selects one HTTPS server from Nginx's actual include graph. Reads its existing certificate/key paths and creates a loopback XHTTP inbound plus a managed HTTP/2 location. Existing WS/gRPC routes and fallback content are retained.
5. Retrieves an official architecture-specific stable Xray release and verifies its published checksum. Installs/upgrades the managed distribution packages with existing package configuration retained. No unrelated package is purged. Shared command wrappers are installed before staging the merge so newly invoked account/expiry commands wait on the migration lock.
6. Checks the staged core against the merged config and Nginx configuration. Replaces the core atomically, preserving the installed service definition.
7. Stops the Blueblue Stunnel/bridge instances, stages their modern replacements, then restarts Xray, reloads Nginx and starts Stunnel/bridge. It does not restart OpenSSH or replace its configuration.
8. Enables one expiry timer and one certificate-change watcher. A detected bundled UDPGW installation is replaced by a source-built compatibility instance.

Source/release staging directories are retained. The live upgrade adds only XHTTP to Nginx by default. HTTPUpgrade and separate RAW/mKCP listeners require explicit actions. The upgrade does not run certificate renewal, modify private-key bytes, change ACME accounts, replace renew jobs or reinstall Nginx from a different source.

Snapshots are private and contain sensitive credentials. Copy them off-host over an authenticated channel. Package upgrades, service-account creation, source-build packages and certificate ACL additions are not reversed by a file rollback. No blanket apt downgrade is attempted.

## File rollback

On an upgrade error, the script attempts automatic file rollback and restarts/reloads original service configurations. It reports the backup directory. A failure to restore a running service still requires operator intervention.

To perform a deliberate rollback later, use the retained modern source bundle (not a script that might disappear during restoration):

```bash
sudo systemctl stop blueblue-expiry.timer blueblue-cert-watch.path
sudo systemctl stop stunnel5 ws-stunnel
sudo systemctl stop blueblue-udpgw@7100 blueblue-udpgw@7200 blueblue-udpgw@7300
sudo python3 /path/to/blueblue/lib/snapshot.py restore /var/backups/blueblue/TIMESTAMP-PID
sudo systemctl daemon-reload
```

The root-created archive restores original ownership/modes/symlinks and removes only entries created by the upgrade under the saved paths. It preserves saved service directories instead of deleting and regenerating them. Review `probe.json` for the original Xray service and paths; review `*.active`/`*.enabled` state files before restoring service state. Then, in your maintenance window:

```bash
sudo systemctl restart xray.service
sudo systemctl reload nginx
sudo systemctl start stunnel5 ws-stunnel
```

Use the original service name when customized. Restart timers only if they existed and were enabled before the upgrade. Restoring the old bridge/Stunnel files can restore the original incompatibility; the archive is a recovery point, not a promise that the old software works on a newer OS. For original screen-based UDPGW sessions, the restored `/etc/rc.local` contains the original startup commands; start only the needed legacy instances manually.

The snapshot records existing POSIX ACLs and file capabilities for restoration. New ACL grants on paths outside the snapshot remain additive read/traverse permissions to the service users. If reverting to software that does not need them, remove the specific `stunnel4`/Xray-user ACL entries using `setfacl -x u:USERNAME PATH`; do not reset all ACLs or change a working private key to mode 0644. Package versions can be recovered only using the distribution's package-management/recovery process and a separate machine snapshot.

## Domain and certificate workflow

The main menu retains choices 11 (Add Domains) and 12 (Renew Certificate). Add Domains validates the domain, stores it in `/etc/xray/domain`, `/root/domain`, the shared settings and the legacy `ipvps.conf`, and adds the hostname to the selected Nginx site. Existing hostname aliases are retained.

Renew Certificate is explicit. For an existing acme.sh installation, it uses the existing account/home/CA choices and known standalone workflow; only Nginx is stopped while HTTP-01 owns port 80. A failure trap attempts to bring Nginx back up. It does not stop arbitrary processes found on port 80. Certificate/key bytes are backed up before the explicit renewal. Existing standalone jobs that already stop/start Nginx remain intact.

For fresh installations, Certbot uses `/home/vps/public_html` for HTTP-01. Add Domains makes the HTTP server match the owned hostname before issuance. Do not block the challenge path at a CDN. Certbot's managed renewal job and one Blueblue deploy hook maintain the familiar `/etc/xray/xray.crt` and `.key` destinations.

`blueblue-cert-watch.path` observes the existing configured certificate/key paths. Its oneshot service confirms that their public keys match, grants necessary service-user read access, checks Nginx, reloads Nginx and Stunnel, and restarts Xray only if an inbound uses Xray-owned TLS (for example RAW). It requests no new certificate and edits no ACME account or cron job. Inspect failures with the journal; sequential certificate/key updates can briefly produce a mismatch before the next path event.

Do not run Renew Certificate as an XHTTP migration step. A working installation already has everything XHTTP needs for external TLS termination.

## Stunnel troubleshooting

Static inspection found concrete legacy defects:

- `stunnel5.zip` contains Stunnel **5.60** source, with no architecture-independent maintained-package lifecycle.
- The old build runs `make install`, but units invoke `/usr/local/bin/stunnel5` and the SysV script invokes `/usr/local/lamvpn/stunnel5`: these paths disagree with one another and the normal upstream executable name.
- `chmod 644 /etc/stunnel5` removes directory traversal permission.
- Forking systemd and a separate SysV init path compete for lifecycle management without a consistent tracked process.
- The bridge requires `python2` and uses Python 2 syntax; this runtime is unavailable in the supported Ubuntu package set.
- Private keys were made world-readable and TLS settings did not enforce a modern minimum.

OpenSSL 3 compatibility of that bundled build was not executed or established. It is a portability risk addressed by using the distro's maintained build; no particular OpenSSL runtime failure is claimed as observed.

The new unit intentionally retains `stunnel5.service` and `/etc/stunnel5/stunnel5.conf`, while `ExecStart` invokes the authoritative package binary `/usr/bin/stunnel4`. Existing service sections and mapped ports are retained, including an existing OpenVPN section if present. Fresh configuration only creates real SSH mappings, 447→109 and 777→22.

Operator diagnostic commands:

```bash
systemctl status stunnel5 ws-stunnel
journalctl -u stunnel5 -u ws-stunnel -n 100 --no-pager
ss -ltnp
namei -l /etc/xray/xray.key
getfacl /etc/xray/xray.key
```

Look for a missing certificate, denied directory traversal, conflicting accept port or missing Dropbear backend. Configure a customized bridge port/target using `/etc/blueblue/bridge.env`; keep the listen address loopback. Changing the target port is an explicit operator setting, not a client-controlled header.

The migrator refuses other active service sections under `/etc/stunnel/*.conf` instead of disabling unrelated package-managed tunnels. Reconcile their ownership/ports manually. A global Stunnel default certificate and per-section cert/key files are supported as long as paths are explicit and readable. External keys stored behind custom security mechanisms may need a custom unit.

## Accounts, recovery and downloads

`/etc/blueblue/accounts.json` is the expiry/transport source of truth. It is mode 0600 under a root-only directory. Atomic writes and a shared lock coordinate account edits, cron expiry, backup and migration. Runtime account changes validate the candidate Xray configuration, restart the existing service and restore the old file contents if that application fails.

The legacy Xray JSON comments are removed after migration. Unknown named users remain without an invented expiry. Anonymous seed credentials remain in their original inbound and are copied into XHTTP for compatibility; map/revoke those explicitly if they should expire. A shared UUID under conflicting usernames or a UUID with unrelated policy semantics requires manual reconciliation before migration. Do not hand-edit just one transport's account list.

Accounts expire at the local server's calendar date boundary; the timer removes entries within approximately one minute. Renewal extends from the later of today and the old expiry. Deletion removes credentials in every transport by shared identity. Optional direct transports inherit active users when first enabled; creation can then select an enabled subset. No direct transport port is exposed merely by choosing a URI format.

Private exports can be downloaded with SFTP/SCP. Published link files are credentials. Legacy HTTP port 81 remains only when already installed, and should be retired when possible. Download files are updated when renewed and removed on expiry/deletion. If disabling publication, remove old published files too; changing a setting does not erase an already-distributed credential.

`backup` creates a sensitive `.tar.gz` locally. `BLUEBLUE_BACKUP_DEST` opts into an operator-configured rclone remote. Use an encrypted private backend rather than a public repository or public share. No credentials are bundled. Restore supports the new Blueblue archive format; old ZIP backups require deliberate manual extraction and migration.

Default restore imports proxy accounts into current listeners without changing certificates, domain, ACME or routing. `--restore-config` deliberately replaces the Xray config as well. `--restore-ssh` creates only missing SSH accounts; user home data is not included and existing system usernames/passwords are not replaced. A recovery backup is created first. Errors during individual SSH account recreation may require manual completion; it is not a transactional whole-machine restore.

For full TLS/Nginx recovery, inspect the private archive off-line, copy only the intended backed-up certificate/site files in a maintenance window, and preserve or deliberately restore the corresponding ACME state together. Do not untar an untrusted archive over `/`. For full operating-system user/home or package recovery, use a machine snapshot.

## Known operational boundaries

- Configuration has not been executed or tested on the target platforms in this work.
- Single-file Xray configurations only; ambiguous HTTPS selection and unowned XHTTP locations are refused.
- Cert paths must be explicit; inherited, dynamic and multiple certificate pairs require manual handling.
- Direct RAW TLS requires service-user key access. The helper grants named ACLs; policy-constrained filesystems may refuse ACLs.
- Nginx's distro HTTP/2 build is required. No HTTP/3 listener, Cloudflare UDP tunnel or automatic REALITY keys are installed.
- mKCP is optional legacy UDP transport and should not be mistaken for TLS or HTTP.
- Old copied scripts and third-party JSON editors cannot synchronize the new metadata.
- Retired remote license, Telegram/GitHub upload, custom kernel, Webmin HTTP and DDoS-deflate bootstraps are not reinstalled. Existing unrelated services and firewall policies are preserved.
- UDPGW is a compatibility build from an infrequently released fork; compiler dependencies and provenance are recorded rather than shipping a stale ELF.
- A package installation can update maintained dependencies; rollback cannot undo all package maintainer-script effects.
