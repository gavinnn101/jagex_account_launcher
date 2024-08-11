const API = {
    async fetchDaemons() {
        return await fetch('/get_daemons').then(res => res.json());
    },

    async fetchAccounts() {
        return await fetch('/get_accounts').then(res => res.json());
    },

    async launchAccount(accountId, daemonNickname) {
        return await fetch('/launch_account', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ account_id: accountId, daemon_nickname: daemonNickname }),
        }).then(res => res.json());
    },

    async saveAccount(accountData) {
        const { originalNickname, ...data } = accountData;
        const url = originalNickname ? '/update_account' : '/add_account';
        const method = originalNickname ? 'PUT' : 'POST';
        return await fetch(url, {
            method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(originalNickname ? { originalNickname, ...data } : data),
        }).then(res => res.json());
    },

    async deleteAccount(nickname) {
        return await fetch('/delete_account', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ nickname }),
        }).then(res => res.json());
    }
};

export default API;
