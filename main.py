import os
import json
import logging

def clear_console():
    os.system('cls' if os.name == 'nt' else 'clear')

def set_console_title(title):
    if os.name == 'nt':
        os.system(f"title {title}")

clear_console()
set_console_title("Klaro's Twitch Miner")

strikes = 0
while True:
    try:
        from TwitchChannelPointsMiner import TwitchChannelPointsMiner
        from TwitchChannelPointsMiner.classes.Settings import FollowersOrder
        from TwitchChannelPointsMiner.logger import LoggerSettings
        from TwitchChannelPointsMiner.classes.entities.Streamer import StreamerSettings
        from TwitchChannelPointsMiner.classes.entities.Bet import Strategy, BetSettings, Condition, OutcomeKeys, FilterCondition, DelayMode
        break
    except ImportError:
        if strikes >= 3:
            raise ImportError("Failed to import required modules.")
        strikes += 1
        os.system("pip install -r requirements.txt")

def load_or_create_config(file_path):
    default_config = {
        "username": "your-twitch-username",
        "password": "your-twitch-password (Optional)",
        "smart_logging": True,
        "disable_ssl_cert_verification": False,
        "show_seconds": False,
        "claim_drops_startup": True,
        "claim_drops": True,
        "betting(make_predictions)": True,
        "follow_raid": True,
        "emojis": True,
        "disable_ssl_cert_verification": False,
        "save_logs": False,
        "show_username_in_console": False,
        "show_claimed_bonus_msg": True,
        "streamers": [],
        "bet": {
            "strategy": None,
            "percentage": None,
            "percentage_gap": None,
            "max_points": None,
            "stealth_mode": None,
            "delay_mode": None,
            "delay": None,
            "minimum_points": None,
        }
    }

    if os.path.exists(file_path):
        with open(file_path, 'r') as file:
            config = json.load(file)

        updated = False
        for key, value in default_config.items():
            if key not in config:
                config[key] = value
                updated = True
        if updated:
            with open(file_path, 'w') as file:
                json.dump(config, file, indent=4)

    else:
        with open(file_path, 'w') as file:
            json.dump(default_config, file, indent=4)
        config = default_config

    return config

def main():
    config = load_or_create_config("config.json")
    bet_settings = config.get("bet", {})

    newStrategy = None
    for strategy in Strategy:
        if bet_settings.get(strategy.name):
            newStrategy = strategy
            break
    else:
        newStrategy = Strategy.SMART

    newDelayMode = None
    for delay_mode in DelayMode:
        if bet_settings.get(delay_mode.name):
            newDelayMode = delay_mode
            break
    else:
        newDelayMode = DelayMode.FROM_END

    try:
        logger_settings = LoggerSettings(
            save=config.get("save_logs", False),
            console_level=logging.INFO,
            file_level=logging.DEBUG,
            emoji=config.get("emojis", True),
            smart=config.get("smart_logging", True),
            show_seconds=config.get("show_seconds", False),
            console_username=config.get("show_username_in_console", False),
            show_claimed_bonus_msg=config.get("show_claimed_bonus_msg", True)
        )

        streamer_settings = StreamerSettings(
            make_predictions=config.get("betting(make_predictions)", True),
            follow_raid=config.get("follow_raid", True),
            claim_drops=config.get("claim_drops", True),
            bet=BetSettings(
                strategy=newStrategy,
                percentage=bet_settings.get("percentage"),
                percentage_gap=bet_settings.get("percentage_gap"),
                max_points=bet_settings.get("max_points"),
                stealth_mode=bet_settings.get("stealth_mode"),
                delay_mode=newDelayMode,
                delay=bet_settings.get("delay"),
                minimum_points=bet_settings.get("minimum_points")
            )
        )

        twitch_miner = TwitchChannelPointsMiner(
            username=config.get("username", ""),
            password=config.get("password", ""),
            claim_drops_startup=config.get("claim_drops_startup", True),
            disable_ssl_cert_verification=config.get("disable_ssl_cert_verification", False),
            logger_settings=logger_settings,
            streamer_settings=streamer_settings
        )

        streamers = config.get("streamers", [])
        if streamers:
            twitch_miner.mine(streamers)
        else:
            twitch_miner.mine(
                followers=True,
                followers_order=FollowersOrder.DESC
            )
    except Exception as e:
        logging.error(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
