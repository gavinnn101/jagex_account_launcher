from account_launcher.account_launcher import AccountLauncher
from web_server.app import WebServer
from daemon.daemon import Daemon

from loguru import logger
from pathlib import Path
import json
import sys
import threading

_BASE_PATH = Path(__file__).parent.resolve()
SETTINGS_PATH = _BASE_PATH / "data" / "settings.json"


def main() -> None:
    with open(SETTINGS_PATH) as f:
        settings = json.load(f)

    logger.remove()
    logger.add(sys.stderr, level=settings["log_level"].upper())

    if settings["server"]["enabled"]:
        logger.info("Initializing web server")
        # Initialize the web server
        web_server = WebServer()

        # Start server broadcast thread
        # This is required for daemons to find the server address
        web_server.run_broadcast_thread()

        # Start the web server in a separate thread
        web_server_thread = threading.Thread(target=web_server.run, daemon=True)
        web_server_thread.start()

    if settings["daemon"]["enabled"]:
        logger.info("Initializing daemon")
        # Initialize account launcher
        account_launcher = AccountLauncher(settings=settings)

        # Initialize the daemon
        daemon = Daemon(settings=settings, account_launcher=account_launcher)

        # Start the daemon in a separate thread
        daemon_thread = threading.Thread(target=daemon.run, daemon=True)
        daemon_thread.start()

        # Join the threads to keep the main program alive
        web_server_thread.join()
        daemon_thread.join()


if __name__ == "__main__":
    main()
