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
                "index.html",
                daemons=self.daemons,
                accounts=self.accounts,
                notification={},
            )

        @self.app.route("/heartbeat")
        def heartbeat():
            """Returns a heartbeat response letting the requester know that the server is online."""
            return jsonify({"status": "success", "message": "Server is alive"}), 200

        @self.app.route("/get_daemons", methods=["GET"])
        def get_daemons():
            daemon_list = [
                {"nickname": d.nickname, "ip_address": d.ip_address, "port": d.port}
                for d in self.daemons
            ]
            return jsonify(daemon_list)

        @self.app.route("/get_accounts", methods=["GET"])
        def get_accounts():
            """Returns the list of accounts."""
            return jsonify(self.accounts)

        @self.app.route("/add_account", methods=["POST"])
        def add_account():
            """Adds an account to `self.accounts` and `accounts.json`."""
            try:
                account_data = request.json
                new_nickname = account_data.get("nickname")

                if not new_nickname:
                    return (
                        jsonify({"status": "error", "message": "Nickname is required"}),
                        400,
                    )

                if new_nickname in self.accounts:
                    return (
                        jsonify(
                            {
                                "status": "error",
                                "message": "Account with this nickname already exists",
                            }
                        ),
                        409,
                    )

                self.accounts[new_nickname] = {
                    "JX_CHARACTER_ID": account_data.get("JX_CHARACTER_ID"),
                    "JX_SESSION_ID": account_data.get("JX_SESSION_ID"),
                    "JX_DISPLAY_NAME": account_data.get("JX_DISPLAY_NAME"),
                    "JX_REFRESH_TOKEN": account_data.get("JX_REFRESH_TOKEN"),
                    "JX_ACCESS_TOKEN": account_data.get("JX_ACCESS_TOKEN"),
                }

                self.save_accounts()
                return (
                    jsonify(
                        {"status": "success", "message": "Account added successfully."}
                    ),
                    201,
                )

            except Exception as e:
                logger.exception("Failed to add account.")
                return jsonify({"status": "error", "message": str(e)}), 500

        @self.app.route("/update_account", methods=["PUT"])
        def update_account():
            """Updates an accounts data in `self.accounts` and `accounts.json`."""
            try:
                account_data = request.json
                original_nickname = account_data.get("originalNickname")
                new_nickname = account_data.get("nickname")

                if not original_nickname or not new_nickname:
                    return (
                        jsonify(
                            {
                                "status": "error",
                                "message": "Both original and new nicknames are required",
                            }
                        ),
                        400,
                    )

                if original_nickname not in self.accounts:
                    return (
                        jsonify({"status": "error", "message": "Account not found"}),
                        404,
                    )

                if original_nickname != new_nickname and new_nickname in self.accounts:
                    return (
                        jsonify(
                            {
                                "status": "error",
                                "message": "New nickname already exists",
                            }
                        ),
                        409,
                    )

                # Remove old entry if the nickname has changed
                if original_nickname != new_nickname:
                    self.accounts[new_nickname] = self.accounts.pop(original_nickname)

                # Update the account data
                self.accounts[new_nickname].update(
                    {
                        "JX_CHARACTER_ID": account_data.get("JX_CHARACTER_ID"),
                        "JX_SESSION_ID": account_data.get("JX_SESSION_ID"),
                        "JX_DISPLAY_NAME": account_data.get("JX_DISPLAY_NAME"),
                        "JX_REFRESH_TOKEN": account_data.get("JX_REFRESH_TOKEN"),
                        "JX_ACCESS_TOKEN": account_data.get("JX_ACCESS_TOKEN"),
                    }
                )

                self.save_accounts()
                return (
                    jsonify(
                        {
                            "status": "success",
                            "message": "Account updated successfully.",
                        }
                    ),
                    200,
                )

            except Exception as e:
                logger.exception("Failed to update account.")
                return jsonify({"status": "error", "message": str(e)}), 500

        @self.app.route("/delete_account", methods=["POST"])
        def delete_account():
            """Deletes an account from `self.accounts` and `accounts.json`."""
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
                logger.warning(f"Daemon not found: {daemon_nickname}")
                return jsonify({"status": "error", "message": "Daemon not found"}), 404

            # Retrieve the account data from the server's accounts.json
            account_data = self.accounts[account_id]
            if not account_data:
                logger.warning(f"Couldn't find account data for: {account_id}")
                return jsonify({"status": "error", "message": "Account not found"}), 404

            # Send the account data to the selected daemon
            response = requests.post(
                f"http://{daemon.ip_address}:{daemon.port}/launch_account",
                json=account_data,
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

    def save_accounts(self):
        """Saves `self.accounts` data to `accounts.json`."""
        try:
            accounts_file_path = self.data_path / "accounts.json"
            with open(accounts_file_path, "w") as f:
                json.dump(self.accounts, f, indent=4)
            logger.info(f"Accounts successfully saved to {accounts_file_path}")
        except Exception as e:
            logger.error(f"Failed to save accounts: {e}")

    def _broadcast_server_address(
        self, multicast_address: str = "224.1.1.1", multicast_port: int = 6000
    ) -> None:
        """Uses multicast to broadcast the server address for daemons to find and use."""
        # Create socket
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

    def _check_daemons(self) -> None:
        """Checks daemon heartbeats and manages `self.daemons` appropriately."""
        while True:
            for index, daemon in enumerate(self.daemons):
                try:
                    response = requests.get(
                        f"http://{daemon.ip_address}:{daemon.port}/heartbeat", timeout=5
                    )
                except requests.exceptions.ConnectTimeout:
                    logger.info(
                        f"Couldn't get heartbeat from daemon: {daemon.nickname}, removing from list."
                    )
                    self.daemons.pop(index)
                if response.ok:
                    continue
                else:
                    self.daemons.pop(index)
            time.sleep(5)

    def run(self, host: str = None, port: int = None):
        """Runs the webserver app."""
        # Start broadcast thread, required by server for daemons to discover.
        self.run_broadcast_thread()

        # Start daemon checker thread to manage `self.daemons`
        self.run_check_daemons_thread()

        host = host or self.server_ip
        port = port or self.server_port
        self.app.run(host=host, port=port)

    def run_broadcast_thread(self) -> None:
        """Starts a separate thread to run the broadcast server to find daemons."""
        broadcast_thread = threading.Thread(
            target=self._broadcast_server_address, daemon=True
        )
        broadcast_thread.start()

    def run_check_daemons_thread(self) -> None:
        """Starts a separate thread to run heartbeat checks on daemons."""
        check_daemons_thread = threading.Thread(target=self._check_daemons, daemon=True)
        check_daemons_thread.start()
