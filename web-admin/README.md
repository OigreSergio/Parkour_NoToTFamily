# Web admin

Internal Next.js dashboard for verifying user-submitted spots and managing videos.

## Run

```bash
npm install
npm run dev
# open http://localhost:3000
```

Set `NEXT_PUBLIC_API_URL` to point at the backend (defaults to `http://localhost:8000`).

## Pages

- `/login` — admin sign-in (uses the same `/api/v1/auth/login` endpoint; the API enforces admin role on `/admin/*`).
- `/spots` — pending-spot queue. **Verify** or **Reject (with reason)** per spot.

## Add later

- Spot detail page with embedded map.
- Videos CRUD.
- Audit log viewer (`spot_moderation_events`).
- Server-side session cookies (currently uses `localStorage` for simplicity).
