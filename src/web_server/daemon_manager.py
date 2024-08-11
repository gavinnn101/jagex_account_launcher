import threading
import time
from dataclasses import dataclass

import requests
from loguru import logger


@dataclass
class Daemon:
    """ip/port information for daemons connected to the web server."""
    nickname: str
    ip_address: str
    port: int


class DaemonManager:
    def __init__(self):
        self.daemons: list[Daemon] = []
        self._lock = threading.Lock()

    def add_daemon(self, daemon: Daemon):
        with self._lock:
            self.daemons.append(daemon)
        logger.info(f"Added daemon: {daemon.nickname}")

    def remove_daemon(self, nickname: str):
        with self._lock:
            self.daemons = [d for d in self.daemons if d.nickname != nickname]
        logger.info(f"Removed daemon: {nickname}")

    def get_daemons(self):
        with self._lock:
            return self.daemons.copy()

    def check_daemons(self):
        while True:
            with self._lock:
                for index, daemon in enumerate(self.daemons):
                    try:
                        response = requests.get(
                            f"http://{daemon.ip_address}:{daemon.port}/heartbeat", timeout=5
                        )
                        if not response.ok:
                            self.daemons.pop(index)
                            logger.info(f"Removed unresponsive daemon: {daemon.nickname}")
                    except requests.exceptions.RequestException:
                        self.daemons.pop(index)
                        logger.info(f"Removed unreachable daemon: {daemon.nickname}")
            time.sleep(5)

    def run_check_daemons_thread(self):
        check_daemons_thread = threading.Thread(target=self.check_daemons, daemon=True)
        check_daemons_thread.start()

    def launch_account(self, account_data, daemon_nickname):
        daemon = next((d for d in self.daemons if d.nickname == daemon_nickname), None)
        if not daemon:
            raise ValueError(f"Daemon not found: {daemon_nickname}")

        response = requests.post(
            f"http://{daemon.ip_address}:{daemon.port}/launch_account",
            json=account_data,
        )
        return response.json()