# Spot verification

Every spot submitted by a user goes through review before appearing on the public map. This protects the community from unsafe, private, or fake locations.

## Lifecycle

```
   user submits spot
         │
         ▼
   status = pending  ── visible only to author and admins
         │
         ▼
   admin reviews in web admin
         │
   ┌─────┴──────┐
   ▼            ▼
verified     rejected
   │            │
   ▼            ▼
public map   author notified with reason
```

## Submitter sees

- Their own pending spots in "My submissions" with current status.
- Once verified, a push notification + the spot becomes visible on the map for everyone.
- If rejected, the rejection reason and a path to edit + resubmit.

## Admin sees

A queue ordered oldest-first, with:
- All photos at full size
- Lat/lng on an embedded map
- Submitter's history (how many spots verified vs. rejected)
- Buttons: **Verify**, **Reject (with reason)**, **Request changes**

## Rules to verify

A spot can be marked verified only if:
1. Photos clearly show a parkour-suitable obstacle or area.
2. Location is publicly accessible (no private property without owner consent).
3. Not a duplicate of an existing verified spot within 30 m.
4. No personally identifying info in description or photos.

Rule 1 is enforced by the API, not just by convention:
- a spot with **no photos cannot be verified** (422), and
- the verify call must carry an explicit attestation
  (`{"photos_real": true}`) that the admin looked at the photos and they
  show a real location. The web admin surfaces this as a checkbox that
  must be ticked before the **Verify** button activates, and the
  attestation is written to the audit log.

## Admin-created spots

Admins can also add spots directly (`POST /api/v1/admin/spots`, or the
**Add spot** form in the web admin). These skip the queue and are published
as `verified` immediately, with a `created_by_admin` audit event. Regular
users have no code path that produces a `verified` spot.

## Roles

| Ability                              | Anonymous | User | Admin |
| ------------------------------------ | --------- | ---- | ----- |
| Browse map / list of verified spots  | ✅        | ✅   | ✅    |
| Submit a spot (starts `pending`)     | —         | ✅   | ✅    |
| See own submissions + status         | —         | ✅   | ✅    |
| Verify / reject submissions          | —         | —    | ✅    |
| Create an already-verified spot      | —         | —    | ✅    |

The first admin account is seeded at API startup from
`INITIAL_ADMIN_EMAIL` / `INITIAL_ADMIN_PASSWORD`; there is deliberately no
self-service way to become admin.

## Endpoints

- `POST /api/v1/spots` — submit (status starts as `pending`).
- `GET /api/v1/spots/mine` — the caller's own submissions with status.
- `GET /api/v1/admin/spots?status=pending` — admin queue.
- `POST /api/v1/admin/spots` — admin creates an immediately-verified spot.
- `POST /api/v1/admin/spots/{id}/verify` — approve with
  `{photos_real: true, note?}`.
- `POST /api/v1/admin/spots/{id}/reject` — reject with `{reason}`.

All admin actions are written to an audit log (`spot_moderation_events`).
