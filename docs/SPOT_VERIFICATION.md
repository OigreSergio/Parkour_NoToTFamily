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

## Roles

Every account starts at the same level: sign-up always creates a plain
`user`. `instructor` is a qualification an admin can grant later (and revoke)
to members who qualify to teach — it adds recognition, not moderation power.
`admin` is reserved: it is the only role that can operate the web admin, and
there is deliberately no self-service or API path to obtain it.

| Ability                                  | Anonymous | User | Instructor | Admin |
| ---------------------------------------- | --------- | ---- | ---------- | ----- |
| Browse map / list of verified spots      | ✅        | ✅   | ✅         | ✅    |
| Read comments on a verified spot         | ✅        | ✅   | ✅         | ✅    |
| Comment on a verified spot               | —         | ✅   | ✅         | ✅    |
| Submit a spot (starts `pending`)         | —         | ✅   | ✅         | ✅    |
| Verify / reject submissions (web admin)  | —         | —    | —          | ✅    |
| Grant / revoke the instructor badge      | —         | —    | —          | ✅    |
| Become admin via API                     | —         | —    | —          | —     |

## Comments

Verified spots can be discussed: `GET /api/v1/spots/{id}/comments` is public
(the read-only spot page renders real comments), while posting requires an
authenticated account. Pending and rejected spots accept no comments — they
are not public, and comments would leak their existence.

## Endpoints

- `POST /api/v1/spots` — submit (status starts as `pending`).
- `GET /api/v1/spots/{id}/comments` — real comments on a verified spot (public).
- `POST /api/v1/spots/{id}/comments` — add a comment (authenticated).
- `GET /api/v1/admin/spots?status=pending` — admin queue.
- `POST /api/v1/admin/spots/{id}/verify` — approve.
- `POST /api/v1/admin/spots/{id}/reject` — reject with `{reason}`.
- `POST /api/v1/admin/users/{id}/role` — qualify a member as `instructor`
  or set them back to `user`; the `admin` role is never grantable here.

All admin actions are written to an audit log (`spot_moderation_events`).
