# Twitch Channel Points Miner v2

A Python bot that watches Twitch streams on your behalf and earns [channel points](https://help.twitch.tv/s/article/channel-points-guide): watch time, claim bonuses, follow raids, place predictions, claim drops, and more.

This repository is a fork of [rdavydov/Twitch-Channel-Points-Miner-v2](https://github.com/rdavydov/Twitch-Channel-Points-Miner-v2), which continues development from [Tkd-Alex/Twitch-Channel-Points-Miner-v2](https://github.com/Tkd-Alex/Twitch-Channel-Points-Miner-v2).

## Features

- **Passive earning**: watch time, stream-start bonuses (+450), claim buttons (+50), raid follows (+250), watch streaks
- **Predictions**: configurable bet strategies, filters, delays, and stealth mode
- **Drops & moments**: progress toward drop campaigns and claim [Moments](https://help.twitch.tv/s/article/moments) when available
- **Smart prioritization**: watch streaks, drops, subscription tier, channel point balance, or your streamer list order
- **Follower list mining**: optionally load your followed channels automatically
- **IRC chat presence**: join chat to improve watch-time tracking and detect `@mentions`
- **Analytics dashboard**: optional Flask chart of point gains over time
- **Notifications**: Telegram, Discord, generic webhooks, Matrix, Pushover, and Gotify
- **Structured logging**: colored console output, log files, session summaries, and emoji support (disable on Windows if needed)

## Requirements

- Python 3.12+
- A Twitch account

## Quick start

```sh
git clone https://github.com/combwizard/Twitch-Channel-Points-Miner-v2.git
cd Twitch-Channel-Points-Miner-v2
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp config.example.yaml config.yaml   # edit username and streamers
python -m TwitchChannelPointsMiner

# Optional: use a config file outside the repo
CONFIG_PATH=/path/to/config.yaml python -m TwitchChannelPointsMiner
```

On first run you will be prompted to log in unless a cookie file already exists in `cookies/`.

### Minimal configuration

Copy [`config.example.yaml`](config.example.yaml) to `config.yaml` and set your username and streamers:

```yaml
username: your-twitch-username
streamers:
  - streamer1
  - streamer2
```

Advanced options (bet strategies, notifications, per-streamer overrides) are still configured in Python via [`example.py`](example.py). You can also use the programmatic API directly:

```python
from TwitchChannelPointsMiner import TwitchChannelPointsMiner

miner = TwitchChannelPointsMiner("your-twitch-username")
miner.mine(["streamer1", "streamer2"])
```

See [`config.example.yaml`](config.example.yaml) for all YAML options (Hermes, priorities, logger, analytics, streamer defaults).

## How it works

The miner connects to Twitch over GraphQL, real-time WebSockets (Hermes by default), and IRC. It tracks which streamers are live, watches up to **two channels at a time** (a Twitch limit), and performs configured actions for each active stream.

Twitch shut down the legacy PubSub WebSocket API in April 2025. This fork includes the [Hermes WebSocket integration](https://github.com/rdavydov/Twitch-Channel-Points-Miner-v2/pull/728) from upstream PR #728. **`use_hermes=True` is the default.** Set `use_hermes=False` only if you still need the old PubSub transport for testing.

Streamer priority is controlled by the `priority` setting and the order of your streamer list. When using `followers=True`, channels can be sorted by follow date (`FollowersOrder.ASC` or `DESC`). Use `blacklist=[...]` to exclude specific channels from a follower-based list.

When `STREAK` is in your priority list and more than two streamers are live, the miner watches two channels at a time. Once a watched channel finishes its streak window (~7 minutes of watch time), that slot is given to the next online streamer that still needs streak progress instead of staying on a channel that no longer needs it.

## Configuration reference

Settings can be defined in `config.yaml` (recommended) or in Python when constructing `TwitchChannelPointsMiner`. Bet strategies, notifications, and per-streamer Python objects remain in [`example.py`](example.py).

### YAML layout

| Section | Purpose |
| --- | --- |
| `username` | Twitch login name (required) |
| `password` | Optional; omit to use TV device login on first run |
| `miner` | Hermes, priorities, analytics collection, SSL, `@` matching |
| `logger` | Console/file logging, rotation, emoji, colors |
| `streamer_settings` | Defaults applied to every streamer |
| `analytics` | Optional Flask dashboard (`enabled`, host, port, refresh) |
| `streamers` | Channel login names to mine (list order matters) |
| `mine` | Follower list mode, sort order, blacklist |

Example mapping: Python `use_hermes=True` → YAML `miner.use_hermes: true`. Python `Priority.STREAK` → YAML `miner.priority: [streak, drops, order]` (case-insensitive).

When using the Python API alongside YAML, settings resolve in this order (highest wins):

1. Per-streamer settings passed to `mine()`
2. `StreamerSettings` on the `TwitchChannelPointsMiner` instance
3. Built-in defaults

### TwitchChannelPointsMiner options

| Key | Type | Default | Description |
| --- | --- | --- | --- |
| `use_hermes` | bool | `True` | Use the Hermes WebSocket API instead of legacy PubSub |
| `enable_analytics` | bool | `False` | Collect point history for the analytics dashboard |
| `claim_drops_startup` | bool | `False` | Claim all inventory drops when the miner starts |
| `disable_ssl_cert_verification` | bool | `False` | Disable TLS verification (use only to work around cert errors) |
| `disable_at_in_nickname` | bool | `False` | Match chat mentions without a leading `@` |
| `priority` | list | `[STREAK, DROPS, ORDER]` | Streamer selection order when multiple are live |

### Priority values

| Value | Behavior |
| --- | --- |
| `STREAK` | Catch watch-streak bonuses first; frees watch slots when a channel no longer needs streak progress |
| `DROPS` | Prioritize streamers with active drop campaigns |
| `SUBSCRIBED` | Prioritize subscribed channels (higher tiers first) |
| `ORDER` | Follow the streamer list order |
| `POINTS_ASCENDING` | Lowest balance first |
| `POINTS_DESCENDING` | Highest balance first |

Combine priorities as needed. Include at least one of `ORDER`, `POINTS_ASCENDING`, or `POINTS_DESCENDING` so the miner keeps watching after streaks and drops are handled.

### `mine` options (YAML)

| Key | Type | Default | Description |
| --- | --- | --- | --- |
| `followers` | bool | `false` | Load your Twitch follow list instead of `streamers` |
| `followers_order` | str | `asc` | `asc` or `desc` by follow date when `followers` is true |
| `blacklist` | list | `[]` | Usernames to skip (also applies to the followers list) |

### StreamerSettings

| Key | Type | Default | Description |
| --- | --- | --- | --- |
| `make_predictions` | bool | `True` | Place channel-point predictions |
| `follow_raid` | bool | `True` | Follow raids for bonus points |
| `claim_drops` | bool | `True` | Count watch time toward drop campaigns |
| `claim_moments` | bool | `True` | Claim Moments when available |
| `watch_streak` | bool | `True` | Prioritize channels with an active watch streak |
| `community_goals` | bool | `False` | Contribute max points to community goals |
| `chat` | `ChatPresence` | `ONLINE` | IRC presence: `ALWAYS`, `NEVER`, `ONLINE`, `OFFLINE` |
| `bet` | `BetSettings` | - | Prediction behavior (see below) |

### BetSettings

| Key | Type | Default | Description |
| --- | --- | --- | --- |
| `strategy` | `Strategy` | `SMART` | Outcome selection strategy |
| `percentage` | int | `5` | Bet this % of your balance |
| `percentage_gap` | int | `20` | Gap threshold for `SMART` strategy |
| `max_points` | int | `50000` | Cap on bet size |
| `minimum_points` | int | `0` | Skip bets below this balance |
| `stealth_mode` | bool | `False` | Bet just under the current leader |
| `delay_mode` | `DelayMode` | `FROM_END` | How `delay` is interpreted |
| `delay` | float | `6` | Seconds or fraction (see below) |
| `filter_condition` | `FilterCondition` | `None` | Optional gate before placing a bet |

**Strategies:** `MOST_VOTED`, `HIGH_ODDS`, `PERCENTAGE`, `SMART_MONEY`, `SMART`, `NUMBER_1` … `NUMBER_8`

**Delay modes:**

- `FROM_START`: wait `delay` seconds after the prediction opens
- `FROM_END`: place the bet `delay` seconds before it closes
- `PERCENTAGE`: place when `delay` fraction of the timer has elapsed (e.g. `0.2` = 20%)

**FilterCondition**: gate bets with `by` (`TOTAL_USERS`, `TOTAL_POINTS`, `ODDS`, `PERCENTAGE_USERS`, `ODDS_PERCENTAGE`, `TOP_POINTS`), `where` (`GT`, `LT`, `GTE`, `LTE`), and `value`.

### LoggerSettings

| Key | Type | Default | Description |
| --- | --- | --- | --- |
| `save` | bool | `True` | Write logs to `logs/` |
| `console_level` | level | `INFO` | Terminal verbosity |
| `file_level` | level | `DEBUG` | File verbosity |
| `less` | bool | `False` | Compact log format |
| `colored` | bool | `True` | ANSI colors in terminal |
| `emoji` | bool | platform | Disable on Windows if output breaks |
| `console_username` | bool | `False` | Prefix lines with account name |
| `auto_clear` | bool | `True` | Rotate logs daily, keep 7 days |
| `time_zone` | str | `""` | tz database name, e.g. `America/Denver` |
| `color_palette` | `ColorPalette` | - | Per-event terminal colors |
| `telegram` / `discord` / `webhook` / `matrix` / `pushover` / `gotify` | - | `None` | Optional notification backends |

**Notification events:** `STREAMER_ONLINE`, `STREAMER_OFFLINE`, `GAIN_FOR_RAID`, `GAIN_FOR_CLAIM`, `GAIN_FOR_WATCH`, `BET_WIN`, `BET_LOSE`, `BET_REFUND`, `BET_FILTERS`, `BET_GENERAL`, `BET_FAILED`, `BET_START`, `BONUS_CLAIM`, `MOMENT_CLAIM`, `JOIN_RAID`, `DROP_CLAIM`, `DROP_STATUS`, `CHAT_MENTION`

## Analytics

Enable the dashboard in `config.yaml`:

```yaml
analytics:
  enabled: true
  host: 127.0.0.1   # use 0.0.0.0 in Docker to reach from the host
  port: 5000
  refresh_seconds: 5   # dashboard poll interval in seconds
  days_ago: 7
```

Setting `analytics.enabled: true` also turns on data collection (`miner.enable_analytics`). Open `http://127.0.0.1:5000` while the miner is running.

Alternatively, enable collection and start the server from Python:

```python
miner = TwitchChannelPointsMiner("your-twitch-username", enable_analytics=True)
miner.analytics(host="127.0.0.1", port=5000, refresh_seconds=5, days_ago=7)
miner.mine(["streamer1", "streamer2"])
```

When analytics is disabled (default), memory and disk use are lower and no `analytics/*.json` files are written.

## Docker

Build from this repository or use a published image when available: `combwizard/twitch-channel-points-miner-v2`.

Mount your config and persistent data:

```yaml
# docker-compose.yml
services:
  miner:
    image: combwizard/twitch-channel-points-miner-v2
    stdin_open: true
    tty: true
    environment:
      - TERM=xterm-256color
      - CONFIG_PATH=/config/config.yaml
    volumes:
      - ./config.yaml:/config/config.yaml:ro
      - ./analytics:/usr/src/app/analytics
      - ./cookies:/usr/src/app/cookies
      - ./logs:/usr/src/app/logs
    ports:
      - "5000:5000"
```

Use `-it` for the first login when no cookie file exists yet. On Windows, use absolute paths instead of `$(pwd)`.

To build locally:

```sh
docker build -t combwizard/twitch-channel-points-miner-v2 .
```

## Session cookies

Login state is stored in `cookies/<username>.json`. Legacy pickle files (`cookies/<username>.pkl`) are loaded automatically and migrated to JSON on the next save.

```
.
├── config.yaml
└── cookies/
    └── your-twitch-username.json
```

If you see `ERR_BADAUTH` in the logs, delete the cookie file for that account and log in again.

**Do not commit cookie files.** They grant full access to your Twitch account.

## Platform notes

### Windows

Emoji in logs can cause encoding issues. Set `logger.emoji: false` in `config.yaml` (or `LoggerSettings(emoji=False)` in Python) if terminal output looks wrong.

### Termux (Android)

```sh
pkg upgrade
pkg install python git rust libjpeg-turbo libcrypt ndk-sysroot clang zlib binutils tur-repo python-cryptography python-pandas
git clone https://github.com/combwizard/Twitch-Channel-Points-Miner-v2.git
cd Twitch-Channel-Points-Miner-v2
cp config.example.yaml config.yaml && nano config.yaml
pip install -r requirements.txt
python -m TwitchChannelPointsMiner
```

If `cryptography` fails to build:

```sh
export RUSTFLAGS=" -C lto=no"
export CARGO_BUILD_TARGET="$(rustc -vV | sed -n 's|host: ||p')"
pip install cryptography
```

## Contributing

Pull requests are welcome. Read [CONTRIBUTING.md](CONTRIBUTING.md) before opening a PR. To report bugs, open an issue on [upstream](https://github.com/rdavydov/Twitch-Channel-Points-Miner-v2/issues) or contact the fork maintainer directly.

To sync with upstream:

```sh
git fetch upstream
git merge upstream/master
```

## Credits

| Project | Role |
| --- | --- |
| [gottagofaster236/Twitch-Channel-Points-Miner](https://github.com/gottagofaster236/Twitch-Channel-Points-Miner) | Original idea |
| [Tkd-Alex/Twitch-Channel-Points-Miner-v2](https://github.com/Tkd-Alex/Twitch-Channel-Points-Miner-v2) | v2 architecture and features |
| [rdavydov/Twitch-Channel-Points-Miner-v2](https://github.com/rdavydov/Twitch-Channel-Points-Miner-v2) | Active maintenance fork |

## Disclaimer

This project is not affiliated with Twitch. Use at your own risk. Automated activity may violate Twitch's terms of service and could lead to account restrictions. The authors provide no warranty.

Licensed under [GPLv3+](LICENSE).
