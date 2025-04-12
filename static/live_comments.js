// Configuration de l'URL du backend
const BACKEND_URL = window.location.hostname === 'localhost' ?
    'http://localhost:5000' :
    'http://192.168.1.90:5000'; // Ajuster pour déploiement
const WS_URL = BACKEND_URL + '/live';

let token = null;
let tokenExpiration = null;
let hls = null; // Instance HLS globale
let socket = null; // Socket global

// Éléments de l’écran de connexion
const loginScreen = document.getElementById('login-screen');
const emailInput = document.getElementById('email');
const passwordInput = document.getElementById('password');
const loginBtn = document.getElementById('login-btn');
const backBtn = document.getElementById('back-btn');
const loginControls = [emailInput, passwordInput, loginBtn, backBtn];
let loginFocusIndex = 0;

// Éléments de l’écran principal
const video = document.getElementById('live-video');
const channelSelector = document.getElementById('channel-selector');
const playPauseBtn = document.getElementById('play-pause');
const replayBtn = document.getElementById('replay');
const rewindBtn = document.getElementById('rewind');
const forwardBtn = document.getElementById('forward');
const seekBar = document.getElementById('seek-bar');
const muteBtn = document.getElementById('mute');
const volumeBar = document.getElementById('volume-bar');
const fullscreenBtn = document.getElementById('fullscreen');
const newCommentInput = document.getElementById('new-comment');
const sendCommentBtn = document.getElementById('send-comment');
const weatherCityInput = document.getElementById('weather-city');
const weatherSubmitBtn = document.getElementById('weather-submit');
const weatherGeoBtn = document.getElementById('weather-geolocation');
const weatherInfo = document.getElementById('weather-info');

// Éléments du chatbot
const chatbotBtn = document.getElementById('chatbot-btn');
const chatbotModal = document.getElementById('chatbot-modal');
const chatbotClose = document.getElementById('chatbot-close');
const chatbotInput = document.getElementById('chatbot-input');
const chatbotSend = document.getElementById('chatbot-send');
const chatbotMessages = document.getElementById('chatbot-messages');
const chatbotControls = [chatbotInput, chatbotSend, chatbotClose];
let chatbotFocusIndex = 0;

// Regrouper les éléments par section pour une navigation bidimensionnelle
const videoControls = [channelSelector, replayBtn, playPauseBtn, rewindBtn, forwardBtn, muteBtn, volumeBar, fullscreenBtn, chatbotBtn];
const commentControls = [newCommentInput, sendCommentBtn];
const weatherControls = [weatherCityInput, weatherSubmitBtn, weatherGeoBtn];
const controlSections = [videoControls, commentControls, weatherControls];

// Index pour la section et l’élément dans la section
let currentSectionIndex = 0;
let currentElementIndex = 0;

// Fonction pour mettre à jour le focus
function updateFocus() {
    if (chatbotModal && chatbotModal.style.display === 'flex') {
        chatbotControls[chatbotFocusIndex].focus();
    } else if (loginScreen.style.display !== 'none') {
        loginControls[loginFocusIndex].focus();
    } else {
        const currentSection = controlSections[currentSectionIndex];
        const element = currentSection[currentElementIndex];
        element.focus();
    }
}

// Forcer l’ouverture du clavier virtuel sur les Smart TVs
function ensureKeyboardOpens(inputElement) {
    inputElement.addEventListener('focus', () => {
        inputElement.dispatchEvent(new Event('click', { bubbles: true }));
    });
}

// Appliquer à tous les champs de saisie
ensureKeyboardOpens(emailInput);
ensureKeyboardOpens(passwordInput);
ensureKeyboardOpens(newCommentInput);
ensureKeyboardOpens(weatherCityInput);
ensureKeyboardOpens(chatbotInput);

// Gérer le focus après la saisie
newCommentInput.addEventListener('blur', () => {
    currentSectionIndex = 1;
    currentElementIndex = 1; // sendCommentBtn
    updateFocus();
});

weatherCityInput.addEventListener('blur', () => {
    currentSectionIndex = 2;
    currentElementIndex = 1; // weatherSubmitBtn
    updateFocus();
});

