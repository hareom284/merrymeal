# Production deploy — pull-image recipe

> Target: a fresh Ubuntu 24.04 VPS (e.g. Hetzner CX21, 2 vCPU / 4 GB RAM).
> Domain: **merrymeal.freebarcodeqr.com**.
> Time-to-live target: 30 minutes.
> The server never `git clone`s. The only files it needs are **`docker-compose.yml`**, **`.env`**, and the Nginx vhost. The image comes from GHCR (built by the GitHub Actions `release` job on every push to `main`).

## How the image gets to the server

1. You push to `main` on GitHub.
2. The `release` job in `.github/workflows/ci.yml` builds the image and pushes
   `ghcr.io/hareom284/merrymeal:latest` (and a `:<commit-sha>` tag).
3. On the server, `docker compose pull && docker compose up -d` fetches and runs it.

> First-time setup needs the GHCR package to be public (or you must give the
> server a token). See **One-time: make the image public** below.

## 1. DNS — point the subdomain at the server

Wherever `freebarcodeqr.com` DNS is hosted, add one record:

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

## 4. Ship the two files to the server

You only ever copy two files to `/srv/merrymeal/`: **`docker-compose.yml`** and **`.env`**.

From your laptop:

```bash
ssh root@<server-ip> 'sudo mkdir -p /srv/merrymeal'
scp docker-compose.yml root@<server-ip>:/tmp/
cp .env.example .env.prod
# Edit .env.prod with the production values from the block below.
scp .env.prod root@<server-ip>:/tmp/.env
ssh root@<server-ip> 'sudo mv /tmp/docker-compose.yml /tmp/.env /srv/merrymeal/'
```

Or, if you'd rather just paste on the server:

```bash
# On the server.
sudo mkdir -p /srv/merrymeal && cd /srv/merrymeal
sudo nano docker-compose.yml   # paste contents of docker-compose.yml from the repo
sudo nano .env                 # paste the prod env values below
```

### Prod `.env` values

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

## 5. Pull and bring up the stack

```bash
cd /srv/merrymeal
sudo docker compose pull          # fetches ghcr.io/hareom284/merrymeal:latest + mysql:8 + redis:7-alpine
sudo docker compose up -d
sudo docker compose ps            # every service should be healthy within ~30 s
sudo docker compose logs -f web   # ctrl-c to detach
```

Create the first admin:

```bash
sudo docker compose run --rm web python manage.py createsuperuser
```

> Port 8000 is bound to `127.0.0.1:8000` in `docker-compose.yml`, so it's
> only reachable from the host itself — Nginx will proxy to it. Even
> without a firewall, the public internet can't hit the container directly.

## 6. Firewall

Second line of defence — block everything except SSH + HTTP + HTTPS:

```bash
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw --force enable
sudo ufw status
```

## 7. Nginx + Let's Encrypt TLS

Install:

```bash
sudo apt install -y nginx certbot python3-certbot-nginx
```

Write the vhost in one shot — no editor permission games:

```bash
sudo tee /etc/nginx/sites-available/merrymeal > /dev/null <<'EOF'
upstream merrymeal_web {
    server 127.0.0.1:8000 fail_timeout=0;
}

server {
    listen 80;
    server_name merrymeal.freebarcodeqr.com;

    client_max_body_size 25M;          # proof-of-delivery photos in Epic 04

    location / {
        proxy_pass http://merrymeal_web;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 30s;
    }
}
EOF

sudo ln -sf /etc/nginx/sites-available/merrymeal /etc/nginx/sites-enabled/merrymeal
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx
```

> No `/static/` or `/media/` aliases in this vhost. Django serves static
> files via Whitenoise from inside the container — no need to mount
> anything on the host.

Now run certbot — it solves the HTTP-01 challenge on port 80, issues the
cert, and **rewrites the vhost** with the HTTPS server block + auto-redirect:

```bash
sudo certbot --nginx -d merrymeal.freebarcodeqr.com \
  --redirect --agree-tos -m you@yourdomain.com --non-interactive
sudo nginx -t && sudo systemctl reload nginx
```

Auto-renewal is on by default — confirm with:

```bash
systemctl list-timers | grep certbot
```

## 8. Smoke test

From your laptop:

```bash
curl -I https://merrymeal.freebarcodeqr.com/accounts/login/
```

Expected: `HTTP/2 200` with a `strict-transport-security` header.

Open `https://merrymeal.freebarcodeqr.com/accounts/login/` in a browser.

## 9. Verify Django's deploy checks

```bash
sudo docker compose run --rm web python manage.py check --deploy
```

Expected: 0 issues. Anything reported maps directly to a setting in `.env`
— fix and `sudo docker compose up -d --force-recreate web`.

## Daily ops

- **Deploy a new release:**
  ```bash
  ssh root@<server-ip>
  cd /srv/merrymeal
  sudo docker compose pull
  sudo docker compose up -d
  ```
  Gunicorn workers are recreated; existing requests finish first.
- **Tail logs:** `sudo docker compose logs -f web worker`
- **Restart after `.env` change:** `sudo docker compose up -d --force-recreate web worker`
- **DB backup:** see Story 7.8 (Epic 07) for the nightly backup script.

## One-time: make the image public

After the first `release` job pushes successfully, the GHCR package starts
out **private**. The server can't pull a private image without a token.
The easiest fix is to make it public (appropriate for an open-source charity):

1. Open <https://github.com/hareom284/merrymeal/pkgs/container/merrymeal>
2. Right sidebar → "Package settings" → scroll to "Danger Zone" → "Change visibility" → **Public**.

If you'd rather keep it private, generate a fine-grained PAT with
`read:packages` and on the server:

```bash
echo "<YOUR_PAT>" | sudo docker login ghcr.io -u hareom284 --password-stdin
sudo docker compose pull   # now succeeds
```

## What's NOT in this recipe (and why)

- **Server-side `git clone`.** The server never has source code. Everything
  ships in the image.
- **Managed MySQL.** Use it once the charity scales beyond ~500 members.
- **CDN / WAF.** Add once Story 5.4 (Stripe) is live.
- **Multi-VPS / load balancer.** Out of scope until uptime SLAs are signed.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `docker compose pull` says `denied: name unknown` | Image not pushed yet, or repo name typo | Wait for the `release` job to go green; confirm GHCR URL. |
| `docker compose pull` says `unauthorized` | Package is private and server isn't logged in | Make package public, OR `docker login ghcr.io -u hareom284 -p <PAT>`. |
| `dig` returns nothing | DNS not propagated | Wait 5–60 min; check at `dnschecker.org`. |
| `certbot` fails — "connection refused" on 80 | UFW blocking 80, or Cloudflare proxy on | `sudo ufw status`; flip Cloudflare to "DNS only"; verify `dig` resolves. |
| `502 Bad Gateway` from nginx | `web` container not healthy | `sudo docker compose ps`; `sudo docker compose logs web`. |
| `400 Bad Request` after deploy | `DJANGO_ALLOWED_HOSTS` doesn't list the subdomain | Edit `.env`; `sudo docker compose up -d --force-recreate web`. |
| `web` restarts with MySQL connection error | First-run MySQL still initialising | Wait ~30 s; `sudo docker compose logs mysql` shows "ready for connections". |
| Static files (CSS/JS) 404 | `collectstatic` didn't run | `sudo docker compose logs web | grep collectstatic`; manually `sudo docker compose run --rm web python manage.py collectstatic --noinput`. |
