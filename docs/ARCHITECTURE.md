# Architecture and dependency map

The original tracked-file inventory is in [SOURCE-INVENTORY.md](SOURCE-INVENTORY.md). Text source, duplicates, binary signatures and the Stunnel archive contents were inspected. The speedtest files were ELF executables, not Python source. The archive was inspected without running its configure/build/tests. No bundled executable was executed or decompiled.

## Original installation graph

```mermaid
flowchart TD
    setup[setup.sh] --> ssh[ssh-vpn.sh]
    setup2[setup2.sh] --> ssh2[ssh-vpn2.sh]
    setup --> common[cf.sh / jembot.sh / ins-xray.sh / set-br.sh]
    setup2 --> common
    common --> xray[Xray + Nginx + certificates + generated config]
    ssh --> old[Dropbear + OpenSSH + Stunnel bundle + Python 2 bridge + UDPGW ELF]
    ssh2 --> old
    setup --> commands[/usr/bin menus, account editors, monitors and backup]
    setup2 --> commands
    commands --> comments[Independent sed edits to commented Xray JSON]
    commands --> downloads[Core changer and other downloaded replacements]
```

`setup.sh` and `setup2.sh` are not identical: the latter downloads `ssh-vpn2.sh`, changes cleanup names and has a minor cron-layout difference. The SSH installers are also different: `ssh-vpn.sh` writes IPv6-disable settings; `ssh-vpn2.sh` comments them out. Both otherwise share the destructive installer and Stunnel problems. The modern aliases preserve IPv6 and share code.

Both original setup scripts download/install commands into `/usr/bin`: add-ws, add-ssws, add-socks, add-vless, add-tr, add-trgo, autoreboot, restart, tendang, clearlog, running, cek-trafik, cek-speed, cek-bandwidth, cek-ram, limit-speed, all protocol/SSH menus, menu-bckp, usernew, xp, and the main menu. Setup downloads two different backup menus to the same `menu-bckp` path, so the latter silently replaces the former. It also references files not tracked in this repository, including a bot backup script. The old main menu can retrieve a separate core changer and additional helpers from unrelated repositories. These replacement/download paths are removed from modern command dispatch.

`ins-xray.sh` obtains Xray twice using inconsistent methods (an installer script and a manually downloaded archive), generates random loopback ports, writes a new Nginx configuration, creates commented Xray JSON and writes a new systemd unit. It also bootstraps acme.sh and changes certificate permissions. `set-br.sh` installs rclone and downloads a shared rclone account, builds a bandwidth helper from another source and installs backup/restore/log cleaner commands. `jembot.sh` builds an old vnstat release. These paths now use shared installers and distribution packages.

The old SSH path installs a bundled BadVPN ELF, builds Stunnel 5.60 from a ZIP, writes both SysV and systemd management, runs the Python 2 bridge on loopback 700, rewrites SSH/PAM/rc.local, downloads DDoS-deflate over HTTP and modifies global firewall rules. None of those unrelated global edits is part of the new installation path.

Original proxy lifecycle tools are not internally consistent: VLESS creation uses `#vls`/`#vlsg`, whereas the separate user-display/deletion scripts look for `###`. Expiry removes VLESS WS/gRPC but has no mechanism to remove a future XHTTP identity. VMess has extra worryfree/kuota WS endpoints, which must not be confused with ordinary `/vmess`. All current proxy editing aliases now enter the same structured manager.

Original backup files differ substantially: the simple script uploads to a bundled rclone account; the two menus combine license checks, archive upload and unrelated repository writes. The modern wrappers preserve backup/restore entrypoints while removing their shared destinations and credentials.

## New installation graph

```mermaid
flowchart TD
    setup[setup.sh / setup2.sh / ins-xray.sh] --> installer[lib/install.sh]
    upgrade[upgrade-existing.sh] --> live[lib/upgrade.sh]
    live --> snapshot[probe.py + snapshot.py]
    live --> installer
    installer --> apt[Signed distribution packages]
    installer --> release[Official Xray release API + checksums]
    installer --> manager[lib/blueblue.py]
    live --> manager
    manager --> json[Existing Xray JSON + /etc/blueblue account metadata]
    manager --> nginx[Selected existing Nginx HTTPS server]
    installer --> tls[stunnel.py + Python 3 bridge]
    installer --> commands[/usr/bin compatibility commands]
    commands --> manager
    commands --> domain[domain helpers + existing ACME or fresh Certbot]
    commands --> backup[Private local backup helper]
    expiry[Expiry timer / existing xp cron] --> manager
    watcher[Certificate path watcher] --> consumers[Nginx / Stunnel / optional Xray TLS reload]
```

