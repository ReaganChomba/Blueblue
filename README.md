# Blueblue 2026

Project: https://github.com/reaganchomba/blueblue

Blueblue manages SSH over TLS/HTTP upgrade and Xray accounts, including VLESS XHTTP. This modernization replaces the legacy destructive installers, bundled executables, Python 2 bridge and independent JSON-editing menus with shared installation and account-management code.

**Implementation status:** source changes have received code inspection only. No tests, benchmarks, live installations or VPS service operations were performed during this work. Compatibility and migration behavior require validation in an isolated Linux environment before production use. Commands below are instructions for the operator; they were not executed as part of this implementation.

## Manual publication

The clean modernization history is on `modernization-2026`. From the local project directory, publish it with:

```bash
git push --set-upstream origin modernization-2026
```

After publishing, you can set `modernization-2026` as the default branch in the fork's GitHub settings. Changing the default branch does not redirect raw URLs containing an explicit branch name; the installation links and bootstrap defaults below already use `modernization-2026`. The existing remote `main` remains unchanged. Publication is operator-managed; no successful push is claimed here.

## Platforms and prerequisites

- Primary targets: Ubuntu 22.04 LTS and 24.04 LTS with systemd.
- Debian 12 and 13 are accepted as practical secondary targets; they have not been exercised.
- Ubuntu 18.04/20.04 and Debian 9/10/11 are outside this installer's support policy, including releases that require special extended-support subscriptions. Upgrade the OS separately.
- Root access, outbound HTTPS to GitHub and distribution repositories, correct system time, an owned DNS domain and available service ports are required.
- Xray release selection recognizes x86-64, arm64, ARMv7/ARMv6, x86-32, riscv64, ppc64le, s390x and loong64. A missing upstream asset or unsupported CPU fails closed. An advertised architecture does not establish compatibility with every CPU/kernel variant.
- The Python modules use the distribution Python 3 standard library. No Python 2, pip bootstrap or third-party Python library is needed.
- Keep provider-console access and a separate backup available for server maintenance.

## Fresh installation

Use a new server. The installer refuses an existing Xray configuration or occupied Blueblue listener ports. It preserves the distribution's Nginx configuration, existing sites, OpenSSH settings, firewall policies, timezone and IPv6 settings. It does not run a distribution upgrade, replace PAM policy or reboot.

Download a reviewed copy of the project, then run:

```bash
git clone --branch modernization-2026 https://github.com/reaganchomba/blueblue.git
cd blueblue
sudo bash setup.sh
```

`setup2.sh` uses the same implementation and preserves IPv6. `ins-xray.sh` delegates to that fresh installation entrypoint; it is not a destructive Xray reset tool. Component Stunnel entrypoints `ssh-vpn.sh` and `ssh-vpn2.sh` also share their implementation and require the project bundle.

The standalone fresh entrypoint is available at:

```text
https://raw.githubusercontent.com/reaganchomba/blueblue/modernization-2026/setup.sh
```

A standalone entrypoint resolves `BLUEBLUE_REF` (default `modernization-2026`) to an immutable commit, retrieves that source archive over verified HTTPS, checks archive paths and retains it locally. Prefer reviewing the complete bundle and setting `BLUEBLUE_REF` to a reviewed commit. There is no `curl | bash` bootstrap. Installation links become usable after the operator publishes this local source to the intended repository.

After installation:

1. Create an A/AAAA DNS record for a domain you control. Do not create an AAAA record unless IPv6 actually reaches this server.
2. Run `sudo menu` and select **Add Domains** (11).
3. Select **Renew Certificate** (12). A fresh deployment requests an ACME contact email and uses the distro Certbot webroot client.
4. Configure host and provider firewalls. Create accounts from the menus.

The HTTP site is installed first; the same server block gains TLS on 443 after certificate issuance. No self-signed certificate is generated over an existing certificate. Fresh certificates use `/etc/xray/xray.crt` and `/etc/xray/xray.key`.

## Existing-server upgrade

Use `upgrade-existing.sh`, not `setup.sh`:

```bash
cd blueblue
sudo bash upgrade-existing.sh
```

Standalone entrypoint:

```text
https://raw.githubusercontent.com/reaganchomba/blueblue/modernization-2026/upgrade-existing.sh
```

