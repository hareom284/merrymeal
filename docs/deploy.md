# Production deploy — single-VPS Docker recipe

> Target: a fresh Ubuntu 24.04 VPS (e.g. Hetzner CX21, 2 vCPU / 4 GB RAM).
> Domain: **merrymeal.freebarcodeqr.com**.
> Time-to-live target: 30 minutes.
> On the server you only edit **two files**: `docker-compose.yml` (rarely)
> and `.env` (every config change). No prod-only compose overlay, no
> separate prod env template.

## 1. DNS — point the subdomain at the server

Wherever `freebarcodeqr.com` DNS is hosted (Cloudflare / Namecheap / cPanel),
add one record:

| Type | Name | Value | TTL | Proxy |
|---|---|---|---|---|
| `A` | `merrymeal` | _server IPv4_ | `300` | **DNS only** (no Cloudflare proxy) until certbot has issued the cert; flip to Proxied after if desired. |

Verify before touching the server:

```bash
dig +short merrymeal.freebarcodeqr.com   # must print the server IP
```

## 2. Provision the VPS

Create the VPS in your provider's UI. SSH in as root (or as a sudoer).

## 3. Install Docker

```bash
sudo apt update && sudo apt install -y ca-certificates curl gnupg
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu noble stable" \
  | sudo tee /etc/apt/sources.list.d/docker.list
sudo apt update && sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

## 4. Clone and configure

```bash
sudo mkdir -p /srv && cd /srv
sudo git clone <repo-url> merrymeal
cd merrymeal
sudo cp .env.example .env
sudo nano .env
```

In `.env`, set the prod-only values:

```dotenv
# Switch to prod settings — flips on HSTS, secure cookies, SSL redirect.
DJANGO_SETTINGS_MODULE=config.settings.prod

# Generate fresh: python3 -c "import secrets; print(secrets.token_urlsafe(50))"
DJANGO_SECRET_KEY=<paste output here>

DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=merrymeal.freebarcodeqr.com

# In-compose MySQL — container name is `mysql`, so HOST=mysql.
MYSQL_HOST=mysql
MYSQL_DATABASE=merrymeal
MYSQL_USER=merrymeal
MYSQL_PASSWORD=<strong password>
MYSQL_ROOT_PASSWORD=<another strong password>

REDIS_URL=redis://redis:6379/0

# Security knobs — all True in prod.
DJANGO_SECURE_SSL_REDIRECT=True
DJANGO_SESSION_COOKIE_SECURE=True
DJANGO_CSRF_COOKIE_SECURE=True
DJANGO_SECURE_HSTS_SECONDS=31536000
DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS=True
DJANGO_SECURE_HSTS_PRELOAD=True
```

Everything else in `.env.example` is fine to leave as the default.

## 5. Bring up the stack

```bash
sudo docker compose up -d --build
```

First build is 3–4 minutes. Once `docker compose ps` shows every service
healthy:

```bash
sudo docker compose run --rm web python manage.py createsuperuser
```

> **Port exposure.** `docker-compose.yml` publishes `8000:8000` on all
> interfaces. Step 6 closes that off with a firewall so port 8000 is only
> reachable from the host itself (Nginx). If you'd rather not run a
> firewall, edit the `ports` line in `docker-compose.yml` on the server
> to `"127.0.0.1:8000:8000"` and `docker compose up -d --force-recreate web`.

## 6. Firewall

Block direct access to port 8000 from the internet; leave SSH + HTTP + HTTPS open.

```bash
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw --force enable
sudo ufw status
```

## 7. Nginx + Let's Encrypt TLS

```bash
sudo apt install -y nginx certbot python3-certbot-nginx
sudo cp /srv/merrymeal/deploy/nginx.conf.example /etc/nginx/sites-available/merrymeal
sudo ln -sf /etc/nginx/sites-available/merrymeal /etc/nginx/sites-enabled/merrymeal
sudo rm -f /etc/nginx/sites-enabled/default
```

> The sample vhost references SSL cert paths certbot hasn't created yet —
> `nginx -t` will complain. The next step issues the cert and rewrites the
> vhost to use it.

```bash
sudo certbot --nginx -d merrymeal.freebarcodeqr.com \
  --redirect --agree-tos -m you@yourdomain.com --non-interactive
sudo nginx -t && sudo systemctl reload nginx
```

What certbot does:

- Solves the HTTP-01 challenge on port 80 (needs UFW step 6 already applied).
- Writes the cert to `/etc/letsencrypt/live/merrymeal.freebarcodeqr.com/`.
- Patches the vhost with cert paths + HTTP→HTTPS redirect.
- Installs a systemd timer for auto-renewal — confirm with
  `systemctl list-timers | grep certbot`.

## 8. Smoke test

From your laptop:

```bash
curl -I https://merrymeal.freebarcodeqr.com/accounts/login/
```

Expected: `HTTP/2 200` with a `strict-transport-security` header.

Open `https://merrymeal.freebarcodeqr.com/accounts/login/` in a browser — the mobile-first login page should render over HTTPS.

## 9. Verify Django's deploy checks

```bash
sudo docker compose run --rm web python manage.py check --deploy
```

Expected: 0 issues. Anything reported maps directly to a setting in `.env`
— fix and run `sudo docker compose up -d --force-recreate web`.

## Daily ops

- **Pull updates:**
  ```bash
  cd /srv/merrymeal && sudo git pull && sudo docker compose up -d --build
  ```
- **Tail logs:** `sudo docker compose logs -f web worker`
- **Restart after `.env` change:** `sudo docker compose up -d --force-recreate web worker`
- **DB backup:** see Story 7.8 (Epic 07) for the nightly backup script.

## What's NOT in this recipe (and why)

- **Managed MySQL.** Use it once the charity scales beyond ~500 members; the
  docker MySQL service is fine for v1.
- **CDN / WAF.** Add once Story 5.4 (Stripe) is live and donor traffic
  justifies it.
- **Multi-VPS / load balancer.** Out of scope until uptime SLAs are signed.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `dig` returns nothing | DNS not propagated | Wait 5–60 min; check at `dnschecker.org`. |
| `certbot` fails — "connection refused" on 80 | UFW or Cloudflare proxy blocking port 80 | `sudo ufw status` (allow 80/tcp); set the Cloudflare record to "DNS only". |
| `502 Bad Gateway` from nginx | `web` container down or healthcheck not green | `sudo docker compose ps`; `sudo docker compose logs web`. |
| `Bad Request (400)` after deploy | `DJANGO_ALLOWED_HOSTS` doesn't list `merrymeal.freebarcodeqr.com` | Edit `.env`, `sudo docker compose up -d --force-recreate web`. |
| `Mixed content` warnings in browser | Nginx not forwarding `X-Forwarded-Proto` | Confirm `proxy_set_header X-Forwarded-Proto $scheme;` is in the vhost (the sample includes it). |
| `web` keeps restarting with MySQL connection error | First-run MySQL still initialising | Wait ~30 s; `sudo docker compose logs mysql` should show "ready for connections". |
