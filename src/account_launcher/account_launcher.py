import os
from dataclasses import dataclass, fields
from pathlib import Path
import json
import subprocess
from loguru import logger


@dataclass
class JagexAccount:
    """Jagex account character data needed to login."""

    JX_CHARACTER_ID: str
    JX_SESSION_ID: str
    JX_DISPLAY_NAME: str
    JX_REFRESH_TOKEN: str = ""
    JX_ACCESS_TOKEN: str = ""


@dataclass
class AccountNickname:
    """Represents the nickname for the account from `accounts.json`."""

    name: str = ""


class AccountLauncher:
    def __init__(
        self,
        base_path: Path = Path(__file__).parent.parent.resolve(),
        jagex_accounts: dict[AccountNickname, JagexAccount] = None,
        settings: dict = None,
    ) -> None:
        self._base_path = base_path
        self.jagex_accounts = jagex_accounts or self._load_jagex_accounts()
        self.settings = settings or self._load_settings()
        self.runelite_install_path = Path(self.settings["runelite_install_path"])

    def _validate_account_field(self, field_name, value) -> bool:
        """Checks if the account data value is valid to use."""
        required_data = ["JX_CHARACTER_ID", "JX_SESSION_ID", "JX_DISPLAY_NAME"]
        if field_name in required_data:
            logger.debug(f"Returning bool for required data value: {bool(value)}")
            return value
        return True

    def _set_env_vars(self, jagex_account: JagexAccount) -> bool:
        """Sets required environment variables to launch a jagex account."""
        for field in fields(jagex_account):
            value = getattr(jagex_account, field.name)
            if not self._validate_account_field(field.name, value):
                logger.warning(
                    f"Failed to validate field: {field.name} with value: {value}"
                )
                return False

            logger.debug(
                f"Setting environment variable: {field.name} with value: {value}"
            )
            os.environ[field.name] = value
        return True

    def _unset_env_vars(self, jagex_account: JagexAccount) -> None:
        """Unsets the environment variables used to launch a jagex account."""
        for field in fields(jagex_account):
            logger.debug(f"Unsetting environment variable: {field.name}")
            os.environ.pop(field.name, None)

    def _load_jagex_accounts(self) -> dict[AccountNickname, JagexAccount]:
        """Loads Jagex accounts from `accounts.json`."""
        accounts_file_path = self._base_path / "data" / "accounts.json"
        logger.debug(f"Loading jagex accounts from file: {accounts_file_path}")
        with open(accounts_file_path) as f:
            accounts_data = json.load(f)
        return {
            account: JagexAccount(**account_data)
            for account, account_data in accounts_data.items()
        }

    def _load_settings(self) -> dict:
        """Loads settings from `settings.json` into a dict."""
        settings_file_path = self._base_path / "data" / "settings.json"
        logger.debug(f"Loading settings from file path: {settings_file_path}")
        with open(settings_file_path) as f:
            return json.load(f)

    def launch_account(self, jagex_account: JagexAccount) -> None:
        """Launches a JagexAccount via the runelite jar."""
        logger.info(f"Launching Jagex Account: {jagex_account.JX_DISPLAY_NAME}")
        java_path = self.runelite_install_path / "jre" / "bin" / "java.exe"
        runelite_jar_path = self.runelite_install_path / "RuneLite.jar"
        launch_cmd = [
            "start",
            "cmd",
            "/c",
            java_path,
            "-XX:+DisableAttachMechanism",
            "-Xmx2G",
            "-Xss2m",
            "-XX:CompileThreshold=1500",
            "-jar",
            "-Dawt.useSystemAAFontSettings=on",
            "-Dswing.aatext=true",
            runelite_jar_path,
        ]

        # Set environment variables for this account before launching.
        if self._set_env_vars(jagex_account):
            # Launch runelite.
            subprocess.run(launch_cmd, shell=True)
        else:
            logger.warning(f"Not launching account: {jagex_account.JX_DISPLAY_NAME}")

        # Unset environment variables for this account after launching.
        self._unset_env_vars(jagex_account)
