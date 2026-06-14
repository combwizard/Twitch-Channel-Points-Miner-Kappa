# -*- coding: utf-8 -*-

import logging
import os
import random
import signal
import sys
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path

import TwitchChannelPointsMiner.classes.websocket.hermes.data as hermes_data
from TwitchChannelPointsMiner.classes.Chat import ChatPresence, ThreadChat
from TwitchChannelPointsMiner.classes.Exceptions import StreamerDoesNotExistException
from TwitchChannelPointsMiner.classes.PubSub import PubSubHandler
from TwitchChannelPointsMiner.classes.Settings import FollowersOrder, Priority, Settings
from TwitchChannelPointsMiner.classes.Twitch import Twitch
from TwitchChannelPointsMiner.classes.entities.EventPrediction import EventPrediction
from TwitchChannelPointsMiner.classes.entities.PubsubTopic import PubsubTopic
from TwitchChannelPointsMiner.classes.entities.Streamer import (
    Streamer,
    StreamerSettings,
)
from TwitchChannelPointsMiner.classes.websocket import HermesWebSocketPool, PubSubWebSocketPool
from TwitchChannelPointsMiner.constants import HERMES_WEBSOCKET, CLIENT_ID_WEB
from TwitchChannelPointsMiner.logger import LoggerSettings, configure_loggers
from TwitchChannelPointsMiner.utils import (
    _millify,
    at_least_one_value_in_settings_is,
    check_versions,
    get_user_agent,
    set_default_settings,
)

# Suppress:
#   - chardet.charsetprober - [feed]
#   - chardet.charsetprober - [get_confidence]
#   - requests - [Starting new HTTPS connection (1)]
#   - Flask (werkzeug) logs
#   - irc.client - [process_data]
#   - irc.client - [_dispatcher]
#   - irc.client - [_handle_message]
logging.getLogger("chardet.charsetprober").setLevel(logging.ERROR)
logging.getLogger("requests").setLevel(logging.ERROR)
logging.getLogger("werkzeug").setLevel(logging.ERROR)
logging.getLogger("irc.client").setLevel(logging.ERROR)
logging.getLogger("seleniumwire").setLevel(logging.ERROR)
logging.getLogger("websocket").setLevel(logging.ERROR)

logger = logging.getLogger(__name__)


