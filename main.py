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

while True:
    try:
        from TwitchChannelPointsMiner import TwitchChannelPointsMiner
        from TwitchChannelPointsMiner.classes.Settings import FollowersOrder
        from TwitchChannelPointsMiner.logger import LoggerSettings
        break
    except ImportError:
        os.system("pip install -r requirements.txt")

def load_or_create_config(file_path):
    default_config = {
        "username": "",
        "password": "",
        "streamers": []
    }

    if os.path.exists(file_path):
        with open(file_path, 'r') as file:
            config = json.load(file)
    else:
        with open(file_path, 'w') as file:
            json.dump(default_config, file, indent=4)
        config = default_config

    return config

def main():
    config = load_or_create_config("config.json")

    try:
        logger_settings = LoggerSettings(
            save=True,
            console_level=logging.INFO,
            file_level=logging.DEBUG,
            emoji=True,
            smart=True,
        )

        twitch_miner = TwitchChannelPointsMiner(
            username=config.get("username", ""),
            password=config.get("password", ""),
            logger_settings=logger_settings
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