The live upgrade detects the effective Xray systemd command, binary, configuration, Nginx include tree, HTTPS server, domain and certificate paths. It saves a timestamped root-only snapshot under `/var/backups/blueblue/`, merges XHTTP into the current configuration and adds its managed location to the selected HTTPS server. It updates managed commands, Xray and relevant distribution packages, and migrates the Blueblue Stunnel instance. Running it again replaces the same managed location/unit rather than adding duplicates.

Existing users, UUIDs, account expiry, routing, API, statistics, outbounds, WebSocket paths and gRPC service names are retained. Legacy VLESS accounts are provisioned on the new shared XHTTP inbound. Account metadata moves from `#vls`/`#vlsg` and other legacy comments to `/etc/blueblue/accounts.json`; the Xray file becomes ordinary JSON. All shipped proxy menus use this metadata consistently.

The upgrade requires running Xray and Nginx services. It does **not** issue/renew certificates, alter ACME account data, replace Nginx's main configuration or add a second TLS listener. It restarts managed services only when the operator executes the upgrade. Account editing briefly pauses behind a shared lock during the migration.

For an ambiguous configuration, specify the existing choices explicitly:

```bash
sudo env BLUEBLUE_DOMAIN=vpn.example.com \
  NGINX_CONFIG=/etc/nginx/conf.d/xray.conf \
  XRAY_SERVICE=xray.service \
  bash upgrade-existing.sh
```

`XRAY_CONFIG` and `XRAY_BINARY` can identify customized single-file layouts, but must agree with the effective service command. Multiple configuration directories, dynamic/inherited/multiple certificate pairs and complex ambiguous HTTPS layouts require operator reconciliation. Unknown existing XHTTP locations fail closed instead of being overwritten. Do not bypass a refusal by overwriting a server configuration.

## Xray version management

The installer retrieves `https://api.github.com/repos/XTLS/Xray-core/releases/latest` at execution time, selects the Linux asset for the detected CPU and checks its official `.dgst` SHA-256 checksum before replacement. If GitHub supplies an asset digest, that must match too. Prereleases and drafts are excluded; `XRAY_PRERELEASE=1` explicitly opts into release-list selection including prereleases. There is no hardcoded release version or branch-downloaded core executable.

Release identity and the verified archive checksum are recorded in `/etc/blueblue/xray-release.json`. To update, rerun the reviewed live-upgrade bundle. The original core changer that downloaded unrelated scripts is retired. Customized existing geodata is retained; missing release-provided data initializes the standard asset directory.

Managed Nginx, Stunnel, OpenSSH, Dropbear, OpenSSL, Certbot, Python, rclone, vnstat, speedtest-cli and installation utilities come from the enabled distribution repositories. These receive distribution security maintenance; version numbers can be lower than upstream releases. No blanket `apt upgrade`, `dist-upgrade`, package purges, custom kernel or unverified Webmin repository is installed. Existing package configuration is retained with dpkg's `--force-confold`. Package restarts are suppressed while the upgrade stages its files.

## Transports and ports

| VLESS transport | Underlying connection | TLS endpoint | Default backend / direct port | Activation |
| --- | --- | --- | --- | --- |
| WebSocket | HTTP/1.1 upgrade over TCP | Nginx 443; existing HTTP 80 retained | Fresh loopback 11001; existing port retained | Default |
| gRPC | HTTP/2 over TCP | Nginx 443 | Fresh loopback 11002; existing port retained | Default |
| XHTTP | HTTP/2 over TCP, current Xray `xhttp` implementation | Nginx 443 | Loopback 10086 | Fresh and live upgrade |
| HTTPUpgrade | Its own HTTP/1.1 upgrade over TCP | Nginx 443 | Loopback 10087 | Fresh; optional on live upgrade |
| RAW | Direct TCP | Xray TLS 1.2+ using existing certificate/key | TCP 8443 | Explicit opt-in |
| mKCP | Direct UDP | No Nginx HTTP/TLS listener | UDP 40000 | Explicit opt-in |

Nginx alone owns the public HTTPS listener. All HTTP transport backends listen on loopback. Backend ports are checked for conflicts before addition. Existing unrelated inbounds are retained as configured.

The project retains Xray's currently supported WS, gRPC and HTTPUpgrade implementations for client compatibility. Current Xray source emits non-removal deprecation notices for these transports; XHTTP is preferred for new HTTP/2 deployments. Removed HTTP/H2 transport fields are not used for new inbounds.

### XHTTP

The server uses `network: "xhttp"`, `xhttpSettings.path` and `mode: "auto"`. One shared path serves every account. Set it during first installation/migration, for example:

```bash
sudo env XHTTP_PATH=/my-shared-path/ XHTTP_PORT=10086 bash upgrade-existing.sh
```

The existing path/port is retained on later upgrades. To change it later, edit both the Xray inbound and its `# BEGIN BLUEBLUE xhttp` Nginx block in a maintenance window, then regenerate account exports. No per-account random endpoint is created.

The Nginx route uses `grpc_pass grpc://127.0.0.1:10086`, not WebSocket headers. It preserves request paths, allows streaming request bodies, and uses longer gRPC/body timeouts. It follows the official XHTTP example while using `listen ... ssl http2` syntax supported by Ubuntu's Nginx versions. This deployment does not require HTTP/3 or QUIC support.

### WebSocket, gRPC and HTTPUpgrade

Existing `/vless` and `vless-grpc` settings are preserved. Fresh VMess, Trojan and Shadowsocks routes also use their legacy WS/gRPC endpoints. HTTPUpgrade has a separate inbound and `/httpupgrade` location; sharing its HTTP upgrade headers with WS does not turn it into a WebSocket transport.

On an upgraded server, enable HTTPUpgrade explicitly:

```bash
sudo blueblue enable httpupgrade
```

### RAW and mKCP

```bash
sudo blueblue enable raw --port 8443
sudo blueblue-firewall tcp 8443

sudo blueblue enable kcp --port 40000
sudo blueblue-firewall udp 40000
```

If the public domain uses a CDN, use a direct DNS record or origin IP for these transports, for example `blueblue enable kcp --port 40000 --address origin.example.com`. RAW also accepts `--address`; its TLS SNI still uses the configured certificate domain. Run `blueblue refresh` to regenerate existing account exports after enabling a transport or changing export settings.

Both commands add a direct listener only when explicitly requested. Repeat enablement does not create another inbound. Enabled transports initially inherit active VLESS accounts; subsequent account creation can select a subset. A transport's direct port is shown in its exported URI/JSON.

RAW is Xray's current name for the TCP transport, with direct TLS here. V2rayN's share format uses the `type=tcp` alias. Automated REALITY provisioning is outside this implementation: it requires independent destination, key and client-fingerprint choices. RAW TLS remains compatible with the existing certificate architecture and avoids competing on 443.

mKCP uses `network: "kcp"` and a server-wide random seed in `kcpSettings`. Its URI uses `type=kcp&seed=...&headerType=none`. It requires direct UDP connectivity through the host and provider firewall; an ordinary Cloudflare HTTP proxy does not carry it. A seed is not equivalent to TLS identity verification or a forward-secure TLS handshake. Leave it disabled unless the client requires it. Export JSON is the authoritative fallback for clients with different URI support.

### Firewall requirements

| Port | Protocol | Purpose |
| --- | --- | --- |
| 22 | TCP | Existing OpenSSH access; preserve operator rules |
| 80 | TCP | HTTP-01, legacy non-TLS WS/SSH upgrade |
| 443 | TCP | Nginx HTTPS: HTTP transports and SSH upgrade |
| 109, 143 | TCP | Fresh Dropbear compatibility listeners |
| 447, 777 | TCP | Fresh Stunnel SSH TLS; existing section ports retained |
| 81 | TCP | Legacy download listener only where already installed |
| 8443 | TCP | Optional RAW TLS |
| 40000 | UDP | Optional mKCP |
| 700, 10085–10087, 11001–11008 | Loopback TCP | Bridge, API, HTTP transport backends; do not expose |
| 7100, 7200, 7300 | Loopback TCP | Optional SSH UDPGW compatibility control connections |

`blueblue-firewall` adds an explicit allow rule to an active UFW/firewalld instance or a checked iptables rule. It does not change default policies, persist unrelated rules, manage provider firewalls or add IPv6 rules automatically. Use your existing nftables tooling if appropriate.

## Account management and client exports

```bash
sudo add-vless
sudo blueblue account vless add alice --days 30 --transports ws,grpc,xhttp
sudo blueblue account vless renew alice --days 30
sudo blueblue account vless show alice
sudo blueblue account vless delete alice
```

The same UUID is synchronized across the account's selected enabled transports. Expiry removes credentials from every corresponding inbound. Deletion retains a revoked identity tombstone so stale copies cannot survive; recreating that username generates new credentials. A systemd timer checks expiry each minute. Existing cron calls to `xp` invoke the same idempotent operation. SSH uses system expiry and a managed-user registry; it does not delete arbitrary system users or their home directories.

