import socket
from pathlib import Path

from flask import Flask

from .account_manager import AccountManager
from .daemon_manager import DaemonManager
from .discovery_server import DiscoveryServer
from .routes.routes import setup_routes


class WebServer:
    def __init__(self, server_port: int = 5000):
        self.app = Flask(__name__)
        self.server_ip = socket.gethostbyname(socket.gethostname())
        self.server_port = server_port
        self.data_path = Path(__file__).parent.parent.resolve() / "data"

        self.daemon_manager = DaemonManager()
        self.account_manager = AccountManager(self.data_path)
        self.discovery_server = DiscoveryServer(self.server_ip, self.server_port)

        setup_routes(self.app, self.daemon_manager, self.account_manager)

    def run(self, host: str = None, port: int = None):
        self.discovery_server.run_broadcast_thread()
        self.daemon_manager.run_check_daemons_thread()

        host = host or self.server_ip
        port = port or self.server_port
        self.app.run(host=host, port=port)