from flask import jsonify, render_template, request
from loguru import logger
from web_server.services.account_manager import AccountManager
from web_server.services.daemon_manager import Daemon, DaemonManager


def setup_routes(app, daemon_manager: DaemonManager, account_manager: AccountManager):
    @app.route("/")
    def index():
        return render_template(
            "index.html",
            daemons=daemon_manager.get_daemons(),
            accounts=account_manager.get_accounts(),
            notification={},
        )

    @app.route("/heartbeat")
    def heartbeat():
        logger.debug("Sending server is alive response")
        return jsonify({"status": "success", "message": "Server is alive"}), 200

    @app.route("/get_daemons", methods=["GET"])
    def get_daemons():
        logger.debug("Returning list of daemons in json format.")
        daemon_list = [
            {"nickname": d.nickname, "ip_address": d.ip_address, "port": d.port}
            for d in daemon_manager.get_daemons()
        ]
        return jsonify(daemon_list)

    @app.route("/get_accounts", methods=["GET"])
    def get_accounts():
        return jsonify(account_manager.get_accounts())

    @app.route("/add_account", methods=["POST"])
    def add_account():
        try:
            account_data = request.json
            new_nickname = account_data.pop("nickname")
            logger.info(f"Adding account with data: {account_data}")
            account_manager.add_account(new_nickname, account_data)
            return jsonify({"status": "success", "message": "Account added successfully."}), 201
        except Exception as e:
            logger.exception("Failed to add account.")
            return jsonify({"status": "error", "message": str(e)}), 500

    @app.route("/update_account", methods=["PUT"])
    def update_account():
        try:
            account_data = request.json
            original_nickname = account_data.pop("originalNickname")
            new_nickname = account_data.pop("nickname")
            logger.info(f"Updating account {original_nickname} with data: {account_data}")
            account_manager.update_account(original_nickname, new_nickname, account_data)
            return jsonify({"status": "success", "message": "Account updated successfully."}), 200
        except Exception as e:
            logger.exception("Failed to update account.")
            return jsonify({"status": "error", "message": str(e)}), 500

    @app.route("/delete_account", methods=["POST"])
    def delete_account():
        try:
            nickname = request.json["nickname"]
            logger.info(f"Deleting account {nickname}")
            account_manager.delete_account(nickname)
            return jsonify({"status": "success", "message": "Account deleted successfully."}), 200
        except Exception as e:
            logger.exception("Failed to delete account.")
            return jsonify({"status": "error", "message": f"Internal Server Error: {e}"}), 500

    @app.route("/launch_account", methods=["POST"])
    def launch_account():
        account_id = request.json["account_id"]
        daemon_nickname = request.json["daemon_nickname"]
        logger.info(f"Launching account: {account_id} on daemon: {daemon_nickname}")
        
        try:
            account_data = account_manager.get_accounts()[account_id]
            return jsonify(daemon_manager.launch_account(account_data, daemon_nickname))
        except Exception as e:
            logger.exception("Failed to launch account.")
            return jsonify({"status": "error", "message": str(e)}), 500

    @app.route("/register_daemon", methods=["POST"])
    def register_daemon():
        data = request.json
        new_daemon = Daemon(
            nickname=data["nickname"],
            ip_address=data["ip_address"],
            port=data["port"],
        )
        daemon_manager.add_daemon(new_daemon)
        return jsonify({"status": "success", "message": f"Daemon {new_daemon.nickname} registered"}), 200