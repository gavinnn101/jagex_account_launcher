import API from './api.js';
const { ref, computed, watch, onMounted, onUnmounted, createApp } = Vue;

// Composable for notifications
const useNotification = () => {
    const notification = ref({ type: '', message: '' });
    let timeoutId = null;

    const showNotification = (type, message, duration = 3000) => {
        clearTimeout(timeoutId);
        notification.value = { type, message: message || 'No message provided' };

        timeoutId = setTimeout(() => {
            closeNotification();
        }, duration);
    };

    const closeNotification = () => {
        notification.value = { type: '', message: '' };
        clearTimeout(timeoutId);
    };

    return { notification, showNotification, closeNotification };
};

// Composable for dark mode
const useDarkMode = () => {
    const isDarkMode = ref(false);

    const toggleDarkMode = () => {
        isDarkMode.value = !isDarkMode.value;
        localStorage.setItem('darkMode', isDarkMode.value);
        applyDarkMode();
    };

    const applyDarkMode = () => {
        if (isDarkMode.value) {
            document.body.classList.add('dark-mode');
        } else {
            document.body.classList.remove('dark-mode');
        }
    };

    onMounted(() => {
        const savedDarkMode = localStorage.getItem('darkMode');
        if (savedDarkMode !== null) {
            isDarkMode.value = JSON.parse(savedDarkMode);
            applyDarkMode();
        }
    });

    return { isDarkMode, toggleDarkMode };
};

// Components
const NotificationAlert = {
    props: ['notification'],
    emits: ['close'],
    data() {
        return {
            isVisible: true,
        };
    },
    watch: {
        notification: {
            handler(newVal) {
                if (newVal.message) {
                    this.isVisible = true;
                    setTimeout(() => {
                        this.isVisible = false;
                    }, this.fadeDuration);
                }
            },
            immediate: true,
            deep: true
        }
    },
    computed: {
        fadeDuration() {
            return 3000;
        }
    },
    template: `
        <transition name="fade" @after-leave="$emit('close')">
            <div v-if="isVisible && notification.message" :class="['alert', 'alert-' + (notification.type || 'info')]" role="alert">
                {{ notification.message }}
                <button type="button" class="btn-close" @click="isVisible = false" aria-label="Close"></button>
            </div>
        </transition>
    `
};

const DaemonsTable = {
    props: ['daemons'],
    emits: ['launch'],
    template: `
        <table class="table table-bordered">
            <thead>
                <tr>
                    <th>Nickname</th>
                    <th>IP Address</th>
                    <th>Port</th>
                    <th>Action</th>
                </tr>
            </thead>
            <tbody>
                <tr v-if="daemons.length === 0">
                    <td colspan="4" class="text-center">No daemons available</td>
                </tr>
                <tr v-for="daemon in daemons" :key="daemon.nickname">
                    <td>{{ daemon.nickname }}</td>
                    <td>{{ daemon.ip_address }}</td>
                    <td>{{ daemon.port }}</td>
                    <td>
                        <button class="btn btn-primary btn-sm" @click="$emit('launch', daemon.nickname)">
                            Launch Account
                        </button>
                    </td>
                </tr>
            </tbody>
        </table>
    `
};

const AccountsTable = {
    props: ['accounts'],
    emits: ['edit', 'delete'],
    template: `
        <table class="table table-bordered">
            <thead>
                <tr>
                    <th>Nickname</th>
                    <th>JX_CHARACTER_ID</th>
                    <th>JX_SESSION_ID</th>
                    <th>JX_DISPLAY_NAME</th>
                    <th>Action</th>
                </tr>
            </thead>
            <tbody>
                <tr v-for="(account, nickname) in accounts" :key="nickname">
                    <td>{{ nickname }}</td>
                    <td>{{ account.JX_CHARACTER_ID }}</td>
                    <td>{{ account.JX_SESSION_ID }}</td>
                    <td>{{ account.JX_DISPLAY_NAME }}</td>
                    <td>
                        <button class="btn btn-primary btn-sm me-2" @click="$emit('edit', nickname)">Edit</button>
                        <button class="btn btn-danger btn-sm" @click="$emit('delete', nickname)">Delete</button>
                    </td>
                </tr>
            </tbody>
        </table>
    `
};