emailInput.addEventListener('blur', () => {
    loginFocusIndex = 1; // passwordInput
    loginControls[loginFocusIndex].focus();
});

passwordInput.addEventListener('blur', () => {
    loginFocusIndex = 2; // loginBtn
    loginControls[loginFocusIndex].focus();
});

chatbotInput.addEventListener('blur', () => {
    chatbotFocusIndex = 1; // chatbotSend
    updateFocus();
});

// Détecter la saisie pour débogage
[newCommentInput, weatherCityInput, emailInput, passwordInput, chatbotInput].forEach(input => {
    input.addEventListener('input', () => {
        console.log('Saisie détectée dans', input.id, ':', input.value);
    });
});

// Initialisation du focus
updateFocus();

document.addEventListener('keydown', (e) => {
    if (chatbotModal && chatbotModal.style.display === 'flex') {
        switch (e.key) {
            case 'ArrowUp':
            case 'ArrowLeft':
                chatbotFocusIndex = (chatbotFocusIndex - 1 + chatbotControls.length) % chatbotControls.length;
                updateFocus();
                e.preventDefault();
                break;
            case 'ArrowDown':
            case 'ArrowRight':
                chatbotFocusIndex = (chatbotFocusIndex + 1) % chatbotControls.length;
                updateFocus();
                e.preventDefault();
                break;
            case 'Enter':
                if (chatbotControls[chatbotFocusIndex] === chatbotSend) chatbotSend.click();
                else if (chatbotControls[chatbotFocusIndex] === chatbotClose) chatbotClose.click();
                e.preventDefault();
                break;
            case 'Escape':
                closeChatbotModal();
                e.preventDefault();
                break;
        }
    } else if (loginScreen.style.display !== 'none') {
        switch (e.key) {
            case 'ArrowUp':
                loginFocusIndex = (loginFocusIndex - 1 + loginControls.length) % loginControls.length;
                loginControls[loginFocusIndex].focus();
                e.preventDefault();
                break;
            case 'ArrowDown':
                loginFocusIndex = (loginFocusIndex + 1) % loginControls.length;
                loginControls[loginFocusIndex].focus();
                e.preventDefault();
                break;
            case 'Enter':
                if (loginControls[loginFocusIndex] === loginBtn) loginBtn.click();
                else if (loginControls[loginFocusIndex] === backBtn) backBtn.click();
                e.preventDefault();
                break;
            case 'Escape':
                backBtn.click();
                e.preventDefault();
                break;
        }
    } else {
        const currentSection = controlSections[currentSectionIndex];
        switch (e.key) {
            case 'ArrowLeft':
                currentElementIndex = (currentElementIndex - 1 + currentSection.length) % currentSection.length;
                updateFocus();
                e.preventDefault();
                break;
            case 'ArrowRight':
                currentElementIndex = (currentElementIndex + 1) % currentSection.length;
                updateFocus();
                e.preventDefault();
                break;
            case 'ArrowUp':
                if (currentSectionIndex === 1 && currentSection[currentElementIndex] === newCommentInput) {
                    const commentsContainer = document.getElementById('comments');
                    commentsContainer.scrollTop -= 50;
                } else {
                    currentSectionIndex = (currentSectionIndex - 1 + controlSections.length) % controlSections.length;
                    currentElementIndex = Math.min(currentElementIndex, controlSections[currentSectionIndex].length - 1);
                    updateFocus();
                }
                e.preventDefault();
                break;
            case 'ArrowDown':
                if (currentSectionIndex === 1 && currentSection[currentElementIndex] === newCommentInput) {
                    const commentsContainer = document.getElementById('comments');
                    commentsContainer.scrollTop += 50;
                } else {
                    currentSectionIndex = (currentSectionIndex + 1) % controlSections.length;
                    currentElementIndex = Math.min(currentElementIndex, controlSections[currentSectionIndex].length - 1);
                    updateFocus();
                }
                e.preventDefault();
                break;
            case 'Enter':
                const element = currentSection[currentElementIndex];
                if (element === chatbotBtn) chatbotBtn.click();
                else if (element.tagName !== 'INPUT' && element.tagName !== 'SELECT') element.click();
                e.preventDefault();
                break;
            case 'Escape':
                if (isTokenValid()) {
                    loginScreen.style.display = 'flex';
                    loginControls[0].focus();
                }
                e.preventDefault();
                break;
        }
    }
});

