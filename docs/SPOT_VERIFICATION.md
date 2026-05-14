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

## Endpoints

- `POST /api/v1/spots` — submit (status starts as `pending`).
- `GET /api/v1/admin/spots?status=pending` — admin queue.
- `POST /api/v1/admin/spots/{id}/verify` — approve.
- `POST /api/v1/admin/spots/{id}/reject` — reject with `{reason}`.

All admin actions are written to an audit log (`spot_moderation_events`).