const AccountModal = {
    props: ['show', 'account'],
    emits: ['close', 'save'],
    setup(props, { emit }) {
        const formData = ref({
            nickname: '',
            JX_CHARACTER_ID: '',
            JX_SESSION_ID: '',
            JX_DISPLAY_NAME: '',
            JX_REFRESH_TOKEN: '',
            JX_ACCESS_TOKEN: '',
        });
        const originalNickname = ref('');
        const errors = ref({});

        const resetForm = () => {
            formData.value = {
                nickname: '',
                JX_CHARACTER_ID: '',
                JX_SESSION_ID: '',
                JX_DISPLAY_NAME: '',
                JX_REFRESH_TOKEN: '',
                JX_ACCESS_TOKEN: '',
            };
            originalNickname.value = '';
            errors.value = {};
        };

        const validateForm = () => {
            errors.value = {};
            if (!formData.value.nickname) errors.value.nickname = 'Nickname is required';
            if (!formData.value.JX_CHARACTER_ID) errors.value.JX_CHARACTER_ID = 'Character ID is required';
            if (!formData.value.JX_SESSION_ID) errors.value.JX_SESSION_ID = 'Session ID is required';
            if (!formData.value.JX_DISPLAY_NAME) errors.value.JX_DISPLAY_NAME = 'Display Name is required';
            return Object.keys(errors.value).length === 0;
        };

        const handleSubmit = () => {
            if (validateForm()) {
                emit('save', { ...formData.value, originalNickname: originalNickname.value });
            }
        };

        watch(() => props.account, (newAccount) => {
            if (newAccount) {
                formData.value = { ...newAccount };
                originalNickname.value = newAccount.nickname;
            } else {
                resetForm();
            }
        }, { immediate: true });

        return { formData, handleSubmit, errors };
    },
    template: `
        <div v-if="show" class="modal fade show d-block" tabindex="-1" aria-labelledby="accountModalLabel" aria-modal="true">
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title" id="accountModalLabel">{{ account ? 'Edit' : 'Add' }} Account</h5>
                        <button type="button" class="btn-close" @click="$emit('close')" aria-label="Close"></button>
                    </div>
                    <div class="modal-body">
                        <form @submit.prevent="handleSubmit">
                            <div class="mb-3">
                                <label for="accountNickname" class="form-label">Account Nickname</label>
                                <input type="text" class="form-control" id="accountNickname" v-model="formData.nickname" required>
                                <div v-if="errors.nickname" class="text-danger">{{ errors.nickname }}</div>
                            </div>
                            <div class="mb-3">
                                <label for="jxCharacterId" class="form-label">JX_CHARACTER_ID</label>
                                <input type="text" class="form-control" id="jxCharacterId" v-model="formData.JX_CHARACTER_ID" required>
                                <div v-if="errors.JX_CHARACTER_ID" class="text-danger">{{ errors.JX_CHARACTER_ID }}</div>
                            </div>
                            <div class="mb-3">
                                <label for="jxSessionId" class="form-label">JX_SESSION_ID</label>
                                <input type="text" class="form-control" id="jxSessionId" v-model="formData.JX_SESSION_ID" required>
                                <div v-if="errors.JX_SESSION_ID" class="text-danger">{{ errors.JX_SESSION_ID }}</div>
                            </div>
                            <div class="mb-3">
                                <label for="jxDisplayName" class="form-label">JX_DISPLAY_NAME</label>
                                <input type="text" class="form-control" id="jxDisplayName" v-model="formData.JX_DISPLAY_NAME" required>
                                <div v-if="errors.JX_DISPLAY_NAME" class="text-danger">{{ errors.JX_DISPLAY_NAME }}</div>
                            </div>
                            <div class="mb-3">
                                <label for="jxRefreshToken" class="form-label">JX_REFRESH_TOKEN (Optional)</label>
                                <input type="text" class="form-control" id="jxRefreshToken" v-model="formData.JX_REFRESH_TOKEN">
                            </div>
                            <div class="mb-3">
                                <label for="jxAccessToken" class="form-label">JX_ACCESS_TOKEN (Optional)</label>
                                <input type="text" class="form-control" id="jxAccessToken" v-model="formData.JX_ACCESS_TOKEN">
                            </div>
                            <button type="submit" class="btn btn-primary">Save Account</button>
                        </form>
                    </div>
                </div>
            </div>
        </div>
    `
};

const LaunchAccountModal = {
    props: ['show', 'accounts', 'selectedDaemon'],
    emits: ['close', 'launch'],
    setup(props, { emit }) {
        const selectedAccount = ref('');

        const handleSubmit = () => {
            emit('launch', selectedAccount.value, props.selectedDaemon);
        };

        watch(() => props.show, (newShow) => {
            if (newShow) {
                selectedAccount.value = '';
            }
        });

        return { selectedAccount, handleSubmit };
    },
    template: `
        <div v-if="show" class="modal fade show d-block" tabindex="-1" aria-labelledby="launchAccountModalLabel" aria-modal="true">
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title" id="launchAccountModalLabel">Launch Account</h5>
                        <button type="button" class="btn-close" @click="$emit('close')" aria-label="Close"></button>
                    </div>
                    <div class="modal-body">
                        <form @submit.prevent="handleSubmit">
                            <div class="mb-3">
                                <label for="accountSelect" class="form-label">Select Account</label>
                                <select class="form-select" v-model="selectedAccount" required>
                                    <option value="" disabled>Choose an account</option>
                                    <option v-for="(account, nickname) in accounts" :value="nickname" :key="nickname">
                                        {{ nickname }}
                                    </option>
                                </select>
                            </div>
                            <button type="submit" class="btn btn-primary">Launch</button>
                        </form>
                    </div>
                </div>
            </div>
        </div>
    `
};

