import os
from dataclasses import dataclass, fields
from pathlib import Path
import json
import subprocess
import sys
from loguru import logger
import time

_BASE_PATH = Path(__file__).parent.resolve()
SETTINGS_PATH = _BASE_PATH / "data" / "settings.json"


@dataclass
class JagexAccount:
    JX_CHARACTER_ID: str
    JX_SESSION_ID: str
    JX_DISPLAY_NAME: str
    JX_REFRESH_TOKEN: str = ""
    JX_ACCESS_TOKEN: str = ""


class AccountLauncher:
    def __init__(
        self,
        base_path: Path = Path(__file__).parent.resolve(),
        jagex_accounts: list[JagexAccount] = None,
        settings: dict = None,
    ) -> None:
        self._base_path = base_path
        self.jagex_accounts = jagex_accounts or self._load_jagex_accounts()
        self.settings = settings or self._load_settings()
        self.runelite_install_path = Path(self.settings["runelite_install_path"])

    def _set_envs(self, jagex_account: JagexAccount) -> None:
        """Sets required environment variables to launch a jagex account."""
        for field in fields(jagex_account):
            value = getattr(jagex_account, field.name)
            logger.debug(
                f"Setting environment variable: {field.name} with value: {value}"
            )
            os.environ[field.name] = value

    def _unset_envs(self, jagex_account: JagexAccount) -> None:
        """Unsets the environment variables used to launch a jagex account."""
        for field in fields(jagex_account):
            logger.debug(f"Unsetting environment variable: {field.name}")
            os.environ.pop(field.name, None)

    def _load_jagex_accounts(self) -> list[JagexAccount]:
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

    def launch_account(self, jagex_account: JagexAccount):
        """Launches a JagexAccount via the runelite jar."""
        logger.info(f"Loading Jagex Account: {jagex_account.JX_DISPLAY_NAME}")
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
        self._set_envs(jagex_account)

        # Launch runelite.
        subprocess.run(launch_cmd, shell=True)

        # Unset environment variables for this account after launching.
        self._unset_envs(jagex_account)


def main():
    with open(SETTINGS_PATH) as f:
        settings = json.load(f)

    logger.remove()
    logger.add(sys.stderr, level=settings["log_level"].upper())

    ac = AccountLauncher(settings=settings)

    ac.launch_account(ac.jagex_accounts["acc1"])

    time.sleep(5)

    ac.launch_account(ac.jagex_accounts["acc2"])


if __name__ == "__main__":
    main()
