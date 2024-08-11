import json
from pathlib import Path

from loguru import logger


class AccountManager:
    def __init__(self, data_path: Path):
        self.data_path = data_path
        self.accounts = self._load_accounts()

    def _load_accounts(self):
        """Loads accounts from `accounts.json`."""
        logger.debug("Loading accounts")
        accounts_file_path = self.data_path / "accounts.json"
        if accounts_file_path.exists():
            with open(accounts_file_path, "r") as f:
                return json.load(f)
        return {}

    def save_accounts(self):
        """Saves `self.accounts` data to `accounts.json`."""
        try:
            accounts_file_path = self.data_path / "accounts.json"
            logger.debug(f"Saving current accounts in memory to {accounts_file_path}")
            with open(accounts_file_path, "w") as f:
                json.dump(self.accounts, f, indent=4)
            logger.info(f"Accounts successfully saved to {accounts_file_path}")
        except Exception as e:
            logger.error(f"Failed to save accounts: {e}")

    def get_accounts(self):
        return self.accounts

    def add_account(self, nickname, account_data):
        if nickname in self.accounts:
            raise ValueError("Account with this nickname already exists")
        self.accounts[nickname] = account_data
        self.save_accounts()

    def update_account(self, original_nickname, new_nickname, account_data):
        if original_nickname not in self.accounts:
            raise ValueError("Account not found")
        if original_nickname != new_nickname and new_nickname in self.accounts:
            raise ValueError("New nickname already exists")

        if original_nickname != new_nickname:
            self.accounts[new_nickname] = self.accounts.pop(original_nickname)

        self.accounts[new_nickname].update(account_data)
        self.save_accounts()

    def delete_account(self, nickname):
        if nickname not in self.accounts:
            raise ValueError("Account not found")
        del self.accounts[nickname]
        self.save_accounts()