#!/usr/bin/env bash
# MerryMeal — Stripe local testing helper.
#
# Wraps the `stripe` CLI for the donations flow so you don't have to
# remember the forward path / event names. Requires the Stripe CLI
# (`brew install stripe/stripe-cli/stripe`) and a one-time `stripe
# login` in this shell.
#
# Usage:
#   scripts/stripe_dev.sh dev             # run `stripe listen` + `manage.py runserver` together
#   scripts/stripe_dev.sh listen          # start the webhook forwarder only
#   scripts/stripe_dev.sh trigger success # simulate a successful one-off donation
#   scripts/stripe_dev.sh trigger renew   # simulate a monthly subscription invoice
#   scripts/stripe_dev.sh trigger cancel  # simulate a subscription cancellation
#   scripts/stripe_dev.sh card            # print the canonical test cards
#   scripts/stripe_dev.sh status          # show the latest Donation row state
#
# Run `listen` in one terminal and your Django dev server
# (`python manage.py runserver`) in another. The CLI prints
# `Your webhook signing secret is whsec_...` — paste that into
# STRIPE_WEBHOOK_SECRET in .env and restart runserver once.
set -euo pipefail

WEBHOOK_PATH=${WEBHOOK_PATH:-/stripe/webhook/}
HOST=${HOST:-localhost:8000}

need_cli() {
  if ! command -v stripe >/dev/null 2>&1; then
    echo "stripe CLI not found. Install with: brew install stripe/stripe-cli/stripe" >&2
    exit 1
  fi
}

cmd_listen() {
  need_cli
  echo "Forwarding Stripe events → http://${HOST}${WEBHOOK_PATH}"
  echo "Copy the whsec_... below into STRIPE_WEBHOOK_SECRET in .env"
  echo "------------------------------------------------------------"
  exec stripe listen --forward-to "${HOST}${WEBHOOK_PATH}"
}

cmd_trigger() {
  need_cli
  case "${1:-}" in
    success) stripe trigger checkout.session.completed ;;
    renew)   stripe trigger invoice.paid ;;
    cancel)  stripe trigger customer.subscription.deleted ;;
    *)
      echo "Usage: $0 trigger {success|renew|cancel}" >&2
      exit 2
      ;;
  esac
}

cmd_card() {
  cat <<'EOF'
Stripe test cards (any future expiry, any CVC, any ZIP):

  Succeeds:                    4242 4242 4242 4242
  Declined (insufficient):     4000 0000 0000 9995
  Requires 3-D Secure auth:    4000 0025 0000 3155
  Succeeds, then sub fails:    4000 0000 0000 0341
EOF
}

cmd_dev() {
  need_cli
  if ! command -v python3 >/dev/null 2>&1; then
    echo "python3 not found" >&2
    exit 1
  fi

  # `stripe listen` prints its banner (including the webhook secret) on
  # startup. The secret is stable per Stripe account once you've run
  # `stripe login`, so the value in .env should already match. We just
  # remind the operator if STRIPE_WEBHOOK_SECRET is unset.
  if [ -f .env ] && ! grep -qE '^STRIPE_WEBHOOK_SECRET=whsec_[A-Za-z0-9]+' .env; then
    echo "⚠️  STRIPE_WEBHOOK_SECRET in .env looks like a placeholder."
    echo "   Run \`scripts/stripe_dev.sh listen\` once, copy the whsec_..."
    echo "   it prints into .env, then re-run this command."
    echo
  fi

  # Track child PIDs so Ctrl+C tears down both processes cleanly. We
  # use a trap on EXIT so an unexpected death of one child also kills
  # the other — no orphaned `stripe listen` after a Django crash.
  pids=()
  cleanup() {
    for pid in "${pids[@]:-}"; do
      kill -TERM "$pid" 2>/dev/null || true
    done
    wait 2>/dev/null || true
  }
  trap cleanup EXIT INT TERM

  # Prefix each process's output so stripe events and Django log lines
  # are easy to tell apart in the shared terminal. `unbuffer` from the
  # `expect` package would be cleaner but we don't want to add a
  # dependency — `sed` line-buffering does the job.
  (stripe listen --forward-to "${HOST}${WEBHOOK_PATH}" 2>&1 | sed -u 's/^/[stripe] /') &
  pids+=($!)

  (python3 manage.py runserver 2>&1 | sed -u 's/^/[django] /') &
  pids+=($!)

  echo "Started stripe listen + runserver. Ctrl+C to stop both."
  wait
}

cmd_status() {
  python3 manage.py shell -c "
from apps.donations.models import Donation
qs = Donation.objects.order_by('-created_at')[:5]
if not qs:
    print('no donations yet')
else:
    for d in qs:
        print(f'{d.created_at:%Y-%m-%d %H:%M}  {d.status:10s}  \${d.amount_cents/100:>7.2f}  {d.donor_email}')
"
}

case "${1:-}" in
  dev)     cmd_dev ;;
  listen)  cmd_listen ;;
  trigger) shift; cmd_trigger "$@" ;;
  card)    cmd_card ;;
  status)  cmd_status ;;
  *)
    echo "Usage: $0 {dev|listen|trigger|card|status}" >&2
    echo "  dev      — run stripe listen + runserver together (Ctrl+C kills both)"
    echo "  listen   — forward Stripe webhooks to your local Django server"
    echo "  trigger  — fire a fake event (success|renew|cancel)"
    echo "  card     — print test card numbers"
    echo "  status   — show the latest Donation rows"
    exit 2
    ;;
esac
