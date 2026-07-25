"""Business rules for tutorial/video visibility.

The catalog is public: everyone — anonymous visitors, guest accounts signed in
without an email, and registered users — can browse every tutorial with its
title, thumbnail, difficulty and level. Watching is tiered:

- ``beginner`` videos are free for everyone, including guests and anonymous
  viewers.
- ``intermediate`` / ``advanced`` videos require an active subscription
  (``user.is_subscribed``). Admins can always watch.

Locked videos are still listed, but with ``url`` hidden and ``locked=True`` so
clients can render the paywall state.
"""

from app.models.user import User, UserRole
from app.models.video import Video, VideoLevel
from app.schemas.video import VideoOut


def is_premium(video: Video) -> bool:
    return video.level != VideoLevel.beginner


def can_watch(video: Video, user: User | None) -> bool:
    if not is_premium(video):
        return True
    if user is None:
        return False
    return user.is_subscribed or user.role == UserRole.admin


def to_out(video: Video, user: User | None) -> VideoOut:
    out = VideoOut.model_validate(video)
    out.is_premium = is_premium(video)
    out.locked = not can_watch(video, user)
    if out.locked:
        out.url = None
    return out
