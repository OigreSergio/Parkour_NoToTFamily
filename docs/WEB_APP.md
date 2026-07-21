# Web app (PWA) strategy

The Flutter client also targets the **web**, so the same codebase ships as an
installable Progressive Web App. This is the zero-cost distribution channel:
no store fees, no 15–30% commission on payments, and every spot can be shared
as a plain URL.

## Why web-first

| | Stores (Play/App Store) | Web/PWA |
| --- | --- | --- |
| Up-front cost | $25 one-off (Google) + €99/year (Apple) | €0 |
| Cut on revenue | 15–30% | 0% (bank transfer) / ~3% (PSP) |
| Install friction | download required | open a link; optional "Add to Home Screen" |
| Shareability | store page only | deep links to any spot/page |
| Discoverability | store search | SEO + social links |

Recommended path: launch web/PWA first, grow through the community
(shareable spot links, social clips, local SEO), then publish to Play Store
once there is traction.

## Build & deploy

```bash
cd mobile
flutter build web --release --dart-define=API_BASE_URL=https://api.your-domain.example
```

`build/web/` is fully static — host it for free on Cloudflare Pages, GitHub
Pages, Netlify or Vercel. The backend (FastAPI) still needs a host (free tiers
of Render/Fly.io work; add the site origin to `CORS_ORIGINS` in the backend
`.env`).

The PWA bits live in `mobile/web/`:

- `manifest.json` — name, theme colour, icons; makes the app installable.
- `icons/` — placeholder icons (regenerate with real branding before launch).
- `index.html` — Flutter bootstrap + iOS home-screen meta tags.

## Payments / donations

Store billing does not apply on the web. The Support tab shows bank-transfer
(SEPA) coordinates served by `GET /api/v1/payments/bank-details`.

The IBAN and beneficiary are **never committed to this (public) repository**:
the endpoint reads them from environment variables, set only on the deployed
backend (see `backend/.env.example`):

```
PAYMENTS_BENEFICIARY=…
PAYMENTS_IBAN=…
PAYMENTS_BIC=…            # optional
PAYMENTS_TRANSFER_NOTE=…  # optional
```

Until they are set, the endpoint answers 404 and the Support tab shows a
"not set up yet" message, so the feature is safe to ship unconfigured.

If volumes ever justify it, swap/augment the bank transfer with a PSP
(Stripe/PayPal) — those keep bank coordinates in their own dashboard, and the
Support screen can grow "Pay with…" buttons alongside the IBAN card.
