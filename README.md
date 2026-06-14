# Twitch Channel Points Miner v2

A Python bot that watches Twitch streams on your behalf and earns [channel points](https://help.twitch.tv/s/article/channel-points-guide): watch time, bonuses, raids, predictions, drops, and more.

Fork of [rdavydov/Twitch-Channel-Points-Miner-v2](https://github.com/rdavydov/Twitch-Channel-Points-Miner-v2) (continuing [Tkd-Alex/Twitch-Channel-Points-Miner-v2](https://github.com/Tkd-Alex/Twitch-Channel-Points-Miner-v2)).

## Contents

- [Quick start](#quick-start)
- [Web UI](#web-ui)
- [Configuration](#configuration)
- [Docker](#docker)
- [Troubleshooting](#troubleshooting)

## Quick start

**Requirements:** Python 3.12+, a Twitch account.

```sh
git clone https://github.com/combwizard/Twitch-Channel-Points-Miner-v2.git
cd Twitch-Channel-Points-Miner-v2
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp config.example.yaml config.yaml   # edit username and streamers
python -m TwitchChannelPointsMiner
```

On first run you will be prompted to log in unless `cookies/<username>.json` already exists.

Minimal `config.yaml`:

```yaml
username: your-twitch-username
streamers:
  - streamer1
  - streamer2
```

Custom config path:

```sh
CONFIG_PATH=/path/to/config.yaml python -m TwitchChannelPointsMiner
```

### What it does

The miner connects over GraphQL, Hermes WebSockets (default), and IRC. It watches up to **two live channels at a time** (a Twitch limit) and runs configured actions (claims, raids, predictions, drops).

Hermes replaced legacy PubSub in 2025. **`use_hermes: true` is the default** in `config.yaml`.

For bet strategies, notifications, and per-streamer Python objects, see [`example.py`](example.py).

## Web UI

Optional browser dashboard at `http://127.0.0.1:5000` when analytics is enabled:

```yaml
analytics:
  enabled: true
  host: 127.0.0.1   # use 0.0.0.0 in Docker
  port: 5000
  refresh_seconds: 5
  days_ago: 7
```

`analytics.enabled: true` also turns on point history collection. The UI shows live streamer status, session gains, charts, logs, and lets you add/remove streamers, claim drops, and stop the miner.

**Build the frontend** (only needed for local dev outside Docker):

```sh
cd web && npm install && npm run build
```

For frontend hot reload during development: `cd web && npm run dev` (proxies `/api` to port 5000).

There is no authentication on the Web UI. Bind to `127.0.0.1` or protect port 5000 at the network layer.

## Configuration

| What you need | Where to look |
| --- | --- |
| Everyday settings (username, streamers, priorities, logger) | [`config.example.yaml`](config.example.yaml) |
| Full option reference (tables) | [`docs/configuration.md`](docs/configuration.md) |
| Predictions, notifications, Python API | [`example.py`](example.py) |

**Priority** controls which streamers get watched when several are live. Common values: `streak`, `drops`, `order`. See [docs/configuration.md](docs/configuration.md#priority-values) for the full list.

**Follower mode:** set `mine.followers: true` to load your follow list instead of `streamers`. Use `mine.blacklist` to skip channels.

## Docker

```sh
docker build -t combwizard/twitch-channel-points-miner-v2 .
```

Example `docker-compose.yml`:

```yaml
services:
  miner:
    image: combwizard/twitch-channel-points-miner-v2
    stdin_open: true
    tty: true
    restart: unless-stopped
    environment:
      - CONFIG_PATH=/config/config.yaml
    volumes:
      - ./config.yaml:/config/config.yaml
      - ./cookies:/usr/src/app/cookies
      - ./logs:/usr/src/app/logs
      - ./analytics:/usr/src/app/analytics
    ports:
      - "5000:5000"
```

Use `-it` on first run when no cookie file exists. Mount `config.yaml` **writable** if you use the Web UI to add or remove streamers.

## Troubleshooting

| Problem | Fix |
| --- | --- |
| `ERR_BADAUTH` in logs | Delete `cookies/<username>.json` and log in again |
| Garbled terminal emoji (Windows) | Set `logger.emoji: false` in `config.yaml` |
| Web UI add streamer fails | Ensure `config.yaml` mount is writable (not `:ro`) |
| Cookie security | Never commit `cookies/`; files grant full account access |

Login state is stored in `cookies/<username>.json`. Legacy `.pkl` files are migrated to JSON automatically.

### Termux (Android)

```sh
pkg install python git rust libjpeg-turbo libcrypt ndk-sysroot clang zlib binutils tur-repo python-cryptography python-pandas
git clone https://github.com/combwizard/Twitch-Channel-Points-Miner-v2.git
cd Twitch-Channel-Points-Miner-v2
cp config.example.yaml config.yaml && nano config.yaml
pip install -r requirements.txt
python -m TwitchChannelPointsMiner
```

If `cryptography` fails to build, see the [upstream Termux notes](https://github.com/rdavydov/Twitch-Channel-Points-Miner-v2#termux-android) or set `RUSTFLAGS=" -C lto=no"` before installing.

## Credits

| Project | Role |
| --- | --- |
| [gottagofaster236/Twitch-Channel-Points-Miner](https://github.com/gottagofaster236/Twitch-Channel-Points-Miner) | Original idea |
| [Tkd-Alex/Twitch-Channel-Points-Miner-v2](https://github.com/Tkd-Alex/Twitch-Channel-Points-Miner-v2) | v2 architecture |
| [rdavydov/Twitch-Channel-Points-Miner-v2](https://github.com/rdavydov/Twitch-Channel-Points-Miner-v2) | Active maintenance fork |

Personal fork: no PR expectations. See [CONTRIBUTING.md](CONTRIBUTING.md) if you want to fork and modify under GPLv3+.

## Disclaimer

This project is not affiliated with Twitch. Use at your own risk. Automated activity may violate Twitch's terms of service and could lead to account restrictions. The authors provide no warranty.

Licensed under [GPLv3+](LICENSE).
