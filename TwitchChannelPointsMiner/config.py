import logging
import os

import yaml

from TwitchChannelPointsMiner import TwitchChannelPointsMiner
from TwitchChannelPointsMiner.classes.Chat import ChatPresence
from TwitchChannelPointsMiner.classes.Settings import FollowersOrder, Priority
from TwitchChannelPointsMiner.classes.entities.Streamer import StreamerSettings
from TwitchChannelPointsMiner.logger import LoggerSettings


def _enum_value(name, enum_cls):
    if name is None:
        return None
    if isinstance(name, enum_cls):
        return name
    return enum_cls[str(name).upper()]


def _log_level(name):
    if name is None:
        return None
    if isinstance(name, int):
        return name
    return getattr(logging, str(name).upper())


def _build_logger_settings(data):
    if not data:
        return LoggerSettings()

    kwargs = {}
    for key in (
        "save",
        "less",
        "console_username",
        "time_zone",
        "emoji",
        "colored",
        "auto_clear",
    ):
        if key in data:
            kwargs[key] = data[key]
    for key in ("console_level", "file_level"):
        if key in data:
            kwargs[key] = _log_level(data[key])
    return LoggerSettings(**kwargs)


def _build_streamer_settings(data):
    if not data:
        return StreamerSettings()

    kwargs = {}
    for key in (
        "make_predictions",
        "follow_raid",
        "claim_drops",
        "claim_moments",
        "watch_streak",
        "community_goals",
    ):
        if key in data:
            kwargs[key] = data[key]
    if "chat" in data:
        kwargs["chat"] = _enum_value(data["chat"], ChatPresence)
    return StreamerSettings(**kwargs)


def get_config_path(path=None):
    return path or os.environ.get("CONFIG_PATH", "config.yaml")


def load_config(path=None):
    path = get_config_path(path)
    with open(path, encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    if not raw or not raw.get("username"):
        raise ValueError(f"{path}: 'username' is required")
    return raw


def update_streamers_list(path, usernames):
    path = get_config_path(path)
    with open(path, encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}
    cfg["streamers"] = [u.lower().strip() for u in usernames]
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(cfg, f, default_flow_style=False, sort_keys=False)


def _analytics_refresh_seconds(analytics_cfg):
    if "refresh_seconds" in analytics_cfg:
        return analytics_cfg["refresh_seconds"]
    if "refresh" in analytics_cfg:
        # Legacy key was documented as chart interval in minutes
        return max(1, int(analytics_cfg["refresh"]) * 60)
    return 5


def run_from_config(path=None):
    path = get_config_path(path)
    cfg = load_config(path)
    miner_cfg = cfg.get("miner", {})
    analytics_cfg = cfg.get("analytics", {})
    priority = [
        _enum_value(p, Priority)
        for p in miner_cfg.get("priority", ["STREAK", "DROPS", "ORDER"])
    ]

    enable_analytics = miner_cfg.get("enable_analytics", False)
    if analytics_cfg.get("enabled", False):
        enable_analytics = True

    miner = TwitchChannelPointsMiner(
        username=cfg["username"],
        password=cfg.get("password"),
        claim_drops_startup=miner_cfg.get("claim_drops_startup", False),
        enable_analytics=enable_analytics,
        disable_ssl_cert_verification=miner_cfg.get(
            "disable_ssl_cert_verification", False
        ),
        disable_at_in_nickname=miner_cfg.get("disable_at_in_nickname", False),
        use_hermes=miner_cfg.get("use_hermes", True),
        priority=priority,
        logger_settings=_build_logger_settings(cfg.get("logger")),
        streamer_settings=_build_streamer_settings(cfg.get("streamer_settings")),
    )

    if analytics_cfg.get("enabled", False):
        miner.config_path = path
        miner.analytics(
            host=analytics_cfg.get("host", "127.0.0.1"),
            port=analytics_cfg.get("port", 5000),
            days_ago=analytics_cfg.get("days_ago", 7),
            config_path=path,
            refresh_seconds=_analytics_refresh_seconds(analytics_cfg),
        )

    mine_cfg = cfg.get("mine", {})
    miner.mine(
        streamers=cfg.get("streamers", []),
        blacklist=mine_cfg.get("blacklist", []),
        followers=mine_cfg.get("followers", False),
        followers_order=_enum_value(
            mine_cfg.get("followers_order", "ASC"), FollowersOrder
        ),
    )
