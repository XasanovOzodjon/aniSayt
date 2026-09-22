#!/usr/bin/env bash
set -euo pipefail
# VPS: sudo DOMAIN=animee.uz APP_DIR=/opt/animee bash deploy/setup-nginx.sh

DOMAIN="${DOMAIN:-animee.uz}"
APP_DIR="${APP_DIR:-/opt/animee}"
EMAIL="${TLS_EMAIL:-admin@$DOMAIN}"
SRC="$(cd "$(dirname "$0")/.." && pwd)"
CONF_DST="/etc/nginx/sites-available/animee"

if [[ "$(id -u)" -ne 0 ]]; then
  echo "root bilan ishga tushiring: sudo DOMAIN=$DOMAIN bash deploy/setup-nginx.sh"
  exit 1
fi

apt-get update -y
DEBIAN_FRONTEND=noninteractive apt-get install -y nginx certbot python3-certbot-nginx
install -d /var/www/certbot
install -d "$APP_DIR/staticfiles"

render() {
  local src="$1"
  sed -e "s/DOMAIN_NAME/${DOMAIN}/g" -e "s|APP_DIR|${APP_DIR}|g" -e "s|/opt/animee|${APP_DIR}|g" "$src"
}

if [[ -f "/etc/letsencrypt/live/${DOMAIN}/fullchain.pem" ]]; then
  render "$SRC/deploy/nginx/animee.conf" > "$CONF_DST"
else
  render "$SRC/deploy/nginx/animee.http.conf" > "$CONF_DST"
fi

ln -sfn "$CONF_DST" /etc/nginx/sites-enabled/animee
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl reload nginx

if [[ ! -f "/etc/letsencrypt/live/${DOMAIN}/fullchain.pem" ]]; then
  certbot certonly --webroot -w /var/www/certbot \
    -d "$DOMAIN" -d "www.$DOMAIN" \
    --agree-tos --non-interactive --email "$EMAIL" || true
fi

if [[ -f "/etc/letsencrypt/live/${DOMAIN}/fullchain.pem" ]]; then
  render "$SRC/deploy/nginx/animee.conf" > "$CONF_DST"
  nginx -t
  systemctl reload nginx
  echo "HTTPS yoqildi: https://$DOMAIN"
else
  echo "Sertifikat hali yo'q. DNS $DOMAIN shu serverga qarasin, keyin qayta ishga tushiring."
fi

echo "Static: cd $APP_DIR && .venv/bin/python manage.py collectstatic --noinput"
echo "App: systemctl enable --now $(dirname "$0")/animee.service  (nusxani /etc/systemd/system/ ga qo'ying)"
