import requests
from flask import Flask, request, jsonify
from account_launcher.account_launcher import AccountLauncher, JagexAccount
import socket
from loguru import logger
import struct
import threading
import time


class Daemon:
    def __init__(
        self,
        settings: dict,
        nickname: str = None,
        ip_address: str = None,
        port: int = None,
        server_address: tuple[str, int] = None,
        account_launcher: AccountLauncher = None,
    ):
        self.nickname = nickname or self._get_hostname()
        self.ip_address = ip_address or self._get_ip_address()
        self.port = port or self._get_port()
        self.server_address = server_address
        self.settings = settings

        self.account_launcher = account_launcher or AccountLauncher(
            settings=self.settings
        )

        # Initialize Flask app
        self.app = Flask(__name__)
        self._setup_routes()

    def _setup_routes(self):
        @self.app.route("/launch_account", methods=["POST"])
        def launch_account():
            account_data = request.json

            # Validate the received data
            required_fields = ["JX_CHARACTER_ID", "JX_SESSION_ID", "JX_DISPLAY_NAME"]
            if not all(field in account_data for field in required_fields):
                return (
                    jsonify({"status": "error", "message": "Incomplete account data"}),
                    400,
                )

            # Create a JagexAccount instance using the received data
            jagex_account = JagexAccount(
                JX_CHARACTER_ID=account_data["JX_CHARACTER_ID"],
                JX_SESSION_ID=account_data["JX_SESSION_ID"],
                JX_DISPLAY_NAME=account_data["JX_DISPLAY_NAME"],
                JX_REFRESH_TOKEN=account_data.get("JX_REFRESH_TOKEN", ""),
                JX_ACCESS_TOKEN=account_data.get("JX_ACCESS_TOKEN", ""),
            )

            # Launch the account using the AccountLauncher
            self.account_launcher.launch_account(jagex_account)

            return jsonify({"status": "success", "message": "Account launched"})

    def _get_hostname(self) -> str:
        """Gets the name of the computer for the dameon."""
        return socket.gethostname()

    def _get_ip_address(self, hostname: str = None) -> str:
        """Gets the local ip address for the daemon."""
        hostname = hostname or self._get_hostname()
        return socket.gethostbyname(hostname)

    def _get_port(self) -> int:
        """Gets the next available port to use for the daemon app."""
        port = 5001
        while True:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                try:
                    s.bind(("", port))
                except OSError:
                    logger.debug(f"Port: {port} is already in use.")
                    port += 1
                else:
                    logger.debug(f"Found free port: {port}")
                    return port

    def _discover_server(
        self, multicast_address: str = "224.1.1.1", multicast_port: int = 6000
    ):
        """Listens for the server multicast and returns the server IP/Port."""
        logger.info(
            f"Attempting to discover server on {multicast_address}:{multicast_port}"
        )
        # Create the datagram socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)

        # Allow multiple sockets to use the same PORT number
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        # Bind to the multicast port
        sock.bind(("", multicast_port))

        # Tell the operating system to add the socket to the multicast group on all interfaces
        group = socket.inet_aton(multicast_address)
        mreq = struct.pack("4sL", group, socket.INADDR_ANY)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

        while True:
            if self.server_address:
                server_ip, server_port = self.server_address
                try:
                    # Send heartbeat request to see if the server is online.
                    response = requests.get(
                        f"http://{server_ip}:{server_port}/heartbeat", timeout=5
                    )
                    if response.ok:
                        logger.debug(
                            f"Server at {server_ip}:{server_port} is still reachable."
                        )
                        time.sleep(5)
                        continue
                except requests.exceptions.RequestException as e:
                    logger.warning(
                        f"Failed to reach server at {server_ip}:{server_port}: {e}"
                    )
                    # If the server is not reachable, reset server_address to None
                    self.server_address = None
            else:
                logger.debug(
                    f"Listening for multicast messages on {multicast_address}:{multicast_port}..."
                )
                data, address = sock.recvfrom(1024)
                message = data.decode("utf-8")
                logger.debug(f"Received message: {message} from {address}")

                if message.startswith("SERVER_IP:"):
                    _, server_ip, server_port = message.split(":")
                    logger.info(f"Discovered server at {server_ip}:{server_port}")
                    self.server_address = [server_ip, int(server_port)]

                    # Register with the new found server
                    self._register_with_server()

    def _register_with_server(self, server_address: tuple[str, int] = None):
        data = {
            "nickname": self.nickname,
            "ip_address": self.ip_address,
            "port": self.port,
        }
        server_ip, server_port = server_address or self.server_address
        response = requests.post(
            f"http://{server_ip}:{server_port}/register_daemon", json=data
        )
        logger.info(f"Registered with server: {response.json()}")

    def run(self):
        self.run_discover_thread()

        # Run the Flask app
        self.app.run(host=self.ip_address, port=self.port)

    def run_discover_thread(self):
        """Starts a thread to ensure the daemon is connected to a server."""
        discover_thread = threading.Thread(target=self._discover_server, daemon=True)
        discover_thread.start()