If legacy WS/gRPC expiry comments disagree, migration chooses the earliest recorded date rather than extending access. Existing non-TLS WS links/JSON are also generated when the selected Nginx server already exposes the corresponding route on port 80.

Links display in the terminal. Full client JSON files and `links.txt` are stored privately under `/etc/blueblue/exports/PROTOCOL/USERNAME/`; download them over your authenticated SSH/SFTP connection. VMess, Trojan, Shadowsocks and existing SOCKS inbounds use the same structured account manager and JSON export path.

Fresh installations additionally publish a VLESS links file under an unguessable UUID-derived filename at `/accounts/HASH.txt`. This is a bearer-secret download: anyone with its URL can read credentials. Set `publish_exports` to `false` in `/etc/blueblue/settings.json` to disable future publication and remove previously published files manually. On legacy port-81 deployments, the existing `vless-USERNAME.txt` convention is preserved and now includes XHTTP. Set `legacy_download` to `false` and remove existing public files to retire that insecure HTTP download workflow. Renewal rewrites exports; deletion/expiry removes managed VLESS download files.

Current V2rayN with an updated Xray core is the primary share-link target. Other Xray-based clients can import the generated JSON when they support the selected transport. Client support differs by version; no client interoperability testing was performed.

VLESS examples (replace placeholders and percent-encode values):

```text
vless://UUID@vpn.example.com:443?encryption=none&type=ws&security=tls&sni=vpn.example.com&host=vpn.example.com&path=%2Fvless#alice-ws
vless://UUID@vpn.example.com:443?encryption=none&type=grpc&security=tls&sni=vpn.example.com&serviceName=vless-grpc&mode=gun&alpn=h2#alice-grpc
vless://UUID@vpn.example.com:443?encryption=none&type=xhttp&security=tls&sni=vpn.example.com&host=vpn.example.com&path=%2Fxhttp%2F&mode=auto&alpn=h2#alice-xhttp
vless://UUID@vpn.example.com:443?encryption=none&type=httpupgrade&security=tls&sni=vpn.example.com&host=vpn.example.com&path=%2Fhttpupgrade#alice-httpupgrade
vless://UUID@vpn.example.com:8443?encryption=none&type=tcp&security=tls&sni=vpn.example.com&headerType=none#alice-raw
vless://UUID@DIRECT-DNS.example.com:40000?encryption=none&type=kcp&security=none&seed=SEED&headerType=none#alice-kcp
```

VLESS `encryption=none`, the transport choice, and transport security (`tls` or `none`) describe different layers. They are not interchangeable.

## Mux.Cool and XHTTP sessions

Generated client outbounds have `mux.enabled=false`. Mux.Cool is protocol-level connection multiplexing; it does not multiply link capacity. Do not turn it on indiscriminately for gRPC, HTTP/2 or XHTTP.

XHTTP's `xmux` controls its own HTTP connection/session reuse and concurrency. Server defaults are left untouched, and no `xmux` values are forced into generated links. For advanced clients, edit `streamSettings.xhttpSettings.xmux` in an exported client JSON using the current Xray documentation. Supported controls include `maxConcurrency` and `maxConnections` (mutually exclusive), reuse/request limits and keepalive period. Changing one can alter defaults for the others; use a complete deliberate configuration. URI `extra` is a client implementation feature, not an invented bandwidth setting. No general Mux toggle is exposed in the account menu.

## Stunnel, domains and renewal

The **Add Domains → Renew Certificate** menu workflow remains available. Add Domains records the owned domain and updates the selected site's hostname for HTTP-01. Renew Certificate is an explicit operator action: it backs up existing certificate/key files, reuses an existing `/root/.acme.sh` account when present, or uses Certbot webroot for a new deployment. It retains the configured certificate destinations. Existing ACME renewal jobs remain installed; live upgrade never invokes issuance or renewal.

The distribution `stunnel4` package contains modern Stunnel 5.x linked to the distribution's OpenSSL. The Blueblue `stunnel5.service` name remains for menu compatibility. Its configuration remains `/etc/stunnel5/stunnel5.conf`, with existing `[service]`, `accept`, `connect`, `cert` and `key` values retained. Foreground operation, systemd supervision, TLS 1.2 minimum, an unprivileged service user, narrowly scoped bind capability, restart policy and journal logging replace the old bundled build and SysV daemon paths. Read ACLs allow service users to read existing private keys without making them world-readable.

