// --- ChatService: Gerencia a conexão Socket.IO (Singleton) ---
// Usamos uma verificação global para evitar redeclaração se o script for reinjetado.
if (typeof window.ChatService === 'undefined') {
    window.ChatService = class ChatService {
        constructor() {
            if (window.ChatService.instance) {
                return window.ChatService.instance;
            }

            console.log("[ChatService] Inicializando serviço...");
            this.socket = null;
            this.listeners = new Map(); // Map<EventName, Set<Callback>>
            this.chatId = null;
            this.isConnected = false;

            window.ChatService.instance = this;
        }

        connect(chatId) {
        this.chatId = chatId;

        // Se já existe socket, verificar estado
        if (this.socket) {
            if (this.socket.connected) {
                console.log("[ChatService] Socket já conectado. Reutilizando.");
                this.joinRoom(); // Garante que estamos na sala certa
                return;
            } else {
                console.log("[ChatService] Socket desconectado. Reconectando...");
                this.socket.connect();
                return;
            }
        }

        console.log("[ChatService] Criando nova conexão Socket.IO...");
        // forceNew: true garante uma conexão limpa se houve problemas anteriores,
        // mas como gerenciamos o singleton, podemos usar padrão ou forceNew.
        // Vamos usar padrão para evitar overhead, já que gerenciamos o objeto.
        this.socket = io({
            reconnection: true,
            reconnectionAttempts: 5,
            reconnectionDelay: 1000
        });

        this._setupInternalListeners();
    }

    disconnect() {
        if (this.socket) {
            console.log("[ChatService] Desconectando socket...");
            this.socket.disconnect();
            this.socket = null;
            this.isConnected = false;
        }
    }

    _setupInternalListeners() {
        this.socket.on('connect', () => {
            console.log("[ChatService] Conectado!");
            this.isConnected = true;
            this.joinRoom();
        });

        this.socket.on('disconnect', () => {
            console.log("[ChatService] Desconectado.");
            this.isConnected = false;
        });

        // Eventos de Negócio
        this.socket.on('new_general_message', (msg) => this.notify('general_message', msg));
        this.socket.on('new_private_message', (msg) => this.notify('private_message', msg));

        // Histórico
        this.socket.on('general_messages_history', (data) => this.notify('history_general', data));
        this.socket.on('private_messages_history', (data) => this.notify('history_private', data));

        // Erros
        this.socket.on('error', (data) => this.notify('error', data));

        // Lista de Usuários
        this.socket.on('update_user_list', (data) => this.notify('user_list_update', data));
        this.socket.on('update_online_users', (data) => this.notify('online_users_update', data));
    }

        joinRoom() {
            if (!this.socket || !this.chatId) return;
            console.log(`[ChatService] Entrando na sala ${this.chatId}...`);
            this.socket.emit('join', { chat_id: this.chatId });
            this.loadGeneralHistory();
        }

    loadGeneralHistory() {
        if (this.socket && this.chatId) {
            console.log("[ChatService] Solicitando histórico geral...");
            this.socket.emit('load_general_messages', { chat_id: this.chatId });
        }
    }

    loadPrivateHistory(targetUsername) {
        if (this.socket && this.chatId) {
            const myUsername = window.myUsername;
            this.socket.emit('load_private_messages', {
                myUsername: myUsername,
                target_username: targetUsername,
                chat_id: this.chatId
            });
        }
    }

    sendGeneralMessage(content) {
        if (!this.socket) return;
        const myUsername = window.myUsername;
        this.socket.emit('general_message', {
            username: myUsername,
            chat_id: this.chatId,
            content: content
        });
    }

    sendPrivateMessage(targetUsername, content) {
        if (!this.socket) return;
        const myUsername = window.myUsername;
        this.socket.emit('private_message', {
            username: myUsername,
            target_username: targetUsername,
            content: content,
            chat_id: this.chatId
        });
    }

    // --- Sistema de Pub/Sub para a UI ---
    subscribe(event, callback) {
        if (!this.listeners.has(event)) {
            this.listeners.set(event, new Set());
        }
        this.listeners.get(event).add(callback);
    }

    unsubscribe(event, callback) {
        if (this.listeners.has(event)) {
            this.listeners.get(event).delete(callback);
        }
    }

        notify(event, data) {
            if (this.listeners.has(event)) {
                this.listeners.get(event).forEach(cb => cb(data));
            }
        }
    };
}

