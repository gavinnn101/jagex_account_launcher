from flask import Flask, render_template, request, jsonify
import requests
from dataclasses import dataclass
import socket
import time
from loguru import logger
import threading
from pathlib import Path
import json


@dataclass
class Daemon:
    """ip/port information for daemons connected to the web server."""

    nickname: str
    ip_address: str
    port: int


class WebServer:
    def __init__(self, server_port: int = 5000):
        self.parent_dir = Path(__file__).parent.resolve()
        self.app = Flask(__name__)
        self._setup_routes()
        self.daemons: list[Daemon] = []
        self.server_ip = socket.gethostbyname(socket.gethostname())
        self.server_port = server_port
        self.data_path = Path(__file__).parent.parent.resolve() / "data"
        self.accounts = self._load_accounts()

    def _load_accounts(self):
        """Loads accounts from `accounts.json`."""
        accounts_file_path = self.data_path / "accounts.json"
        if accounts_file_path.exists():
            with open(accounts_file_path, "r") as f:
                return json.load(f)
        return {}

    def _setup_routes(self):
        @self.app.route("/")
        def index():
            """Homepage that allows user to launch jagex accounts via runelite clients on daemons."""
            return render_template(
                "index.html", daemons=self.daemons, accounts=self.accounts
            )

        @self.app.route("/get_accounts", methods=["GET"])
        def get_accounts():
            """Returns the list of accounts."""
            return jsonify(self.accounts)

        @self.app.route("/add_account", methods=["POST"])
        def add_account():
            """Adds or updates an account in the accounts.json file."""
            try:
                account_data = request.json
                original_nickname = account_data.get("originalNickname")
                new_nickname = account_data["nickname"]

                accounts_file_path = self.data_path / "accounts.json"

                if not accounts_file_path.exists():
                    accounts = {}
                else:
                    with open(accounts_file_path, "r") as f:
                        accounts = json.load(f)

                # Remove old entry if editing and the nickname has changed
                if original_nickname and original_nickname != new_nickname:
                    if original_nickname in accounts:
                        del accounts[original_nickname]

                # Add or update the account
                accounts[new_nickname] = {
                    "JX_CHARACTER_ID": account_data["JX_CHARACTER_ID"],
                    "JX_SESSION_ID": account_data["JX_SESSION_ID"],
                    "JX_DISPLAY_NAME": account_data["JX_DISPLAY_NAME"],
                    "JX_REFRESH_TOKEN": account_data["JX_REFRESH_TOKEN"],
                    "JX_ACCESS_TOKEN": account_data["JX_ACCESS_TOKEN"],
                }

                with open(accounts_file_path, "w") as f:
                    json.dump(accounts, f, indent=4)

                self.accounts = accounts  # Update the in-memory accounts list
                return (
                    jsonify(
                        {"status": "success", "message": "Account saved successfully."}
                    ),
                    200,
                )

            except Exception as e:
                logger.exception("Failed to save account.")
                return (
                    jsonify({"status": "error", "message": "Internal Server Error"}),
                    500,
                )

        @self.app.route("/delete_account", methods=["POST"])
        def delete_account():
            """Deletes an account from the accounts.json file."""
            try:
                nickname = request.json["nickname"]
                accounts_file_path = self.data_path / "accounts.json"

                if accounts_file_path.exists():
                    with open(accounts_file_path, "r") as f:
                        accounts = json.load(f)

                    if nickname in accounts:
                        del accounts[nickname]

                        with open(accounts_file_path, "w") as f:
                            json.dump(accounts, f, indent=4)

                        self.accounts = accounts  # Update the in-memory accounts list
                        return (
                            jsonify(
                                {
                                    "status": "success",
                                    "message": "Account deleted successfully.",
                                }
                            ),
                            200,
                        )
                    else:
                        return (
                            jsonify(
                                {"status": "error", "message": "Account not found."}
                            ),
                            404,
                        )
                else:
                    return (
                        jsonify(
                            {"status": "error", "message": "No accounts file found."}
                        ),
                        404,
                    )

            except Exception as e:
                logger.exception("Failed to delete account.")
                return (
                    jsonify({"status": "error", "message": "Internal Server Error"}),
                    500,
                )

        @self.app.route("/launch_account", methods=["POST"])
        def launch_account():
            """Sends a launch account request to the daemon to execute."""
            account_id = request.json["account_id"]
            daemon_nickname = request.json["daemon_nickname"]

            logger.info(f"Launching account: {account_id} on daemon: {daemon_nickname}")

            # Find the daemon by nickname
            daemon = next(
                (d for d in self.daemons if d.nickname == daemon_nickname), None
            )

            if not daemon:
                return jsonify({"status": "error", "message": "Daemon not found"}), 404

            # Send the request to the selected daemon
            response = requests.post(
                f"http://{daemon.ip_address}:{daemon.port}/launch",
                json={"account_id": account_id},
            )
            return jsonify(response.json())

        @self.app.route("/register_daemon", methods=["POST"])
        def register_daemon():
            """Registers a new daemon to be managed in the web app."""
            data = request.json
            new_daemon = Daemon(
                nickname=data["nickname"],
                ip_address=data["ip_address"],
                port=data["port"],
            )

            self.daemons.append(new_daemon)
            return (
                jsonify(
                    {
                        "status": "success",
                        "message": f"Daemon {new_daemon.nickname} registered",
                    }
                ),
                200,
            )

    def _broadcast_server_address(
        self, multicast_address: str = "224.1.1.1", multicast_port: int = 6000
    ) -> None:
        """Uses multicast to broadcast the server address for daemons to find and use."""
        # Create the datagram socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)

        # Set the TTL (time-to-live) for messages to 1 to stay within the local network
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 1)

        message = f"SERVER_IP:{self.server_ip}:{self.server_port}".encode("utf-8")

        while True:
            # Send the server IP and port to the multicast group
            sock.sendto(message, (multicast_address, multicast_port))
            logger.debug(
                f"Sent message: {message} to multicast address: {multicast_address}:{multicast_port}"
            )
            time.sleep(5)

    def run(self, host: str = None, port: int = None):
        """Runs the webserver app."""
        host = host or self.server_ip
        port = port or self.server_port
        self.app.run(host=host, port=port)

    def run_broadcast_thread(self) -> None:
        """Starts a separate thread to run the broadcast server to find daemons."""
        broadcast_thread = threading.Thread(target=self._broadcast_server_address)
        broadcast_thread.daemon = True
        broadcast_thread.start()