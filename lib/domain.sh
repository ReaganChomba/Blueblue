#!/usr/bin/env bash
set -Eeuo pipefail
umask 077
[[ $EUID == 0 ]] || { echo 'Root required' >&2; exit 1; }
exec 8>/run/lock/blueblue-domain.lock
flock -n 8 || { echo 'A domain operation is running'; exit 1; }
action=${1:-add}
if [[ $action == add ]]; then
    read -rp 'Domain/Host: ' domain
    python3 /usr/local/lib/blueblue/domain_config.py set "$domain"
    echo 'Domain saved. Select Renew Certificate from the menu to activate TLS.'
    exit
fi
[[ $action == renew ]] || { echo 'Usage: blueblue-domain add|renew'; exit 1; }
mapfile -t info < <(python3 /usr/local/lib/blueblue/domain_config.py info)
(( ${#info[@]} == 3 )) || { echo 'Domain/certificate detection failed'; exit 1; }
domain=${info[0]}; cert=${info[1]}; key=${info[2]}
stamp="/var/backups/blueblue/cert-$(date -u +%Y%m%dT%H%M%SZ)-$$"
install -d -m 700 "$stamp"
[[ ! -f $cert ]] || cp -a -- "$cert" "$stamp/certificate"
[[ ! -f $key ]] || cp -a -- "$key" "$stamp/private-key"
nginx_was_active=0
if systemctl is-active --quiet nginx; then nginx_was_active=1; fi
restore_nginx() {
    if (( nginx_was_active )); then systemctl start nginx; fi
}
trap restore_nginx EXIT
if [[ -x /root/.acme.sh/acme.sh ]]; then
    # Existing ACME accounts, CA choice, home and renewal jobs remain intact.
    # The legacy account uses standalone HTTP-01, so stop only the known listener.
    systemctl stop nginx
    ecc_args=(--ecc)
    if [[ -f "/root/.acme.sh/${domain}_ecc/${domain}.conf" ]]; then
        /root/.acme.sh/acme.sh --renew -d "$domain" --ecc --force
    elif [[ -f "/root/.acme.sh/${domain}/${domain}.conf" ]]; then
        ecc_args=()
        /root/.acme.sh/acme.sh --renew -d "$domain" --force
    else
        /root/.acme.sh/acme.sh --issue -d "$domain" --standalone --keylength ec-256
    fi
    /root/.acme.sh/acme.sh --install-cert -d "$domain" "${ecc_args[@]}" --fullchain-file "$cert" --key-file "$key"
else
    # Fresh installations use the maintained distro ACME client; no remote shell bootstrap.
    [[ -n ${BLUEBLUE_ACME_EMAIL:-} ]] || read -rp 'ACME contact email: ' BLUEBLUE_ACME_EMAIL
    certbot certonly --webroot -w /home/vps/public_html -d "$domain" \
        --non-interactive --agree-tos --email "$BLUEBLUE_ACME_EMAIL"
    install -m 644 "/etc/letsencrypt/live/$domain/fullchain.pem" "$cert"
    install -m 600 "/etc/letsencrypt/live/$domain/privkey.pem" "$key"
    # One managed deploy hook; existing certbot hooks are preserved.
    install -d -m 755 /etc/letsencrypt/renewal-hooks/deploy
    cat > /etc/letsencrypt/renewal-hooks/deploy/blueblue <<'EOF'
#!/usr/bin/env bash
set -Eeuo pipefail
python3 /usr/local/lib/blueblue/domain_config.py deploy "$RENEWED_LINEAGE"
EOF
    chmod 755 /etc/letsencrypt/renewal-hooks/deploy/blueblue
fi
python3 /usr/local/lib/blueblue/domain_config.py activate
python3 /usr/local/lib/blueblue/stunnel.py
nginx -t
systemctl start nginx
systemctl reload nginx
echo "Certificate installed at the existing configured paths. Backup: $stamp"