// Fonction pour charger le flux vidéo
function loadVideoStream(channel) {
    fetch(`${BACKEND_URL}/live/stream/${channel}`)
        .then(response => {
            if (!response.ok) throw new Error(`Erreur HTTP : ${response.status}`);
            return response.json();
        })
        .then(data => {
            const streamUrl = data.stream_url;
            console.log('URL du flux récupérée:', streamUrl);

            if (hls) {
                hls.destroy(); // Nettoyer l’instance précédente
                hls = null;
            }

            if (streamUrl.endsWith('.mp4')) {
                video.src = streamUrl;
                video.load();
                video.play().catch(err => console.error('Erreur de lecture MP4:', err));
            } else if (Hls.isSupported()) {
                hls = new Hls();
                hls.loadSource(streamUrl);
                hls.attachMedia(video);
                hls.on(Hls.Events.MANIFEST_PARSED, () => {
                    console.log('Manifest HLS chargé');
                    video.play().catch(err => console.error('Erreur de lecture HLS:', err));
                });
                hls.on(Hls.Events.ERROR, (event, data) => {
                    console.error('Erreur HLS:', data);
                });
            } else if (video.canPlayType('application/vnd.apple.mpegurl')) {
                video.src = streamUrl;
                video.load();
                video.play().catch(err => console.error('Erreur de lecture native:', err));
            } else {
                console.error('HLS non supporté sur cet appareil');
            }
        })
        .catch(error => console.error('Erreur lors de la récupération du flux:', error));
}

// Contrôles vidéo
playPauseBtn.addEventListener('click', () => {
    if (video.paused) {
        video.play();
        playPauseBtn.innerHTML = '<i class="fas fa-pvu"></i>';
    } else {
        video.pause();
        playPauseBtn.innerHTML = '<i class="fas fa-play"></i>';
    }
});

replayBtn.addEventListener('click', () => {
    video.currentTime = 0;
    video.play();
    playPauseBtn.innerHTML = '<i class="fas fa-pause"></i>';
});

rewindBtn.addEventListener('click', () => {
    video.currentTime = Math.max(0, video.currentTime - 10);
});

forwardBtn.addEventListener('click', () => {
    video.currentTime = Math.min(video.duration || Infinity, video.currentTime + 10);
});

video.addEventListener('timeupdate', () => {
    if (video.duration) {
        const value = (video.currentTime / video.duration) * 100;
        seekBar.value = value;
    }
});

seekBar.addEventListener('input', () => {
    if (video.duration) {
        const time = video.duration * (seekBar.value / 100);
        video.currentTime = time;
    }
});

muteBtn.addEventListener('click', () => {
    video.muted = !video.muted;
    muteBtn.innerHTML = video.muted ? '<i class="fas fa-volume-mute"></i>' : '<i class="fas fa-volume-up"></i>';
});

volumeBar.addEventListener('input', () => {
    video.volume = volumeBar.value;
    video.muted = volumeBar.value == 0;
    muteBtn.innerHTML = video.muted ? '<i class="fas fa-volume-mute"></i>' : '<i class="fas fa-volume-up"></i>';
});

fullscreenBtn.addEventListener('click', () => {
    if (!document.fullscreenElement) {
        video.requestFullscreen();
    } else {
        document.exitFullscreen();
    }
});

// Changement de chaîne
channelSelector.addEventListener('change', () => {
    const selectedChannel = channelSelector.value;
    console.log('Changement de chaîne vers:', selectedChannel);
    loadVideoStream(selectedChannel);
});

