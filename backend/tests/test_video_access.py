from datetime import UTC, datetime
from uuid import uuid4

from app.models.user import User, UserRole
from app.models.video import TrickCategory, Video, VideoCategory, VideoLevel
from app.services import video_service


def _video(level: VideoLevel) -> Video:
    return Video(
        id=uuid4(),
        title="Kong",
        description="",
        url="https://videos.example/kong.mp4",
        thumbnail_url=None,
        category=VideoCategory.practice,
        level=level,
        trick_category=TrickCategory.vaults,
        difficulty=3,
        duration_seconds=90,
        created_at=datetime.now(UTC),
    )


def _user(*, guest: bool = False, subscribed: bool = False, role: UserRole = UserRole.user) -> User:
    return User(
        id=uuid4(),
        email=None if guest else "a@b.c",
        password_hash=None if guest else "x",
        display_name="T",
        role=role,
        is_guest=guest,
        is_subscribed=subscribed,
    )


def test_beginner_is_free_for_everyone() -> None:
    video = _video(VideoLevel.beginner)
    assert video_service.can_watch(video, None)  # anonymous
    assert video_service.can_watch(video, _user(guest=True))  # no-email guest
    assert video_service.can_watch(video, _user())  # registered, no sub


def test_premium_requires_subscription() -> None:
    for level in (VideoLevel.intermediate, VideoLevel.advanced):
        video = _video(level)
        assert not video_service.can_watch(video, None)
        assert not video_service.can_watch(video, _user(guest=True))
        assert not video_service.can_watch(video, _user())
        assert video_service.can_watch(video, _user(subscribed=True))
        assert video_service.can_watch(video, _user(role=UserRole.admin))


def test_locked_video_hides_url_but_stays_listed() -> None:
    out = video_service.to_out(_video(VideoLevel.advanced), _user(guest=True))
    assert out.locked
    assert out.is_premium
    assert out.url is None
    assert out.title == "Kong"  # metadata stays browsable
    assert out.difficulty == 3


def test_unlocked_video_keeps_url() -> None:
    out = video_service.to_out(_video(VideoLevel.beginner), None)
    assert not out.locked
    assert not out.is_premium
    assert out.url == "https://videos.example/kong.mp4"

    out = video_service.to_out(_video(VideoLevel.advanced), _user(subscribed=True))
    assert not out.locked
    assert out.is_premium
    assert out.url is not None
