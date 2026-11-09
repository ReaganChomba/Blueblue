# Original tracked-file inventory

Every original tracked blob was read during source inspection. The identifiers below describe the imported source, not a retained Git history. Bundled artifacts were inspected as data only; no executable, build or tests were run.

| Original file | Bytes | SHA-256 | Disposition |
| --- | ---: | --- | --- |
| `.gitignore` | 350 | `2ef767385125df7d546a79f251e267fab5c0e68a652128987a6982cb61d53584` | Replaced old application ignores with Python/archive/secret ignores. |
| `README.md` | 4628 | `ba8cf280924eaf59f02e9a2bc6abd037a18c2b5b4b98ac3912a9d68a634e3e4a` | Rewritten installation, upgrade, transport, certificate and recovery documentation. |
| `add-host.sh` | 98 | `b0ce52ad7ad3675b258a81961d1284a56b107e84bcf503cde491a411cd283156` | Wrote different legacy state directory; now same validated domain manager. |
| `add-socks.sh` | 9917 | `539f9d259e09e613fb567c2110572d58c482e94560dfddcd85f4d0a73596b17a` | Protocol-specific sed editor/exporter; now structured shared account creation and JSON exports. |
| `add-ssws.sh` | 11350 | `a538d9e575fa69b1ddd71880960fd8635d67a313d399de06182f68cd32d595bc` | Protocol-specific sed editor/exporter; now structured shared account creation and JSON exports. |
| `add-tr.sh` | 7600 | `3e75d4bf7dc922b4c12aba406577c20ba5d050051577813380927ec55de18fe6` | Protocol-specific sed editor/exporter; now structured shared account creation and JSON exports. |
| `add-trgo.sh` | 5522 | `1f53ab1178d18772942907a02a7ead372f629d6807cf52eb6b8a67dc73a056e0` | Independent Trojan-Go account editor; redirects to maintained Xray Trojan menu. |
| `add-vless.sh` | 7911 | `5a2127a669727ec79fa17416430948ba71bdc5af3477b11fa37c35db1182cf12` | WS/gRPC credentials and links; now shared manager with XHTTP and transport selection. |
| `add-ws.sh` | 11453 | `d0b6b5e9818f6303cb8506ca217cb46bc5958d1c85809a0ee4b4f692576dfbe7` | Protocol-specific sed editor/exporter; now structured shared account creation and JSON exports. |
| `autoreboot.sh` | 5919 | `cb2015410e41ee71ad9bb6c7e07a0bd4c49948251b7bccb2eb04f8786ee05e33` | Legacy cron menu; now explicit managed hourly choice, disabled unless selected. |
| `backup.sh` | 2043 | `73ed2825ca0765cd1df427e02723bbee9718f300b5687d06706eb3202819e166` | Uploaded through shared rclone destination; replaced by private configurable archive helper. |
| `bbr.sh` | 4160 | `1bbae586113bd9492a3dfed6b52e49bb95377e1510644bebf59eb6debe816ff4` | Downloaded custom kernel, deleted existing kernels/sysctls; now optional stock-kernel BBR settings. |
| `cek-bandwidth.sh` | 6018 | `650d47610cd5772ee84fb3ab071537e17c77aa8cd08dcb0bf2f717a42ddbc520` | vnstat menu; now distro vnstat launcher. |
| `cek-trafik.sh` | 2936 | `9a520d144206bf6501bcf3702a9bc41ecd639aec9b93050672c0ae4082b65014` | Stats query at loopback API; now uses detected core binary. |
| `cekv.sh` | 1514 | `e419206586590e5f379ecd3fd145afa3c6dfac0b3174d53839a60b095f7a9029` | Mutable remote version check; now displays recorded verified core release. |
| `cf.sh` | 1982 | `69109db7be36c721ffb3ca230e177dc5e6a17b20d39760ea9beb02dab11a39fb` | Cloudflare shared account API and forced domain; now owned-domain menu wrapper. |
| `cfa.sh` | 3296 | `12d7520a92da1cfe30b5400b273a74f48126ee361eb35b321cbebf31dd5f7cb6` | Cloudflare API additionally created wildcard DNS; now owned-domain menu wrapper. |
| `clearlog.sh` | 627 | `30eda71dd09dcb9eb2b02be973b7ce8692fdd13f815195fab16c321b2088d4ce` | Truncated unrelated global logs; now distro logrotate invocation. |
| `del-xrays.sh` | 2420 | `c3c75422d7711ab6fb0af72346b07f853e96efbb8080b927d530437ef839ad58` | Separate legacy marker deletion; now all-transport VLESS deletion. |
| `dns.sh` | 2973 | `ff731cb7463d7a851d3841aa1cc5b2899514cb6fc8173f23c6cd9a332699d401` | Replaced resolver files; now read-only resolver information. |
| `domain.txt` | 79 | `20250494bf548d78fdc4daadef3db5b1d56b3769426768af0d852121d25b6149` | External domain inventory; replaced with owned-domain guidance. |
| `ins-xray.sh` | 22750 | `c0c52908efc94f46826dcdb4253113667b57951231e372dbcdf95c76033e27d7` | Generated commented Xray JSON, random ports, Nginx and ACME; replaced with shared fresh path. |
| `issue.net` | 588 | `1c679459560795091aac4c3d1ee20540575a6de401691804e02485b340562469` | Original service banner asset retained. |
| `jembot.sh` | 2989 | `f7585a54a58ea906d0ac6382663669f91cc3f7917cea5fc1b2177ea9fd21ee1c` | Old vnstat source build; now distro vnstat package. |
| `limit-speed.sh` | 3264 | `1fc4e8ae75804c95a783aa4def5400a9d62216814ce5ca2d738f0f09df53045f` | Inconsistent cloned wondershaper CLI; now distribution CLI with validated rates. |
| `limit/README.md` | 7 | `6172591bc5eb23d23f845b3ac4477c3f15e16b54a75f69d3a7bf3fec9c7e8b98` | Original directory marker retained. |
| `limit/limit.txt` | 730 | `8d420ffea145035ffbf932080c91698ca7135b1d6165919daf20c21cd749cd49` | Remote license/IP registry; retired without server identity uploads. |
| `logcleaner.sh` | 696 | `f199729019a92678cb50c298922ea7b7e28c877c1ffa92cde978d6201aa24b73` | Repeated destructive global cleaner; now distro logrotate invocation. |
| `menu-bckp-github.sh` | 11047 | `99f85311c789d243eb36a15f66aff018aed24c5ef5b6356c47a6c5bdbb173ab9` | License-gated repository uploader with embedded credentials; replaced with local backup menu. |
| `menu-bckp-telegram.sh` | 12188 | `19fb1bda76547f80ad1f3f8394d1f39c45957245c544376eca72162e85b12878` | Different Telegram/repository backup implementation; replaced with configurable backup menu. |
| `menu-socks.sh` | 8306 | `a95ec2f83e540e604a1ecfeef28364283dff12e8d103b95ea3cd31d6a446142b` | Protocol/SSH lifecycle menu; now local shared management helper. |
| `menu-ss.sh` | 8320 | `a61cec2761b9150392ba66dc7fcb6b2b65b5d3d8aa4e143bf63648bf0bbed9b6` | Protocol/SSH lifecycle menu; now local shared management helper. |
| `menu-ssh.sh` | 20515 | `ffb17f7c2d91366959c99c1556263d39cc5df7a9022bd6eb2ea144da49d6d582` | Protocol/SSH lifecycle menu; now local shared management helper. |
| `menu-trgo.sh` | 7530 | `ea2bc1a89ff118e5cd4f843c08cb3d8de1da76734ad95c35551fbde6e81e602d` | Independent Trojan-Go lifecycle; redirects to Xray Trojan menu. |
| `menu-trojan.sh` | 8378 | `567ffc6bd33e388387984eb08d0d002b64f019f917eea1be1fee59f090437057` | Protocol/SSH lifecycle menu; now local shared management helper. |
| `menu-vless.sh` | 8332 | `b380632e89364b57f6313f612bdc2f3fca990b251c482bdb146f6e5b7f5f3e62` | Separate sed renewal/deletion; now shared full lifecycle menu. |
| `menu-vmess.sh` | 8379 | `a1d34c5d98b0d0ada0bc6bb12363cdf46303bd16686530468c7a03c3e6bdcb5b` | Protocol/SSH lifecycle menu; now local shared management helper. |
| `menu.sh` | 10578 | `f6038fbedc0b199b17f9cca9524584f141f11887510b9a5d6949ee9e02522dde` | Main menu with domain/certificate functions; rewritten around local shared commands. |
| `menu4.sh` | 14192 | `7ed1f3f70395587faef56e196e974580fcf920c827db0c8d82bce1c4f260be7e` | Different main menu with downloaded core/kernel/other helpers; now main-menu alias. |
| `netf.sh` | 10443 | `4b018a359ba98ad8f23ea77e013f2662e01c0cb779d426983a4e60d8a99a8156` | Original optional region checker and attribution retained; not installed by default. |
| `newudpgw` | 496472 | `fb7bc61d566183d68e0214ba7d26ffe20c7415abb8d23b0a8ee9753a6dd0c200` | x86-64 ELF without a source/update lifecycle; removed; optional source-build replacement. |
| `nginx.conf` | 1234 | `ec1db5bf9ecff5e332b6b0704800106e441044cbea74e5f92d9886541bfa19c9` | Full global config, historical CDN trust list and autoindex; now reference only, never overwrites host config. |
| `password` | 1440 | `ede17d3b24602a774a51fde44a5afd536f73eb3da65f948926ab7952b474d3b0` | System PAM password stack replacement; retired, never copied over distribution PAM. |
| `ram.sh` | 21746 | `74af063ae841a8b8b6846727a654314d42d44ed1d55908b33ee1607e96ae1f1b` | Vendored ps_mem Python script; replaced with distribution free launcher; prior attribution recorded. |
| `rclone.conf` | 465 | `2322cf28491ef49a9d56ec3c8c56a5ca1db0d24b79364b880928f42bb29b064f` | Embedded OAuth state; replaced with credential-free explanatory file. |
| `restart.sh` | 5785 | `83309b0c7bbf9b64a9efa971fb6ab3cf61627f45647d3bd197a1e037c9b3ef48` | Broad service/rc-local restart menu; now allowlisted explicit service selection. |
| `restore.sh` | 2613 | `b9e23aa7201355d04d8fcaf284a51c09eb7bcd8e2fe4c64a03ae950ab7791785` | Downloaded ZIP and overwrote system account files; replaced by deliberate account import. |
| `running.sh` | 14477 | `281740da736a7576eb6f3d6edb81a83c309ffb6607e561fd9d3472efecee0bff` | Legacy service status with external IP probes; now local systemd status. |
| `set-br.sh` | 1855 | `3d332acaf1748d0fdb7bf2113878cf948482074a4c35bc85926193b802459231` | Shared rclone config and cloned helper installer; now distro packages/local commands only. |
| `setup.sh` | 17500 | `403cc75da40fbac045fb0b2adc8b32c887b94ca24a82703532c4bda441617af0` | Legacy destructive fresh installer; replaced with shared installer entrypoint. |
| `setup2.sh` | 17506 | `a4b48ab88204e2b29c6c92a3ec774922217ecbd5275e33cf5013559680bfe608` | Distinct IPv6 installer entrypoint; now shares setup implementation and preserves IPv6. |
| `speedtes_cli.py` | 2244696 | `ad551827bacd33cf7fe0b83ebb8df956be3c70f3e5dab6c6d20fb81ff2d824db` | x86-64 ELF, identical to speedtest_cli.py; replaced with distro utility launcher. |
| `speedtest_cli.py` | 2244696 | `ad551827bacd33cf7fe0b83ebb8df956be3c70f3e5dab6c6d20fb81ff2d824db` | x86-64 ELF despite .py extension; replaced with distro utility launcher. |
| `ssh-vpn.sh` | 18450 | `9c05c053ca8915d6eb46b412c8f9a7833ea4bf3d3cca0f2631c62f49b78d87ad` | SSH, Dropbear, Stunnel, Python 2, UDPGW and global system edits; now shared package/Stunnel path. |
| `ssh-vpn2.sh` | 18454 | `185015aa28f30334d751e4be60a93cdf7d7cc41f302309235f80078be28176d8` | Distinct IPv6-preserving variant of SSH installer; now shared package/Stunnel path. |
| `stunnel5.init` | 5397 | `e6c37aace3555b5be146a1c8c772b662eb1b020fe799a6e13dbde44ed77a64b9` | SysV implementation referenced a different executable than systemd; replaced with compatibility wrapper. |
| `stunnel5.zip` | 1094033 | `69851faf17bcd0e2c06c2cb8c0b70c84dfed576807014a557158fd08c2c1488d` | Stunnel 5.60 source archive (226 entries); removed in favor of distro package. |
| `tendang.sh` | 3395 | `fd7b1d7c4d8703dc84e5be0a36fe7d02343ee1f6c8bb8ad0a5b7fd16fa5e9565` | Killed sessions and restarted SSH daemons automatically; now displays sessions and policy guidance. |
| `test/README.md` | 11 | `25cc48f932543df1e0740ea5da820834cec00969fe5f6c302983fcb278f2f06e` | Original directory marker retained; no tests executed. |
| `test/validated-registered-license-key.txt` | 275 | `8ee66bc6612f3e730f84c0ec78271aac5077f18fe6e2dd61fdef3f029ecded54` | Legacy license data retired. |
| `test/versions` | 4 | `66e4c000f2000eb1cca164f97c441e14d438ca2599c8e79f4de6ecade0de8b32` | Legacy script version marker updated. |
| `user-xrays.sh` | 5000 | `40bc337fbcc247cd0e9a08e8df03f62c88a8c7b547f177e6f80e1b456cc965b5` | Looked for metadata inconsistent with add-vless; now structured VLESS export. |
| `usernew.sh` | 12038 | `d19fdf68ceeeffdba98ba64c402a13ae69869c845a6b96b87d4f9068d8111631` | Linux SSH user creation; now validated system-expiry and managed registry helper. |
| `vps.conf` | 494 | `81cadef1cf70dc80c03fbf845e725d107169410fb0a77fca967076bc836af9ee` | Public port-81/PHP site; now optional loopback-only static-download reference. |
| `webmin.sh` | 3800 | `ab86a0d2cb9a6200e7667ce64ff99f0d0f68c60eeb8738d2e1ae8f7874a97f06` | Legacy apt key/repository and disabled Webmin TLS; replaced with authoritative manual guidance. |
| `ws-stunnel` | 7601 | `9a7eea1f817ffd281243fa5484e2f228f1732465ab26778544dc17b39c786386` | Python 2 raw SSH HTTP-101 bridge; replaced by fixed-target bounded Python 3 asyncio bridge. |
| `xp.sh` | 4167 | `133ed69a9e777361f4cf40509a23427c109d8db623a0d6b61616ecf0c286904e` | Independent protocol sed deletion and broad system user removal; now shared expiry helpers. |