// Gestion de la connexion
loginBtn.addEventListener('click', () => {
    const email = emailInput.value;
    const password = passwordInput.value;
    fetch(`${BACKEND_URL}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
    })
    .then(response => response.json())
    .then(data => {
        console.log('Réponse login:', data);
        if (data.access_token) {
            token = data.access_token;
            tokenExpiration = new Date(Date.now() + 10 * 60 * 1000);
            console.log('Token expire à:', tokenExpiration);
            loginScreen.style.display = 'none';
            initializeWebSocket(); // Réinitialiser WebSocket avec le nouveau token
            currentSectionIndex = 0;
            currentElementIndex = 0;
            updateFocus();
        } else {
            alert('Échec de la connexion: ' + (data.message || 'Erreur inconnue'));
        }
    })
    .catch(error => console.error('Erreur de connexion:', error));
});

backBtn.addEventListener('click', () => {
    loginScreen.style.display = 'none';
    currentSectionIndex = 0;
    currentElementIndex = 0;
    updateFocus();
});

// Vérifier si le token est valide
function isTokenValid() {
    if (!token || !tokenExpiration) return false;
    return new Date() < tokenExpiration;
}

// Gestion des commentaires
sendCommentBtn.addEventListener('click', () => {
    const commentText = newCommentInput.value.trim();
    if (commentText) {
        if (!isTokenValid()) {
            token = null;
            tokenExpiration = null;
            loginScreen.style.display = 'flex';
            loginControls[0].focus();
        } else {
            sendComment(commentText);
        }
    }
});

function sendComment(commentText) {
    if (commentText && token) {
        if (!socket || !socket.connected) {
            console.warn('WebSocket non connecté. Tentative de reconnexion...');
            initializeWebSocket();
            setTimeout(() => {
                if (socket && socket.connected) {
                    socket.emit('new_comment', { comment: commentText }, (response) => {
                        handleCommentResponse(response);
                    });
                } else {
                    console.warn('WebSocket toujours déconnecté. Envoi via HTTP.');
                    sendCommentViaHttp(commentText);
                }
            }, 1000);
        } else {
            socket.emit('new_comment', { comment: commentText }, (response) => {
                handleCommentResponse(response);
            });
        }
    }
}

function handleCommentResponse(response) {
    if (response && response.error) {
        console.error('Erreur envoi commentaire:', response.error);
        alert(response.error);
    } else {
        newCommentInput.value = '';
        currentSectionIndex = 1;
        currentElementIndex = 0;
        updateFocus();
    }
}

function sendCommentViaHttp(commentText) {
    fetch(`${BACKEND_URL}/live/comment`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ comment: commentText })
    })
    .then(response => {
        if (!response.ok) throw new Error(`Erreur HTTP : ${response.status}`);
        return response.json();
    })
    .then(data => {
        console.log('Commentaire envoyé via HTTP:', data);
        newCommentInput.value = '';
        currentSectionIndex = 1;
        currentElementIndex = 0;
        updateFocus();
    })
    .catch(error => console.error('Erreur envoi commentaire via HTTP:', error));
}

// Gestion de la météo
weatherSubmitBtn.addEventListener('click', () => {
    const city = weatherCityInput.value.trim();
    if (city) {
        console.log('Recherche météo pour la ville:', city);
        fetchWeatherByCity(city);
    } else {
        console.log('Aucune ville saisie');
    }
});

weatherGeoBtn.addEventListener('click', () => {
    console.log('Demande de météo par géolocalisation');
    fetchWeatherByGeolocation();
});

function fetchWeatherByGeolocation() {
    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(
            (position) => {
                const lat = position.coords.latitude;
                const lon = position.coords.longitude;
                console.log('Position obtenue:', { lat, lon });
                fetchWeatherByCoords(lat, lon);
            },
            (error) => {
                console.error('Erreur de géolocalisation:', error);
                weatherInfo.textContent = 'Géolocalisation refusée ou indisponible. Affichage de la météo pour Paris.';
                fetchWeatherByCity('Paris'); // Ville par défaut
            }
        );
    } else {
        console.log('Géolocalisation non supportée par cet appareil.');
        weatherInfo.textContent = 'Géolocalisation non supportée. Affichage de la météo pour Paris.';
        fetchWeatherByCity('Paris'); // Ville par défaut
    }
}

function fetchWeatherByCity(city) {
    const url = `${BACKEND_URL}/weather/local?city=${encodeURIComponent(city)}`;
    console.log('URL fetch ville:', url);
    fetch(url)
    .then(response => {
        if (!response.ok) throw new Error(`Erreur HTTP : ${response.status}`);
        return response.json();
    })
    .then(data => {
        console.log('Météo reçue pour la ville:', data);
        displayWeather(data);
    })
    .catch(error => {
        console.error('Erreur lors de la récupération de la météo:', error);
        weatherInfo.textContent = 'Erreur lors de la récupération de la météo.';
    });
}

function fetchWeatherByCoords(lat, lon) {
    const url = `${BACKEND_URL}/weather/local?lat=${lat}&lon=${lon}`;
    console.log('URL fetch coordonnées:', url);
    fetch(url)
    .then(response => {
        if (!response.ok) throw new Error(`Erreur HTTP : ${response.status}`);
        return response.json();
    })
    .then(data => {
        console.log('Météo reçue pour les coordonnées:', data);
        displayWeather(data);
    })
    .catch(error => {
        console.error('Erreur lors de la récupération de la météo:', error);
        weatherInfo.textContent = 'Erreur lors de la récupération de la météo.';
    });
}

function displayWeather(data) {
    console.log('Affichage de la météo:', data);
    if (!weatherInfo) {
        console.error('Élément #weather-info non trouvé dans le DOM');
        return;
    }
    if (data.error) {
        weatherInfo.textContent = data.error;
    } else {
        weatherInfo.innerHTML = `
            <span>Ville: ${data.city}, ${data.country}</span>
            <span>Température: ${data.temperature}°C</span>
            <span>Description: ${data.description}</span>
            <span>Humidité: ${data.humidity}%</span>
            <span>Vitesse du vent: ${data.wind_speed} m/s</span>
        `;
    }
}

// Gestion du chatbot
chatbotBtn.addEventListener('click', () => {
    if (!isTokenValid()) {
        token = null;
        tokenExpiration = null;
        loginScreen.style.display = 'flex';
        loginControls[0].focus();
    } else {
        openChatbotModal();
    }
});

chatbotClose.addEventListener('click', () => {
    closeChatbotModal();
});

chatbotSend.addEventListener('click', () => {
    const message = chatbotInput.value.trim();
    if (message) {
        sendChatbotMessage(message);
    }
});

function openChatbotModal() {
    chatbotModal.style.display = 'flex';
    chatbotFocusIndex = 0;
    updateFocus();
    fetchChatbotHistory();
}

function closeChatbotModal() {
    chatbotModal.style.display = 'none';
    currentSectionIndex = 0;
    currentElementIndex = 0;
    updateFocus();
}

function addChatbotMessage(message, isUser = false) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${isUser ? 'user-message' : 'bot-message'}`;
    messageDiv.textContent = message;
    chatbotMessages.appendChild(messageDiv);
    chatbotMessages.scrollTop = chatbotMessages.scrollHeight;
}

function sendChatbotMessage(message) {
    if (!isTokenValid()) {
        token = null;
        tokenExpiration = null;
        loginScreen.style.display = 'flex';
        loginControls[0].focus();
        return;
    }
    addChatbotMessage(message, true);
    fetch(`${BACKEND_URL}/chat/send`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ message })
    })
    .then(response => {
        if (!response.ok) throw new Error(`Erreur HTTP : ${response.status}`);
        return response.json();
    })
    .then(data => {
        addChatbotMessage(data.response);
        chatbotInput.value = '';
        chatbotFocusIndex = 0;
        updateFocus();
    })
    .catch(error => {
        console.error('Erreur envoi message chatbot:', error);
        addChatbotMessage('Erreur : impossible de contacter le chatbot.');
    });
}