// --- ChatUI: Gerencia o DOM e Interação (View) ---
if (typeof window.ChatUI === 'undefined') {
    window.ChatUI = class ChatUI {
        constructor() {
            this.service = new window.ChatService(); // Pega o singleton
            this.myUsername = window.myUsername;
            this.myUserId = window.myUserId;
        this.openPrivateChats = new Set();

        // Elementos DOM (assumindo que o HTML já foi injetado)
        this.dom = {
            userList: document.getElementById('user-list'),
            tabsList: document.getElementById('chat-tabs-list'),
            tabsContent: document.getElementById('chat-tabs-content'),
            form: document.getElementById('chatForm'),
            input: document.getElementById('myMessage')
        };

        // Bindings para não perder o 'this'
        this.handleUserClick = this.handleUserClick.bind(this);
        this.handleTabClose = this.handleTabClose.bind(this);
        this.handleSubmit = this.handleSubmit.bind(this);

        // Callbacks do Service
        this.onGeneralMessage = this.onGeneralMessage.bind(this);
        this.onPrivateMessage = this.onPrivateMessage.bind(this);
        this.onHistoryGeneral = this.onHistoryGeneral.bind(this);
        this.onHistoryPrivate = this.onHistoryPrivate.bind(this);
        this.onUserListUpdate = this.onUserListUpdate.bind(this);
        this.onOnlineUsersUpdate = this.onOnlineUsersUpdate.bind(this);
        this.onError = this.onError.bind(this);
    }

    init() {
        if (!this.dom.tabsList || !this.dom.tabsContent) {
            console.error("[ChatUI] Elementos DOM não encontrados!");
            return;
        }

        console.log("[ChatUI] Inicializando UI...");
        this.buildInitialLayout();
        this.attachDOMListeners();
        this.subscribeToService();
    }

    destroy() {
        console.log("[ChatUI] Destruindo UI e limpando listeners...");
        this.detachDOMListeners();
        this.unsubscribeFromService();
        // Não desconectamos o service, pois ele pode manter a conexão viva se desejado,
        // ou o show_session.js pode chamar service.disconnect() explicitamente.
    }

    buildInitialLayout() {
        // Aba Geral Padrão
        this.dom.tabsList.innerHTML = `
            <li class="nav-item">
                <button class="nav-link active" id="tab-btn-geral" data-bs-toggle="tab" data-bs-target="#tab-pane-geral" type="button" role="tab">Geral</button>
            </li>`;
        this.dom.tabsContent.innerHTML = `
            <div class="tab-pane fade show active" id="tab-pane-geral" role="tabpanel">
                <ul class="list-unstyled overflow-auto chat-messages" style="height: 60vh;"></ul>
            </div>`;

        // Mostrar Loading no Geral imediatamente
        this.showLoading('tab-pane-geral');
    }

    attachDOMListeners() {
        this.dom.userList.addEventListener('click', this.handleUserClick);
        this.dom.tabsList.addEventListener('click', this.handleTabClose);
        this.dom.form.addEventListener('submit', this.handleSubmit);
    }

    detachDOMListeners() {
        if (this.dom.userList) this.dom.userList.removeEventListener('click', this.handleUserClick);
        if (this.dom.tabsList) this.dom.tabsList.removeEventListener('click', this.handleTabClose);
        if (this.dom.form) this.dom.form.removeEventListener('submit', this.handleSubmit);
    }

    subscribeToService() {
        this.service.subscribe('general_message', this.onGeneralMessage);
        this.service.subscribe('private_message', this.onPrivateMessage);
        this.service.subscribe('history_general', this.onHistoryGeneral);
        this.service.subscribe('history_private', this.onHistoryPrivate);
        this.service.subscribe('user_list_update', this.onUserListUpdate);
        this.service.subscribe('online_users_update', this.onOnlineUsersUpdate);
        this.service.subscribe('error', this.onError);
    }

    unsubscribeFromService() {
        this.service.unsubscribe('general_message', this.onGeneralMessage);
        this.service.unsubscribe('private_message', this.onPrivateMessage);
        this.service.unsubscribe('history_general', this.onHistoryGeneral);
        this.service.unsubscribe('history_private', this.onHistoryPrivate);
        this.service.unsubscribe('user_list_update', this.onUserListUpdate);
        this.service.unsubscribe('online_users_update', this.onOnlineUsersUpdate);
        this.service.unsubscribe('error', this.onError);
    }

    // --- Lógica de UI ---

    handleUserClick(e) {
        const userItem = e.target.closest('[data-user-id]');
        if (userItem) {
            const targetUsername = userItem.dataset.userName;
            this.openPrivateChatTab(targetUsername);
        }
    }

    handleTabClose(e) {
        if (e.target.classList.contains('btn-close')) {
            e.stopPropagation();
            const targetUsername = e.target.dataset.userId; // Dataset armazena o username no HTML gerado
            this.closePrivateChatTab(targetUsername);
        }
    }

    handleSubmit(e) {
        e.preventDefault();
        const msg = this.dom.input.value.trim();
        if (!msg) return;

        const activeTab = this.dom.tabsList.querySelector('.nav-link.active');
        if (!activeTab) return;

        if (activeTab.id === 'tab-btn-geral') {
            this.service.sendGeneralMessage(msg);
        } else {
            const targetUsername = activeTab.textContent.trim(); // Simplificado, ou pegar do ID
            // O ID do botão é tab-btn-{username}
            const targetUserFromId = activeTab.id.replace('tab-btn-', '');
            this.service.sendPrivateMessage(targetUserFromId, msg);
        }
        this.dom.input.value = "";
    }

    openPrivateChatTab(targetUsername) {
        if (targetUsername === this.myUsername || this.openPrivateChats.has(targetUsername)) {
            // Foca na aba existente se já aberta
            const existingBtn = document.getElementById(`tab-btn-${targetUsername}`);
            if (existingBtn) {
                const tab = new bootstrap.Tab(existingBtn);
                tab.show();
            }
            return;
        }

        console.log(`[ChatUI] Abrindo aba privada para: ${targetUsername}`);

        // Botão da Aba
        const li = document.createElement('li');
        li.className = 'nav-item';
        li.innerHTML = `
            <button class="nav-link" id="tab-btn-${targetUsername}" data-bs-toggle="tab" data-bs-target="#tab-pane-${targetUsername}" type="button" role="tab">
                ${targetUsername}
                <span class="btn-close btn-close-sm ms-2" data-user-id="${targetUsername}"></span>
            </button>
        `;
        this.dom.tabsList.appendChild(li);

        // Conteúdo da Aba
        const div = document.createElement('div');
        div.className = 'tab-pane fade';
        div.id = `tab-pane-${targetUsername}`;
        div.role = 'tabpanel';
        div.innerHTML = `<ul class="list-unstyled overflow-auto chat-messages" style="height: 60vh;"></ul>`;
        this.dom.tabsContent.appendChild(div);

        this.openPrivateChats.add(targetUsername);

        // Ativar a nova aba
        const newTab = new bootstrap.Tab(li.querySelector('button'));
        newTab.show();

        // Mostrar Loading na nova aba privada
        this.showLoading(`tab-pane-${targetUsername}`);

        // Carregar histórico
        this.service.loadPrivateHistory(targetUsername);
    }

    closePrivateChatTab(targetUsername) {
        console.log(`[ChatUI] Fechando aba de: ${targetUsername}`);
        const btn = document.getElementById(`tab-btn-${targetUsername}`);
        const pane = document.getElementById(`tab-pane-${targetUsername}`);

        if (btn) btn.parentElement.remove();
        if (pane) pane.remove();

        this.openPrivateChats.delete(targetUsername);

        // Voltar para Geral
        const geralBtn = document.getElementById('tab-btn-geral');
        if (geralBtn) {
            const tab = new bootstrap.Tab(geralBtn);
            tab.show();
        }
    }

    addMessageToPane(paneId, message) {
        const pane = document.getElementById(paneId);
        if (!pane) return; // UI não pronta ou aba fechada

        const ul = pane.querySelector('.chat-messages');
        if (!ul) return;

        // Se houver indicador de loading ou "sem mensagens", removemos
        const indicators = ul.querySelectorAll('.loading-indicator, .no-messages-indicator');
        indicators.forEach(el => el.remove());

        const li = document.createElement('li');
        const isMyMessage = message.username === this.myUsername;

        if (message.content && message.content.includes("aviso -")) {
            li.className = `d-flex flex-column my-2 item-warning align-items-center green`;
            li.innerHTML = `<span class="badge bg-info text-dark">${message.content.replace("aviso - ", "")}</span>`;
        } else {
            li.className = `d-flex flex-column my-2 ${isMyMessage ? 'align-items-end' : 'align-items-start'}`;
            li.innerHTML = `
                <div class="m-2 p-2 rounded message ${isMyMessage ? 'bg-primary text-white' : 'bg-light border'}">
                    <strong class="d-block small ${isMyMessage ? 'text-white-50' : 'text-muted'}">${message.username}</strong>
                    <span>${message.content}</span>
                </div>
            `;
        }
        ul.appendChild(li);
        ul.scrollTop = ul.scrollHeight;
    }

    // --- Handlers de Eventos do Service ---

    onGeneralMessage(msg) {
        this.addMessageToPane('tab-pane-geral', msg);
    }

    onPrivateMessage(msg) {
        // Lógica: se recebi mensagem de X, abro a aba de X se não existir
        const sender = msg.username;
        const target = msg.target_username;

        // Verifica se a mensagem é para mim ou enviada por mim
        if (sender !== this.myUsername && target !== this.myUsername) {
            return;
        }

        let chatPartner = (sender === this.myUsername) ? target : sender;

        // Se a aba não existe, abre
        if (!this.openPrivateChats.has(chatPartner)) {
            this.openPrivateChatTab(chatPartner);
        }

        this.addMessageToPane(`tab-pane-${chatPartner}`, msg);
    }

    onHistoryGeneral(data) {
        console.log("[ChatUI] Histórico geral recebido.", data);
        const pane = document.getElementById('tab-pane-geral');
        if (pane) {
            const ul = pane.querySelector('.chat-messages');
            if (ul) {
                ul.innerHTML = ''; // Limpa loading
                if (data.messages && data.messages.length > 0) {
                    data.messages.forEach(msg => this.addMessageToPane('tab-pane-geral', msg));
                } else {
                    this.showNoMessages('tab-pane-geral');
                }
            }
        }
    }

    onError(data) {
        console.error("[ChatUI] Erro recebido:", data);
        const pane = document.getElementById('tab-pane-geral');
        if (pane) {
            const ul = pane.querySelector('.chat-messages');
            if (ul && ul.querySelector('.loading-indicator')) {
                this.showNoMessages('tab-pane-geral');
            }
        }
    }

    onHistoryPrivate(data) {
        // data = { target_username, with_user_id, messages: [] }
        const partner = data.target_username; // Quem eu estou conversando

        const paneId = `tab-pane-${partner}`;
        const pane = document.getElementById(paneId);
        if (pane) {
            const ul = pane.querySelector('.chat-messages');
            if (ul) {
                ul.innerHTML = ''; // Limpa loading
                if (data.messages && data.messages.length > 0) {
                    data.messages.forEach(msg => this.addMessageToPane(paneId, msg));
                } else {
                    this.showNoMessages(paneId);
                }
            }
        }
    }

    showLoading(paneId) {
        const pane = document.getElementById(paneId);
        if (!pane) return;
        const ul = pane.querySelector('.chat-messages');
        if (!ul) return;

        ul.innerHTML = `
            <li class="text-center my-5 loading-indicator">
                <div class="spinner-border text-primary" role="status" style="width: 3rem; height: 3rem;">
                    <span class="visually-hidden">Carregando...</span>
                </div>
                <p class="mt-2 text-muted animate-pulse">Carregando mensagens...</p>
            </li>
        `;
    }

    showNoMessages(paneId) {
        const pane = document.getElementById(paneId);
        if (!pane) return;
        const ul = pane.querySelector('.chat-messages');
        if (!ul) return;

        ul.innerHTML = `
            <li class="text-center my-5 no-messages-indicator">
                <i class="bi bi-chat-square-dots display-1 text-muted opacity-25"></i>
                <p class="mt-3 text-muted">Sem mensagens.</p>
            </li>
        `;
    }

        onUserListUpdate(userListDataString) {
            try {
                const users = JSON.parse(userListDataString);
                this.dom.userList.innerHTML = '';

                users.forEach(user => {
                    if (user.username === this.myUsername) return; // Não mostrar a si mesmo

                    const a = document.createElement('a');
                    a.href = '#';
                    a.className = 'list-group-item list-group-item-action d-flex justify-content-between align-items-center';
                    a.dataset.userId = user.id;
                    a.dataset.userName = user.username;

                    // Indicador de Status (padrão vermelho/offline)
                    // Usaremos um span com classe para manipular a cor
                    a.innerHTML = `
                        <span>${user.username} <small class="text-muted">(${user.type})</small></span>
                        <span class="status-indicator rounded-circle bg-danger border border-light"
                              style="width: 12px; height: 12px; display: inline-block; box-shadow: 0 0 2px #000;"
                              title="Offline">
                        </span>
                    `;

                    this.dom.userList.appendChild(a);
                });
            } catch (e) {
                console.error("Erro ao processar lista de usuários:", e);
            }
        }

        onOnlineUsersUpdate(onlineUserIds) {
            // onlineUserIds é uma lista de IDs [1, 4, 10, ...]
            if (!this.dom.userList) return;

            // Converter para Set para busca rápida (IDs podem vir como strings ou numbers do JSON)
            const onlineSet = new Set(onlineUserIds.map(id => String(id)));

            // Iterar sobre a lista DOM
            const userItems = this.dom.userList.querySelectorAll('[data-user-id]');
            userItems.forEach(item => {
                const userId = item.dataset.userId;
                const indicator = item.querySelector('.status-indicator');

                if (indicator) {
                    if (onlineSet.has(String(userId))) {
                        // Online: Verde Brilhante
                        indicator.className = 'status-indicator rounded-circle bg-success border border-light';
                        indicator.style.boxShadow = '0 0 8px #0f0'; // Brilho verde
                        indicator.title = "Online";
                    } else {
                        // Offline: Vermelho
                        indicator.className = 'status-indicator rounded-circle bg-danger border border-light';
                        indicator.style.boxShadow = 'none';
                        indicator.title = "Offline";
                    }
                }
            });
        }
    };
}

// --- Função Global de Inicialização ---
// Esta função é chamada pelo show_session.js quando o fragmento é carregado.
// Retorna a instância da UI para que o chamador possa destruí-la depois.

function initializeChatComponent() {
    // 1. Inicializa o Singleton do Service (se não existir) e conecta
    const service = new window.ChatService();
    service.connect(window.chatId);

    // 2. Inicializa a UI
    const ui = new window.ChatUI();
    ui.init();

    // 3. Retorna o objeto UI para controle de lifecycle externo
    return ui;
}
