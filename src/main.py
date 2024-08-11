import json
import sys
import threading
import time
from pathlib import Path

from account_launcher.account_launcher import AccountLauncher
from daemon.daemon import Daemon
from loguru import logger
from web_server.app import WebServer

_BASE_PATH = Path(__file__).parent.resolve()
SETTINGS_PATH = _BASE_PATH / "data" / "settings.json"


def main() -> None:
    with open(SETTINGS_PATH) as f:
        settings = json.load(f)

    logger.remove()
    logger.add(sys.stderr, level=settings["log_level"].upper())

    threads = []

    if settings["server"]["enabled"]:
        logger.info("Initializing web server")
        # Initialize the web server
        web_server = WebServer()

        # Start the web server in a separate thread
        web_server_thread = threading.Thread(target=web_server.run, daemon=True)
        web_server_thread.start()
        threads.append(web_server_thread)

    if settings["daemon"]["enabled"]:
        logger.info("Initializing daemon")
        # Initialize account launcher
        account_launcher = AccountLauncher(settings=settings)

        # Initialize the daemon
        daemon = Daemon(settings=settings, account_launcher=account_launcher)

        # Start the daemon in a separate thread
        daemon_thread = threading.Thread(target=daemon.run, daemon=True)
        daemon_thread.start()
        threads.append(daemon_thread)

    while True:
        try:
            time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Got keyboard interrupt, exiting.")
            sys.exit(0)


if __name__ == "__main__":
    main()