function fetchChatbotHistory() {
    if (!isTokenValid()) return;
    fetch(`${BACKEND_URL}/chat/history`, {
        headers: { 'Authorization': `Bearer ${token}` }
    })
    .then(response => {
        if (!response.ok) throw new Error(`Erreur HTTP : ${response.status}`);
        return response.json();
    })
    .then(data => {
        chatbotMessages.innerHTML = '';
        data.forEach(conv => {
            conv.messages.forEach(msg => {
                addChatbotMessage(msg.message, true);
                addChatbotMessage(msg.response);
            });
        });
    })
    .catch(error => console.error('Erreur récupération historique:', error));
}

// WebSocket pour les commentaires en temps réel
function initializeWebSocket() {
    if (socket) {
        socket.disconnect();
        socket = null;
    }

    if (typeof io === 'undefined') {
        console.error('Socket.IO non chargé. Chargement dynamique...');
        const script = document.createElement('script');
        script.src = 'https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.7.5/socket.io.js';
        script.onload = setupWebSocket;
        script.onerror = () => {
            console.error('Échec du chargement de Socket.IO. Les commentaires ne seront pas en temps réel.');
        };
        document.head.appendChild(script);
    } else {
        setupWebSocket();
    }
}

function setupWebSocket() {
    socket = io(WS_URL, {
        transports: ['websocket'],
        reconnection: true,
        reconnectionAttempts: 5,
        reconnectionDelay: 1000,
        auth: token ? { token: token } : {}
    });

    socket.on('connect', () => {
        console.log('Connecté au serveur WebSocket, ID:', socket.id);
    });

    socket.on('new_comment', (data) => {
        console.log('Nouveau commentaire reçu:', data);
        addComment(data);
    });

    socket.on('disconnect', () => {
        console.log('Déconnecté du serveur WebSocket');
    });

    socket.on('connect_error', (error) => {
        console.error('Erreur de connexion WebSocket:', error.message);
        setTimeout(() => {
            console.log('Tentative de reconnexion WebSocket...');
            socket.connect();
        }, 5000);
    });

    socket.on('reconnect', (attempt) => {
        console.log('Reconnecté après', attempt, 'tentatives');
    });

    socket.on('reconnect_failed', () => {
        console.error('Échec de la reconnexion au serveur WebSocket');
        alert('Connexion aux commentaires en temps réel perdue. Utilisation du mode HTTP.');
    });

    socket.on('error', (data) => {
        console.error('Erreur WebSocket:', data.message);
        alert(data.message);
    });
}