class TwitchChannelPointsMiner:
    __slots__ = [
        "username",
        "twitch",
        "claim_drops_startup",
        "enable_analytics",
        "disable_ssl_cert_verification",
        "disable_at_in_nickname",
        "priority",
        "streamers",
        "events_predictions",
        "minute_watcher_thread",
        "sync_campaigns_thread",
        "ws_pool",
        "session_id",
        "running",
        "start_datetime",
        "original_streamers",
        "logs_file",
        "queue_listener",
        "config_path",
        "_control_lock",
    ]

    def __init__(
        self,
        username: str,
        password: str = None,
        claim_drops_startup: bool = False,
        enable_analytics: bool = False,
        disable_ssl_cert_verification: bool = False,
        disable_at_in_nickname: bool = False,
        # Settings for logging and selenium as you can see.
        priority: list = [Priority.STREAK, Priority.DROPS, Priority.ORDER],
        # This settings will be global shared trought Settings class
        logger_settings: LoggerSettings = LoggerSettings(),
        # Default values for all streamers
        streamer_settings: StreamerSettings = StreamerSettings(),
        # True if we want to use the new Hermes WebSocket API
        use_hermes: bool = True,
    ):
        # Fixes TypeError: 'NoneType' object is not subscriptable
        if not username or username == "your-twitch-username":
            logger.error("Please set username in config.yaml and try again.")
            logger.error("No username, exiting...")
            sys.exit(0)

        # This disables certificate verification and allows the connection to proceed, but also makes it vulnerable to man-in-the-middle (MITM) attacks.
        Settings.disable_ssl_cert_verification = disable_ssl_cert_verification

        Settings.disable_at_in_nickname = disable_at_in_nickname

        Settings.use_hermes = use_hermes

        import socket

        def is_connected():
            try:
                # resolve the IP address of the Twitch.tv domain name
                socket.gethostbyname("twitch.tv")
                return True
            except OSError:
                pass
            return False

        # check for Twitch.tv connectivity every 5 seconds
        error_printed = False
        while not is_connected():
            if not error_printed:
                logger.error("Waiting for Twitch.tv connectivity...")
                error_printed = True
            time.sleep(5)

        # Analytics switch
        Settings.enable_analytics = enable_analytics

        if enable_analytics is True:
            Settings.analytics_path = os.path.join(
                Path().absolute(), "analytics", username
            )
            Path(Settings.analytics_path).mkdir(parents=True, exist_ok=True)

        self.username = username

        # Set as global config
        Settings.logger = logger_settings

        # Init as default all the missing values
        streamer_settings.default()
        streamer_settings.bet.default()
        Settings.streamer_settings = streamer_settings

        # user_agent = get_user_agent("FIREFOX")
        user_agent = get_user_agent("CHROME")
        self.twitch = Twitch(self.username, user_agent, password)

        self.claim_drops_startup = claim_drops_startup
        self.priority = priority if isinstance(priority, list) else [priority]

        self.streamers: list[Streamer] = []
        self.events_predictions: dict[str, EventPrediction] = {}
        self.minute_watcher_thread = None
        self.sync_campaigns_thread = None
        self.ws_pool = None

        self.session_id = str(uuid.uuid4())
        self.running = False
        self.start_datetime = None
        self.original_streamers = []

        self.logs_file, self.queue_listener = configure_loggers(
            self.username, logger_settings
        )

        self.config_path = None
        self._control_lock = threading.RLock()

        # Check for the latest version of the script
        current_version, github_version = check_versions()

        logger.info(
            f"Twitch Channel Points Miner Kappa-{current_version}"
        )
        logger.info("https://github.com/combwizard/Twitch-Channel-Points-Miner-Kappa")

        if github_version == "0.0.0":
            logger.error(
                "Unable to detect if you have the latest version of this script"
            )
        elif current_version != github_version:
            logger.info(f"You are running version {current_version} of this script")
            logger.info(f"The latest version on GitHub is {github_version}")

        for sign in [signal.SIGINT, signal.SIGSEGV, signal.SIGTERM]:
            signal.signal(sign, self.end)

    def analytics(
        self,
        host: str = "127.0.0.1",
        port: int = 5000,
        days_ago: int = 7,
        config_path: str = None,
        refresh_seconds: int = 5,
    ):
        if Settings.enable_analytics is True:
            from TwitchChannelPointsMiner.classes.WebServer import WebServer

            days_ago = days_ago if days_ago <= 365 * 15 else 365 * 15
            http_server = WebServer(
                miner=self,
                config_path=config_path or self.config_path,
                host=host,
                port=port,
                refresh_seconds=refresh_seconds,
                days_ago=days_ago,
                username=self.username,
            )
            http_server.daemon = True
            http_server.name = "Web UI Thread"
            http_server.start()
        else:
            logger.error("Can't start analytics(), please set enable_analytics=True")

    def mine(
        self,
        streamers: list = [],
        blacklist: list = [],
        followers: bool = False,
        followers_order: FollowersOrder = FollowersOrder.ASC,
    ):
        self.run(streamers=streamers, blacklist=blacklist, followers=followers)

    def run(
        self,
        streamers: list = [],
        blacklist: list = [],
        followers: bool = False,
        followers_order: FollowersOrder = FollowersOrder.ASC,
    ):
        if self.running:
            logger.error("You can't start multiple sessions of this instance!")
        else:
            logger.info(
                f"Start session: '{self.session_id}'", extra={"emoji": ":bomb:"}
            )
            self.running = True
            self.start_datetime = datetime.now()

            self.twitch.login()

            if self.claim_drops_startup is True:
                self.twitch.claim_all_drops_from_inventory()

            streamers_name: list = []
            streamers_dict: dict = {}

            for streamer in streamers:
                username = (
                    streamer.username
                    if isinstance(streamer, Streamer)
                    else streamer.lower().strip()
                )
                if username not in blacklist:
                    streamers_name.append(username)
                    streamers_dict[username] = streamer

            if followers is True:
                followers_array = self.twitch.get_followers(order=followers_order)
                logger.info(
                    f"Load {len(followers_array)} followers from your profile!",
                    extra={"emoji": ":clipboard:"},
                )
                for username in followers_array:
                    if username not in streamers_dict and username not in blacklist:
                        streamers_name.append(username)
                        streamers_dict[username] = username.lower().strip()

            logger.info(
                f"Loading data for {len(streamers_name)} streamers. Please wait...",
                extra={"emoji": ":nerd_face:"},
            )
            for username in streamers_name:
                if username in streamers_name:
                    time.sleep(random.uniform(0.3, 0.7))
                    try:
                        streamer = (
                            streamers_dict[username]
                            if isinstance(streamers_dict[username], Streamer) is True
                            else Streamer(username)
                        )
                        streamer.channel_id = self.twitch.get_channel_id(username)
                        streamer.settings = set_default_settings(
                            streamer.settings, Settings.streamer_settings
                        )
                        streamer.settings.bet = set_default_settings(
                            streamer.settings.bet, Settings.streamer_settings.bet
                        )
                        if streamer.settings.chat != ChatPresence.NEVER:
                            streamer.irc_chat = ThreadChat(
                                self.username,
                                self.twitch.twitch_login.get_auth_token(),
                                streamer.username,
                            )
                        self.streamers.append(streamer)
                    except StreamerDoesNotExistException:
                        logger.info(
                            f"Streamer {username} does not exist",
                            extra={"emoji": ":cry:"},
                        )

            # Populate the streamers with default values.
            # 1. Load channel points and auto-claim bonus
            # 2. Check if streamers are online
            # 3. DEACTIVATED: Check if the user is a moderator. (was used before the 5th of April 2021 to deactivate predictions)
            for streamer in self.streamers:
                time.sleep(random.uniform(0.3, 0.7))
                try:
                    self.twitch.load_channel_points_context(streamer)
                    self.twitch.check_streamer_online(streamer)
                    # self.twitch.viewer_is_mod(streamer)
                except StreamerDoesNotExistException:
                    logger.info(
                        f"Streamer {streamer.username} does not exist",
                        extra={"emoji": ":cry:"},
                    )

            self.original_streamers = [
                streamer.channel_points for streamer in self.streamers
            ]

            # If we have at least one streamer with settings = make_predictions True
            make_predictions = at_least_one_value_in_settings_is(
                self.streamers, "make_predictions", True
            )

            # If we have at least one streamer with settings = claim_drops True
            # Spawn a thread for sync inventory and dashboard
            if (
                    at_least_one_value_in_settings_is(self.streamers, "claim_drops", True)
                    is True
            ):
                self.sync_campaigns_thread = threading.Thread(
                    target=self.twitch.sync_campaigns,
                    args=(self.streamers,),
                )
                self.sync_campaigns_thread.name = "Sync campaigns/inventory"
                self.sync_campaigns_thread.start()
                time.sleep(30)

            self.minute_watcher_thread = threading.Thread(
                target=self.twitch.send_minute_watched_events,
                args=(self.streamers, self.priority),
            )
            self.minute_watcher_thread.name = "Minute watcher"
            self.minute_watcher_thread.start()

            pubsub_handlers = [PubSubHandler(self.twitch, self.streamers, self.events_predictions)]
            if Settings.use_hermes:
                self.ws_pool = HermesWebSocketPool(
                    url=f"{HERMES_WEBSOCKET}?clientId={CLIENT_ID_WEB}",
                    twitch=self.twitch,
                    request_encoder=hermes_data.JsonEncoder(),
                    response_decoder=hermes_data.JsonDecoder(),
                    listeners=pubsub_handlers
                )
            else:
                self.ws_pool = PubSubWebSocketPool(twitch=self.twitch, listeners=pubsub_handlers)

            self.ws_pool.start()

            # Subscribe to community-points-user. Get update for points spent or gains
            user_id = self.twitch.twitch_login.get_user_id()
            # print(f"!!!!!!!!!!!!!! USER_ID: {user_id}")

            # Fixes 'ERR_BADAUTH'
            if not user_id:
                logger.error("No user_id, exiting...")
                self.end(0, 0)

            self.ws_pool.submit(
                PubsubTopic(
                    "community-points-user-v1",
                    user_id=user_id,
                )
            )

            # Going to subscribe to predictions-user-v1. Get update when we place a new prediction (confirm)
            if make_predictions is True:
                self.ws_pool.submit(
                    PubsubTopic(
                        "predictions-user-v1",
                        user_id=user_id,
                    )
                )

            for streamer in self.streamers:
                self._subscribe_streamer_topics(streamer)

            refresh_context = time.time()
            while self.running:
                time.sleep(random.uniform(20, 60))
                self.ws_pool.check_stale_connections()
                if ((time.time() - refresh_context) // 60) >= 30:
                    refresh_context = time.time()
                    for index in range(0, len(self.streamers)):
                        if self.streamers[index].is_online:
                            self.twitch.load_channel_points_context(
                                self.streamers[index]
                            )

    def _subscribe_streamer_topics(self, streamer):
        if self.ws_pool is None:
            return
        self.ws_pool.submit(PubsubTopic("video-playback-by-id", streamer=streamer))
        if streamer.settings.follow_raid is True:
            self.ws_pool.submit(PubsubTopic("raid", streamer=streamer))
        if streamer.settings.make_predictions is True:
            self.ws_pool.submit(
                PubsubTopic("predictions-channel-v1", streamer=streamer)
            )
        if streamer.settings.claim_moments is True:
            self.ws_pool.submit(
                PubsubTopic("community-moments-channel-v1", streamer=streamer)
            )
        if streamer.settings.community_goals is True:
            self.ws_pool.submit(
                PubsubTopic("community-points-channel-v1", streamer=streamer)
            )

    def _init_streamer(self, streamer: Streamer):
        streamer.channel_id = self.twitch.get_channel_id(streamer.username)
        streamer.settings = set_default_settings(
            streamer.settings, Settings.streamer_settings
        )
        streamer.settings.bet = set_default_settings(
            streamer.settings.bet, Settings.streamer_settings.bet
        )
        if streamer.settings.chat != ChatPresence.NEVER:
            streamer.irc_chat = ThreadChat(
                self.username,
                self.twitch.twitch_login.get_auth_token(),
                streamer.username,
            )
        self.twitch.load_channel_points_context(streamer)
        self.twitch.check_streamer_online(streamer)

    def _persist_streamers(self):
        if not self.config_path:
            return True
        from TwitchChannelPointsMiner.config import update_streamers_list

        try:
            update_streamers_list(
                self.config_path, [s.username for s in self.streamers]
            )
            return True
        except OSError as exc:
            logger.warning(
                "Could not write streamers to config (%s). "
                "Changes apply for this session only; edit config.yaml manually to persist.",
                exc,
            )
            return False

    def get_status_snapshot(self) -> dict:
        with self._control_lock:
            uptime_seconds = 0
            if self.start_datetime is not None:
                uptime_seconds = int(
                    (datetime.now() - self.start_datetime).total_seconds()
                )

            session_points_gained = 0
            streamers_dto = []
            for index, streamer in enumerate(self.streamers):
                baseline = (
                    self.original_streamers[index]
                    if index < len(self.original_streamers)
                    else streamer.channel_points
                )
                session_gained = streamer.channel_points - baseline
                session_points_gained += session_gained

                game = ""
                if streamer.stream.game not in [{}, None]:
                    game = (
                        streamer.stream.game.get("displayName")
                        or streamer.stream.game.get("name")
                        or ""
                    )

                streamers_dto.append(
                    {
                        "username": streamer.username,
                        "online": streamer.is_online,
                        "points": streamer.channel_points,
                        "session_gained": session_gained,
                        "title": streamer.stream.title or "",
                        "game": game,
                        "drops_active": bool(streamer.stream.campaigns)
                        or streamer.stream.drops_tags,
                        "watch_streak": streamer.is_online
                        and not streamer.stream.watch_streak_missing,
                    }
                )

            predictions = []
            for event in self.events_predictions.values():
                predictions.append(
                    {
                        "streamer": event.streamer.username,
                        "title": event.title,
                        "status": event.status,
                        "bet_placed": event.bet_placed,
                    }
                )

            ws_connected = (
                self.ws_pool is not None
                and not getattr(self.ws_pool, "force_close", False)
            )

            return {
                "running": self.running,
                "username": self.username,
                "session_id": self.session_id,
                "uptime_seconds": uptime_seconds,
                "session_points_gained": session_points_gained,
                "ws_connected": ws_connected,
                "streamers": streamers_dto,
                "predictions": predictions,
            }

    def add_streamer(self, username: str) -> bool:
        username = username.lower().strip()
        if not username:
            raise ValueError("Username is required")

        with self._control_lock:
            if any(s.username == username for s in self.streamers):
                raise ValueError(f"Streamer {username} is already in the list")

            streamer = Streamer(username)
            try:
                self._init_streamer(streamer)
            except StreamerDoesNotExistException:
                raise ValueError(f"Streamer {username} does not exist") from None
            self.streamers.append(streamer)
            self.original_streamers.append(streamer.channel_points)
            self._subscribe_streamer_topics(streamer)
            persisted = self._persist_streamers()
            logger.info(
                f"Added streamer {username} via Web UI",
                extra={"emoji": ":heavy_plus_sign:"},
            )
            return persisted

    def remove_streamer(self, username: str) -> bool:
        username = username.lower().strip()
        with self._control_lock:
            index = next(
                (i for i, s in enumerate(self.streamers) if s.username == username),
                None,
            )
            if index is None:
                raise ValueError(f"Streamer {username} not found")

            streamer = self.streamers[index]
            if (
                streamer.irc_chat is not None
                and streamer.settings.chat != ChatPresence.NEVER
            ):
                streamer.leave_chat()
                if streamer.irc_chat.is_alive() is True:
                    streamer.irc_chat.join()

            del self.streamers[index]
            if index < len(self.original_streamers):
                del self.original_streamers[index]
            persisted = self._persist_streamers()
            logger.info(
                f"Removed streamer {username} via Web UI",
                extra={"emoji": ":heavy_minus_sign:"},
            )
            return persisted

    def request_shutdown(self):
        threading.Thread(
            target=self._shutdown,
            kwargs={"exit_process": True, "from_signal": False},
            daemon=True,
            name="Web shutdown",
        ).start()

    def end(self, signum, frame):
        if not self.running:
            return
        self._shutdown(exit_process=True, from_signal=True)

    def _shutdown(self, exit_process=True, from_signal=True):
        if not self.running:
            return

        if from_signal:
            logger.info("CTRL+C Detected! Please wait just a moment!")
        else:
            logger.info("Shutdown requested from Web UI. Please wait just a moment!")

        for streamer in self.streamers:
            if streamer.irc_chat is not None and streamer.settings.chat != ChatPresence.NEVER:
                streamer.leave_chat()
                if streamer.irc_chat.is_alive() is True:
                    streamer.irc_chat.join()

        self.running = self.twitch.running = False
        if self.ws_pool is not None:
            self.ws_pool.end()

        if self.minute_watcher_thread is not None:
            self.minute_watcher_thread.join()

        if self.sync_campaigns_thread is not None:
            self.sync_campaigns_thread.join()

        # Check if all the mutex are unlocked.
        # Prevent breaks of .json file
        for streamer in self.streamers:
            if streamer.mutex.locked():
                streamer.mutex.acquire()
                streamer.mutex.release()

        self.__print_report()

        # Stop the queue listener to make sure all messages have been logged
        self.queue_listener.stop()

        if exit_process:
            sys.exit(0)

    def __print_report(self):
        print("\n")
        logger.info(
            f"Ending session: '{self.session_id}'", extra={"emoji": ":stop_sign:"}
        )
        if self.logs_file is not None:
            logger.info(
                f"Logs file: {self.logs_file}", extra={"emoji": ":page_facing_up:"}
            )
        logger.info(
            f"Duration {datetime.now() - self.start_datetime}",
            extra={"emoji": ":hourglass:"},
        )

        if not Settings.logger.less and self.events_predictions != {}:
            print("")
            for event_id in self.events_predictions:
                event = self.events_predictions[event_id]
                if (
                        event.bet_confirmed is True
                        and event.streamer.settings.make_predictions is True
                ):
                    logger.info(
                        f"{event.streamer.settings.bet}",
                        extra={"emoji": ":wrench:"},
                    )
                    if event.streamer.settings.bet.filter_condition is not None:
                        logger.info(
                            f"{event.streamer.settings.bet.filter_condition}",
                            extra={"emoji": ":pushpin:"},
                        )
                    logger.info(
                        f"{event.print_recap()}",
                        extra={"emoji": ":bar_chart:"},
                    )

        print("")
        for streamer_index in range(0, len(self.streamers)):
            if self.streamers[streamer_index].history != {}:
                gained = self.streamers[streamer_index].channel_points - self.original_streamers[streamer_index]

                from colorama import Fore
                streamer_highlight = Fore.YELLOW

                streamer_gain = (
                    f"{streamer_highlight}{self.streamers[streamer_index]}{Fore.RESET}, Total Points Gained: {_millify(gained)}"
                    if Settings.logger.less
                    else f"{streamer_highlight}{repr(self.streamers[streamer_index])}{Fore.RESET}, Total Points Gained (after farming - before farming): {_millify(gained)}"
                )

                indent = ' ' * 25
                streamer_history = '\n'.join(
                    f"{indent}{history}" for history in self.streamers[streamer_index].print_history().split('; ')
                )

                logger.info(
                    f"{streamer_gain}\n{streamer_history}",
                    extra={"emoji": ":moneybag:"},
                )
