# Production deploy — single-VPS Docker recipe

> Target: a fresh Ubuntu 24.04 VPS (e.g. Hetzner CX21, 2 vCPU / 4 GB RAM).
> Time-to-live target: 30 minutes.

## 1. Provision

Create the VPS in your provider's UI. SSH in as root (or via a sudoer).

## 2. Install Docker

```bash
sudo apt update && sudo apt install -y ca-certificates curl gnupg
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu noble stable" \
  | sudo tee /etc/apt/sources.list.d/docker.list
sudo apt update && sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

Confirm Compose is v2.24+ (required for the `!reset` override syntax used
in `docker-compose.prod.yml`):

```bash
docker compose version
```

If older, either upgrade or remove the `ports: !reset []` line from
`docker-compose.prod.yml` and instead delete the `ports:` block in `docker-compose.yml`
when deploying to prod.

## 3. Clone and configure

```bash
sudo mkdir -p /srv && cd /srv
sudo git clone <repo-url> merrymeal
cd merrymeal
sudo cp .env.prod.example .env
sudo nano .env   # fill in real values
```

## 4. Bring up the stack

```bash
sudo docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

The first build takes 3–4 minutes. Once `docker compose ps` shows all
services healthy:

```bash
sudo docker compose run --rm web python manage.py createsuperuser
```

## 5. Reverse proxy + TLS

Install nginx + certbot:

```bash
sudo apt install -y nginx certbot python3-certbot-nginx
sudo cp /srv/merrymeal/deploy/nginx.conf.example /etc/nginx/sites-available/merrymeal
sudo nano /etc/nginx/sites-available/merrymeal   # replace YOUR_DOMAIN
sudo ln -s /etc/nginx/sites-available/merrymeal /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
sudo certbot --nginx -d YOUR_DOMAIN
```

Certbot adds the SSL block automatically and sets up auto-renewal.

## 6. Smoke test

From your laptop:

```bash
curl -I https://YOUR_DOMAIN/accounts/login/
```

Expected: `HTTP/2 200`, `strict-transport-security` header present.

## 7. Verify Django's deploy checks

```bash
sudo docker compose run --rm web python manage.py check --deploy
```

Expected: 0 issues. If any warning is reported, fix the corresponding
setting in `.env` and restart `web`.

## Daily ops

- **Pull updates:**
  `cd /srv/merrymeal && sudo git pull && sudo docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build`
- **Tail logs:** `sudo docker compose logs -f web worker`
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
| `502 Bad Gateway` from nginx | `web` container down or healthcheck not yet green | `docker compose ps` — restart `web`; check `docker compose logs web` for the migration error. |
| `Bad Request (400)` after deploy | `DJANGO_ALLOWED_HOSTS` doesn't include your domain | Edit `.env`, restart `web`. |
| `Mixed content` warnings in browser | `DJANGO_SECURE_SSL_REDIRECT` not enabled or nginx not forwarding `X-Forwarded-Proto` | Confirm `proxy_set_header X-Forwarded-Proto $scheme;` is present in nginx config. |