function fetchInitialComments() {
    fetch(`${BACKEND_URL}/live/comments`, {
        headers: token ? { 'Authorization': `Bearer ${token}` } : {}
    })
    .then(response => {
        if (!response.ok) throw new Error(`Erreur HTTP : ${response.status}`);
        return response.json();
    })
    .then(comments => {
        console.log('Commentaires initiaux chargés:', comments);
        const commentsContainer = document.getElementById('comments');
        commentsContainer.innerHTML = '';
        comments.sort((a, b) => new Date(a.created_at) - new Date(b.created_at));
        comments.forEach(addComment);
    })
    .catch(error => console.error('Erreur chargement commentaires:', error));
}

function addComment(data) {
    const commentsContainer = document.getElementById('comments');
    if (!commentsContainer) {
        console.error('Élément #comments non trouvé dans le DOM');
        return;
    }
    const existingComment = commentsContainer.querySelector(`.comment[data-id="${data.id}"]`);
    if (existingComment) return;

    const commentDiv = document.createElement('div');
    commentDiv.className = 'comment';
    commentDiv.dataset.id = data.id;
    commentDiv.innerHTML = `
        <span class="user">${data.username || 'Anonyme'}</span>
        <span class="time">${new Date(data.created_at).toLocaleString()}</span>
        <span class="text">${data.comment}</span>
    `;
    commentsContainer.appendChild(commentDiv);
    commentsContainer.scrollTop = commentsContainer.scrollHeight;

    const comments = commentsContainer.children;
    if (comments.length > 50) {
        comments[0].remove();
    }
}

// Ajuster la hauteur du conteneur de commentaires lors du redimensionnement
window.addEventListener('resize', () => {
    const commentsContainer = document.getElementById('comments');
    if (commentsContainer) {
        commentsContainer.style.height = 'auto';
        commentsContainer.scrollTop = commentsContainer.scrollHeight;
    }
});

// Initialisation immédiate
initializeWebSocket();

// Initialisation au chargement
window.addEventListener('load', () => {
    console.log('Chargement de la page');
    fetchWeatherByGeolocation(); // Tentative de géolocalisation au démarrage
    fetchInitialComments();
    loadVideoStream(channelSelector.value); // Charger le flux par défaut
    const commentsContainer = document.getElementById('comments');
    if (commentsContainer) {
        commentsContainer.scrollTop = commentsContainer.scrollHeight;
    }
});