The SSH bridge now uses Python 3 asyncio, binds loopback port 700, fixes its target to loopback Dropbear 109, limits headers/connections, handles partial writes and closes both directions. It preserves legacy payload clients' HTTP-101-followed-by-raw-SSH behavior. It does not implement RFC6455 WebSocket framing and is not a generic browser WebSocket server. `X-Real-Host` can no longer choose arbitrary local services. Configure explicit bridge options in `/etc/blueblue/bridge.env` if needed.

An added systemd path watcher reloads consumers when existing certificate files change; it does not compete with ACME or request certificates. See [operations and troubleshooting](docs/OPERATIONS.md) for certificate permissions, standalone renewal, Stunnel diagnostics and rollback.

## Backup, recovery and limitations

```bash
sudo backup
sudo env BLUEBLUE_BACKUP_DEST=my-private-rclone:blueblue backup
sudo restore /var/backups/blueblue/accounts/blueblue-TIMESTAMP.tar.gz
```

Backups stay local by default, mode 0600, with proxy metadata, configurations, SSH recovery records, existing certificates and ACME data. No shared tokens, public repository uploads or default rclone destination are supplied. Use a private encrypted rclone backend if uploading. Restore imports accounts into the current transport architecture while preserving current domain/certificate/renewal settings. `--restore-config` explicitly restores the backed-up Xray configuration; `--restore-ssh` creates missing SSH users and refuses existing usernames. Full machine/TLS recovery is a deliberate operator procedure; see [operations](docs/OPERATIONS.md).

Legacy Trojan-Go provisioning, remote license checking, shared Cloudflare accounts, DDoS-deflate downloads, global log truncation, custom BBRplus kernels and automatic SSH restarts/session killing are retired. Existing unrelated services are retained. Stock-kernel BBR remains an explicit option. Webmin installation is left to its authoritative signed-repository instructions.

The bundled BadVPN ELF is removed. Optional `install-udpgw.sh` builds UDPGW from a resolved stable release commit of the ssrlive fork, with loopback systemd instances. Fresh installs opt in with `BLUEBLUE_ENABLE_UDPGW=1`; live upgrades migrate a detected legacy `/usr/bin/badvpn-udpgw`. This is legacy client compatibility software with infrequent upstream releases, not a new general UDP VPN. Prefer current Xray transports for new clients. Existing binary/source snapshots are retained for rollback.

Automated REALITY deployment, arbitrary Nginx layouts, multi-file Xray configurations, third-party account editors, legacy ZIP backup import and browser RFC6455 SSH clients are outside the supported automated path. Anonymous legacy credentials are preserved but lack expiry metadata; reconcile them manually. Do not use old copied account scripts after migration: they expect comment markers that no longer exist.

## Architecture and sources

See [dependency map and file inventory](docs/ARCHITECTURE.md), [operations and rollback](docs/OPERATIONS.md), and [implementation report](docs/IMPLEMENTATION.md).

Technical references:

- [Xray-core](https://github.com/XTLS/Xray-core), [transport configuration](https://xtls.github.io/en/config/transport.html), [transport documentation](https://xtls.github.io/en/config/transports/).
- [Official XHTTP Nginx example](https://github.com/XTLS/Xray-examples/tree/main/VLESS-XHTTP3-Nginx) and [XHTTP implementation guide](https://github.com/XTLS/Xray-core/discussions/4113).
- [Outbound Mux documentation](https://xtls.github.io/en/config/outbound.html), [Mux.Cool protocol](https://xtls.github.io/en/development/protocols/muxcool.html).
- [V2rayN share-link implementation](https://github.com/2dust/v2rayN/blob/master/v2rayN/ServiceLib/Handler/Fmt/BaseFmt.cs), [Stunnel manual](https://www.stunnel.org/static/stunnel.html).

Original Blueblue source and authorship: [NevermoreSSH/Blueblue](https://github.com/NevermoreSSH/Blueblue), original copyright comments © 2022 NevermoreSSH. Original-author and third-party attribution are retained; runtime ownership/download references use `reaganchomba/blueblue`. Git remotes were configured only after the subsequent explicit publication request: `origin` is the intended fork and `upstream` is the original source. The modernization is prepared locally on `modernization-2026` for manual publication; the fork's existing `main` is preserved. Project installation URLs and the default `BLUEBLUE_REF` explicitly use `modernization-2026`, independently of the repository's default-branch setting.
