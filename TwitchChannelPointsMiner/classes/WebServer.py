import json
import logging
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from threading import Thread

import pandas as pd
from flask import Flask, Response, cli, jsonify, request, send_from_directory

from TwitchChannelPointsMiner.classes.Settings import Settings

cli.show_server_banner = lambda *_: None
logger = logging.getLogger(__name__)


def _assets_root():
    return os.path.join(Path().absolute(), "assets")


def _dist_folder():
    return os.path.join(_assets_root(), "dist")


def _analytics_json_path(streamer):
    base = os.path.realpath(Settings.analytics_path)
    stem = streamer[:-5] if streamer.endswith(".json") else streamer
    if not stem or os.path.basename(stem) != stem:
        return None

    candidate = os.path.realpath(os.path.join(base, f"{stem}.json"))
    try:
        if os.path.commonpath([base, candidate]) != base:
            return None
    except ValueError:
        return None

    if not os.path.isfile(candidate):
        return None
    return candidate


def filter_datas(start_date, end_date, datas):
    start_date = (
        datetime.strptime(start_date, "%Y-%m-%d").timestamp() * 1000
        if start_date is not None
        else 0
    )
    end_date = (
        datetime.strptime(end_date, "%Y-%m-%d")
        if end_date is not None
        else datetime.now()
    ).replace(hour=23, minute=59, second=59).timestamp() * 1000

    original_series = datas.get("series", [])

    if "series" in datas:
        df = pd.DataFrame(datas["series"])
        if not df.empty:
            df["datetime"] = pd.to_datetime(df.x // 1000, unit="s")
            df = df[(df.x >= start_date) & (df.x <= end_date)]
            datas["series"] = (
                df.drop(columns="datetime")
                .sort_values(by=["x", "y"], ascending=True)
                .to_dict("records")
            )
        else:
            datas["series"] = []
    else:
        datas["series"] = []

    if len(datas["series"]) == 0 and original_series:
        new_end_date = start_date
        new_start_date = 0
        df = pd.DataFrame(original_series)
        if not df.empty:
            df["datetime"] = pd.to_datetime(df.x // 1000, unit="s")
            df = df[(df.x >= new_start_date) & (df.x <= new_end_date)]
            filtered = df.drop(columns="datetime").sort_values(
                by=["x", "y"], ascending=True
            ).to_dict("records")
            if filtered:
                last_balance = filtered[-1]["y"]
                datas["series"] = [
                    {"x": start_date, "y": last_balance, "z": "No Stream"},
                    {"x": end_date, "y": last_balance, "z": "No Stream"},
                ]

    if "annotations" in datas and datas["annotations"]:
        df = pd.DataFrame(datas["annotations"])
        df["datetime"] = pd.to_datetime(df.x // 1000, unit="s")
        df = df[(df.x >= start_date) & (df.x <= end_date)]
        datas["annotations"] = (
            df.drop(columns="datetime")
            .sort_values(by="x", ascending=True)
            .to_dict("records")
        )
    else:
        datas["annotations"] = []

    return datas


def load_analytics_json(streamer, start_date=None, end_date=None):
    file_path = _analytics_json_path(streamer)
    if file_path is None:
        return None

    with open(file_path, "r", encoding="utf-8") as file:
        data = json.load(file)

    return filter_datas(start_date, end_date, data)


class WebServer(Thread):
    def __init__(
        self,
        miner,
        config_path: str = None,
        host: str = "127.0.0.1",
        port: int = 5000,
        refresh_seconds: int = 5,
        days_ago: int = 7,
        username: str = None,
    ):
        super().__init__()
        self.miner = miner
        self.config_path = config_path
        self.host = host
        self.port = port
        self.refresh_seconds = max(1, refresh_seconds)
        self.days_ago = days_ago
        self.username = username
        self._log_offsets = {}

        dist = _dist_folder()
        static_folder = dist if os.path.isdir(dist) else _assets_root()

        self.app = Flask(__name__, static_folder=static_folder, static_url_path="")

        self.app.add_url_rule("/api/status", "api_status", self.api_status, methods=["GET"])
        self.app.add_url_rule("/api/events", "api_events", self.api_events, methods=["GET"])
        self.app.add_url_rule(
            "/api/streamers", "api_add_streamer", self.api_add_streamer, methods=["POST"]
        )
        self.app.add_url_rule(
            "/api/streamers/<string:username>",
            "api_remove_streamer",
            self.api_remove_streamer,
            methods=["DELETE"],
        )
        self.app.add_url_rule(
            "/api/actions/claim-drops",
            "api_claim_drops",
            self.api_claim_drops,
            methods=["POST"],
        )
        self.app.add_url_rule(
            "/api/actions/shutdown",
            "api_shutdown",
            self.api_shutdown,
            methods=["POST"],
        )
        self.app.add_url_rule(
            "/api/analytics/<string:streamer>",
            "api_analytics",
            self.api_analytics,
            methods=["GET"],
        )
        self.app.add_url_rule("/api/logs", "api_logs", self.api_logs, methods=["GET"])
        self.app.add_url_rule("/api/meta", "api_meta", self.api_meta, methods=["GET"])
        self.app.add_url_rule("/", "spa_index", self.spa_index, methods=["GET"])
        self.app.add_url_rule("/<path:path>", "spa_catchall", self.spa_catchall, methods=["GET"])

    def api_meta(self):
        return jsonify({"days_ago": self.days_ago, "username": self.username})

    def api_status(self):
        return jsonify(self.miner.get_status_snapshot())

    def api_events(self):
        def generate():
            while self.miner.running:
                payload = json.dumps(self.miner.get_status_snapshot())
                yield f"data: {payload}\n\n"
                time.sleep(self.refresh_seconds)

        return Response(generate(), mimetype="text/event-stream")

    def api_add_streamer(self):
        body = request.get_json(silent=True) or {}
        username = body.get("username", "")
        try:
            persisted = self.miner.add_streamer(username)
            response = {"ok": True, "persisted": persisted}
            if not persisted:
                response["warning"] = (
                    "Streamer added for this session, but config.yaml could not be updated. "
                    "Check that the config volume is writable."
                )
            return jsonify(response), 201
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        except Exception as exc:
            logger.exception("Add streamer failed")
            return jsonify({"error": str(exc)}), 500

    def api_remove_streamer(self, username):
        try:
            persisted = self.miner.remove_streamer(username)
            response = {"ok": True, "persisted": persisted}
            if not persisted:
                response["warning"] = (
                    "Streamer removed for this session, but config.yaml could not be updated."
                )
            return jsonify(response)
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 404
        except Exception as exc:
            logger.exception("Remove streamer failed")
            return jsonify({"error": str(exc)}), 500

    def api_claim_drops(self):
        try:
            self.miner.twitch.claim_all_drops_from_inventory()
            return jsonify({"ok": True})
        except Exception as exc:
            logger.exception("Claim drops failed")
            return jsonify({"error": str(exc)}), 500

    def api_shutdown(self):
        self.miner.request_shutdown()
        return jsonify({"ok": True})

    def api_analytics(self, streamer):
        start_date = request.args.get("startDate", type=str)
        end_date = request.args.get("endDate", type=str)

        if not start_date and not end_date:
            end = datetime.now().date()
            start = end - timedelta(days=self.days_ago)
            start_date = start.isoformat()
            end_date = end.isoformat()

        data = load_analytics_json(streamer, start_date, end_date)
        if data is None:
            return jsonify({"error": f"No analytics for {streamer}"}), 404
        return jsonify(data)

    def api_logs(self):
        since = int(request.args.get("since", 0))
        logs_path = os.path.join(Path().absolute(), "logs")
        log_file_path = os.path.join(logs_path, f"{self.username}.log")

        try:
            with open(log_file_path, "r", encoding="utf-8") as log_file:
                log_content = log_file.read()
        except FileNotFoundError:
            return jsonify({"text": "", "next_since": since})

        chunk = log_content[since:]
        return jsonify({"text": chunk, "next_since": len(log_content)})

    def spa_index(self):
        return self._serve_spa("index.html")

    def spa_catchall(self, path):
        if path.startswith("api/"):
            return jsonify({"error": "Not found"}), 404
        dist = _dist_folder()
        file_path = os.path.join(dist, path)
        if os.path.isfile(file_path):
            return send_from_directory(dist, path)
        return self._serve_spa("index.html")

    def _serve_spa(self, filename):
        dist = _dist_folder()
        index_path = os.path.join(dist, filename)
        if os.path.isfile(index_path):
            return send_from_directory(dist, filename)
        return Response(
            "<html><body><h1>Web UI not built</h1>"
            "<p>Run <code>cd web && npm install && npm run build</code></p>"
            "</body></html>",
            status=503,
            mimetype="text/html",
        )

    def run(self):
        logger.info(
            f"Web UI running on http://{self.host}:{self.port}/",
            extra={"emoji": ":globe_with_meridians:"},
        )
        self.app.run(host=self.host, port=self.port, threaded=True, debug=False)