const app = createApp({
    components: {
        NotificationAlert,
        DaemonsTable,
        AccountsTable,
        LaunchAccountModal,
        AccountModal,
    },
    setup() {
        const { notification, showNotification, closeNotification } = useNotification();
        const { isDarkMode, toggleDarkMode } = useDarkMode();

        const daemons = ref([]);
        const accounts = ref({});
        const selectedDaemonNickname = ref('');
        const showLaunchModal = ref(false);
        const showAccountModal = ref(false);
        const currentAccount = ref(null);

        const fetchDaemons = async () => {
            try {
                daemons.value = await API.fetchDaemons();
            } catch (error) {
                showNotification('danger', 'Failed to load daemons');
            }
        };

        const fetchAccounts = async () => {
            try {
                accounts.value = await API.fetchAccounts();
            } catch (error) {
                showNotification('danger', 'Failed to load accounts');
            }
        };

        const openLaunchModal = (daemonNickname) => {
            selectedDaemonNickname.value = daemonNickname;
            showLaunchModal.value = true;
        };

        const closeLaunchModal = () => {
            showLaunchModal.value = false;
            selectedDaemonNickname.value = '';
        };

        const launchAccount = async (accountId, daemonNickname) => {
            try {
                await API.launchAccount(accountId, daemonNickname);
                showNotification('success', 'Account launched!');
            } catch (error) {
                showNotification('danger', error.message);
            } finally {
                closeLaunchModal();
            }
        };

        const openAccountModal = (nickname = null) => {
            if (nickname) {
                const account = accounts.value[nickname];
                currentAccount.value = { ...account, nickname };
            } else {
                currentAccount.value = null;
            }
            showAccountModal.value = true;
        };

        const closeAccountModal = () => {
            showAccountModal.value = false;
            currentAccount.value = null;
        };

        const saveAccount = async (accountData) => {
            try {
                await API.saveAccount(accountData);
                showNotification('success', 'Account saved!');
                await fetchAccounts();
            } catch (error) {
                showNotification('danger', 'Failed to save account: ' + error.message);
            } finally {
                closeAccountModal();
            }
        };

        const deleteAccount = async (nickname) => {
            if (confirm("Are you sure you want to delete this account?")) {
                try {
                    await API.deleteAccount(nickname);
                    showNotification('success', 'Account deleted!');
                    await fetchAccounts();
                } catch (error) {
                    showNotification('danger', error.message);
                }
            }
        };

        onMounted(() => {
            fetchDaemons();
            fetchAccounts();
        });

        let intervalId;
        onMounted(() => {
            intervalId = setInterval(fetchDaemons, 5000);
        });

        onUnmounted(() => {
            clearInterval(intervalId);
        });

        return {
            daemons,
            accounts,
            selectedDaemonNickname,
            notification,
            showLaunchModal,
            showAccountModal,
            currentAccount,
            closeNotification,
            openLaunchModal,
            closeLaunchModal,
            launchAccount,
            openAccountModal,
            closeAccountModal,
            saveAccount,
            deleteAccount,
            isDarkMode,
            toggleDarkMode
        };
    },
    template: `
        <div>
            <button @click="toggleDarkMode" class="btn btn-outline-secondary mb-3">
                {{ isDarkMode ? 'Light Mode' : 'Dark Mode' }}
            </button>
            <notification-alert :notification="notification" @close="closeNotification" />
            <ul class="nav nav-tabs mb-3">
                <li class="nav-item">
                    <a class="nav-link active" id="daemons-tab" data-bs-toggle="tab" href="#daemons" role="tab" aria-controls="daemons" aria-selected="true">Daemons</a>
                </li>
                <li class="nav-item">
                    <a class="nav-link" id="accounts-tab" data-bs-toggle="tab" href="#accounts" role="tab" aria-controls="accounts" aria-selected="false">Accounts</a>
                </li>
            </ul>
            <div class="tab-content">
                <div class="tab-pane fade show active" id="daemons" role="tabpanel" aria-labelledby="daemons-tab">
                    <h2 class="mb-3">Daemons</h2>
                    <daemons-table :daemons="daemons" @launch="openLaunchModal" />
                </div>
                <div class="tab-pane fade" id="accounts" role="tabpanel" aria-labelledby="accounts-tab">
                    <div class="d-flex justify-content-between align-items-center mb-3">
                        <h2>Accounts</h2>
                        <button class="btn btn-success" @click="openAccountModal()">Add Account</button>
                    </div>
                    <accounts-table :accounts="accounts" @edit="openAccountModal" @delete="deleteAccount" />
                </div>
            </div>
            <launch-account-modal
                :show="showLaunchModal"
                :accounts="accounts"
                :selected-daemon="selectedDaemonNickname"
                @close="closeLaunchModal"
                @launch="launchAccount"
            />
            <account-modal
                :show="showAccountModal"
                :account="currentAccount"
                @close="closeAccountModal"
                @save="saveAccount"
            />
        </div>
    `
});

app.mount('#app-content');
