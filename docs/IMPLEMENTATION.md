# Implementation report

The project was prepared as a new repository without inherited upstream commits. At the subsequent publication request, `origin` was configured as `https://github.com/reaganchomba/blueblue.git` and `upstream` as `https://github.com/NevermoreSSH/Blueblue.git`. Each project file has its own commit. The clean history is committed locally on `modernization-2026` for manual publication, preserving the fork's existing `main` history. No push succeeded; publication will be performed by the operator. Project installation URLs and bootstrap defaults use `modernization-2026`. The existing Desktop `Blueblue` directory was left untouched. Cloned Git metadata was moved outside the new project after automatic approval review rejected recursive metadata deletion. It is not part of the new repository.

## Changed existing files

61 original files have rewritten content, 22 files are new, and two obsolete bundled artifacts are removed. Four source assets retain their original bytes: `issue.net`, `netf.sh`, `limit/README.md` and `test/README.md`. The final repository contains 87 tracked files, committed individually for review.

- Installers: `setup.sh`, `setup2.sh`, `ins-xray.sh`, `ssh-vpn.sh`, `ssh-vpn2.sh`, `jembot.sh`, `set-br.sh`.
- Accounts: `add-vless.sh`, `menu-vless.sh`, `user-xrays.sh`, `del-xrays.sh`, `usernew.sh`, `xp.sh`, `menu-ssh.sh`, all VMess/Trojan/Shadowsocks/SOCKS add/menu entrypoints, and the retired Trojan-Go entrypoints.
- Menus/helpers: `menu.sh`, `menu4.sh`, `restart.sh`, `running.sh`, `cekv.sh`, `cek-trafik.sh`, `cek-bandwidth.sh`, `clearlog.sh`, `logcleaner.sh`, `ram.sh`, `limit-speed.sh`, `tendang.sh`, `autoreboot.sh`, `dns.sh`, `bbr.sh`, and `webmin.sh`. The optional original `netf.sh` region checker remains as a source asset and is not installed by default.
- Backup/configuration/docs: `backup.sh`, `restore.sh`, both backup menus, `rclone.conf`, `password`, `nginx.conf`, `vps.conf`, `domain.txt`, legacy license/version files, `.gitignore`, and `README.md`.
- Stunnel/bridge/dependency launchers: `stunnel5.init`, `ws-stunnel`, `speedtest_cli.py`, `speedtes_cli.py`.

Removed obsolete binary/source bundles: `newudpgw`, `stunnel5.zip`. The two ELF files disguised as speedtest Python files are replaced with readable launchers. Source blob identities and per-file dispositions are recorded in `SOURCE-INVENTORY.md`.

## New files

- `upgrade-existing.sh`: standalone existing-server entrypoint.
- `install-udpgw.sh`: optional pinned-release source build and loopback service migration.
- `lib/blueblue.py`: official release/checksum handling, commented-JSON import, account transactions, transports, URI/JSON exports and Nginx routing edits.
- `lib/install.sh`, `lib/upgrade.sh`, `lib/probe.py`, `lib/snapshot.py`: shared installation, effective-service detection and timestamped file rollback.
- `lib/stunnel.py`, `lib/ws_bridge.py`: packaged Stunnel migration and bounded Python 3 SSH upgrade bridge.
- `lib/domain.sh`, `lib/domain_config.py`, `lib/cert-watch.py`: domain/certificate workflow and renewal-consumer reloads without replacing existing ACME jobs.
- `lib/ssh-account.py`, `lib/protocol-menu.sh`, `lib/backup.py`, `lib/firewall.sh`: account/menu, private backup and explicit firewall helpers.
- `systemd/xray.service`, `.gitattributes`, and documentation under `docs/`.

## Implemented behavior

Shared VLESS credentials and expiry cover WS, gRPC, XHTTP and optional HTTPUpgrade, RAW TLS and mKCP. Ordinary Mux is disabled in generated client outbounds; XHTTP session defaults remain intact. Menus and scheduled expiry use one JSON-aware manager. Existing routing/API/statistics/outbounds and named credentials are retained by migration. Official Xray releases are architecture-selected and checksum-verified at installation time.

Fresh installation creates an HTTP site and new service configuration, then activates existing-style certificate paths through Add Domains → Renew Certificate. The live upgrade patches the current Xray/Nginx configuration, retains the existing Xray service and certificates, and never requests renewal. Both use the same manager and dependency implementation.

Stunnel uses a distro-maintained OpenSSL-linked binary, foreground systemd management, non-root identity, bind capability, TLS 1.2+, journal logging, readable/traversable configuration and narrowly granted key ACLs. Existing section ports/certificate locations remain. The Python 2 bridge is replaced, preserving the legacy raw payload behavior.

Manual configuration remains: push `modernization-2026` and optionally select it as the fork's default branch, choose DNS/domain and ACME contact, allow necessary host/provider ports, opt into direct transports, reconcile customized/ambiguous service layouts, configure any private backup remote, and import current client links/JSON. REALITY deployment and browser WebSocket framing are not implemented. Optional legacy helper retirement and other boundaries are documented in the README.

**Tests were not run.** No unit/integration suites, benchmarks, live installation, VPS access or VPS service restart was performed. Remote configuration and publication were subsequently requested explicitly. Remotes are configured; the push failed authentication, and the operator chose to publish manually. Runtime guard commands exist in the delivered code but were not executed during development or publication.