`lib/install.sh:commands()` is the authoritative command-installation map. It installs all checked-in account/menu/monitor wrappers into `/usr/bin`, shared implementation modules into `/usr/local/lib/blueblue`, and the bridge into `/usr/local/bin/ws-stunnel`. `menu-update` points to the local menu; `xraychanger` explains the backed-up upgrade process. No runtime menu overwrites itself with remote branch contents.

### Service relationships

| Service | Configuration / executable | Dependencies and listeners |
| --- | --- | --- |
| Xray | Existing config/binary/unit on upgrade; `/etc/xray/config.json`, `/usr/local/bin/xray` fresh | Loopback HTTP transports and API; direct optional RAW/mKCP |
| Nginx | Existing main/include graph; fresh extra `conf.d/blueblue.conf` | Public 80/443; TLS terminates once; HTTP transport backends on loopback |
| Stunnel | `/etc/stunnel5/stunnel5.conf`; package `/usr/bin/stunnel4` | Existing cert/key; existing SSH/OpenVPN backend mappings; fresh 447/777 |
| SSH bridge | `/usr/local/bin/ws-stunnel`; Python 3 asyncio | Loopback 700 to fixed loopback Dropbear 109; Nginx provides external HTTP/TLS |
| Dropbear/OpenSSH | Distribution packages; existing configs retained on live upgrade | Linux account/password/expiry state |
| Expiry timer | `blueblue-expiry.service` → `xp` | JSON-aware proxy removal and managed SSH account locking |
| Certificate watcher | `blueblue-cert-watch.path/service` | Existing certificate files; no ACME issuance or scheduling |
| Optional UDPGW | Source-built binary; `blueblue-udpgw@.service` | Loopback 7100/7200/7300 TCP control; relays outbound UDP |

Stunnel and Nginx consume certificate files but never compete for port 443 in this architecture. SSH's legacy payload upgrade is distinct from Xray WS, HTTPUpgrade and XHTTP. The XHTTP backend is HTTP/2 over loopback TCP, and mKCP is direct UDP.

## Dependency dispositions

| Legacy dependency | Modern source / disposition |
| --- | --- |
| Xray downloaded twice without matching verification | One official release API/checksum implementation, stable by default |
| Stunnel 5.60 ZIP and inconsistent custom paths | Distribution `stunnel4` package and one `stunnel5.service` |
| Python 2 bridge | Project-owned Python 3 standard-library asyncio implementation |
| Two identical x86-64 speedtest ELFs | Readable Python launchers for distro `speedtest-cli` |
| Bundled BadVPN ELF | Removed; optional source build at ssrlive stable release commit |
| Old vnstat source release | Distro `vnstat` |
| rclone binary/config downloads | Distro `rclone`, operator configuration only |
| Git-built wondershaper variants | Distro `wondershaper`, positional interface/rate CLI |
| Remote acme.sh bootstrap | Existing acme.sh state retained; fresh distro Certbot |
| Custom BBRplus kernel and kernel purges | Optional stock-kernel BBR sysctl only |
| DDoS-deflate HTTP scripts | Retired; no global firewall replacement |
| Webmin unsigned legacy repository / disabled TLS | Retired bootstrap; authoritative installation instructions only |
| Ruby/lolcat, neofetch/screenfetch decoration | Not needed by new menus; no language package downloads |
| PAM replacement and shared DNS/Cloudflare credentials | Retired; existing system policy and operator-owned DNS |
| Remote license gates and repository backup pushes | Retired; local ownership, private configurable backup |

Distribution-maintained stable packages are selected at installer execution time. Compatibility has been reasoned about from code and authoritative upstream sources, not demonstrated by tests.

## Attribution

Original Blueblue scripts carry NevermoreSSH authorship and 2022 copyright comments, retained in the rewritten entrypoint headers and project documentation. The unchanged optional region checker preserves its original authorship and is not installed by default. The replaced memory-report script credited Pádraig Brady's LGPLv2 `ps_mem.py`; no code from that implementation remains in the `free` launcher. Bundled Stunnel source includes its own upstream copyright, now superseded operationally by the distribution package. Xray, Stunnel, BadVPN/fork and other separately installed packages retain their upstream licenses and distribution copyright metadata.
