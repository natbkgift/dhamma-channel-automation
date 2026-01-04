from __future__ import annotations

import pytest

from automation_core.dispatch.adapters.registry import DispatchAdapterError, get_adapter
from automation_core.dispatch.adapters.youtube import YoutubeAdapter
from automation_core.dispatch.adapters.youtube_community import YoutubeCommunityAdapter


def test_registry_resolves_youtube():
    adapter = get_adapter("youtube", "youtube")
    assert adapter.name == "youtube"


def test_registry_resolves_youtube_community():
    adapter = get_adapter("youtube_community", "youtube_community")
    assert adapter.name == "youtube_community"


def test_registry_unknown_target_raises_deterministic_error():
    with pytest.raises(DispatchAdapterError) as excinfo:
        get_adapter("line", "youtube_community")
    assert excinfo.value.code == "unknown_target"
    assert "unknown_target:" in excinfo.value.message


def test_youtube_adapter_build_actions_contract():
    adapter = YoutubeAdapter()
    actions = adapter.build_actions(
        short_bytes=5,
        long_bytes=7,
        publish_reason="dry_run default",
        target="youtube",
    )

    assert len(actions) == 3
    assert actions[0]["type"] == "print" and actions[0]["label"] == "short"
    assert actions[1]["type"] == "print" and actions[1]["label"] == "long"
    assert actions[2]["type"] == "noop" and actions[2]["label"] == "publish"

    assert actions[0]["bytes"] == 5
    assert actions[1]["bytes"] == 7
    assert actions[2]["reason"] == "dry_run default"

    assert actions[0]["adapter"] == "youtube"
    assert actions[0]["target"] == "youtube"


def test_youtube_community_adapter_build_actions_contract():
    adapter = YoutubeCommunityAdapter()
    actions = adapter.build_actions(
        short_bytes=5,
        long_bytes=7,
        publish_reason="dry_run default",
        target="youtube_community",
    )

    assert len(actions) == 3
    assert actions[0]["type"] == "print" and actions[0]["label"] == "short"
    assert actions[1]["type"] == "print" and actions[1]["label"] == "long"
    assert actions[2]["type"] == "noop" and actions[2]["label"] == "publish"

    assert actions[0]["bytes"] == 5
    assert actions[1]["bytes"] == 7
    assert actions[2]["reason"] == "dry_run default"

    assert actions[0]["adapter"] == "youtube_community"
    assert actions[0]["target"] == "youtube_community"
