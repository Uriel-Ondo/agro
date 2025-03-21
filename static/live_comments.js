let token = null;
let tokenExpiration = null;

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
// Éléments météo
const weatherCityInput = document.getElementById('weather-city');
const weatherSubmitBtn = document.getElementById('weather-submit');
const weatherGeoBtn = document.getElementById('weather-geolocation');
const weatherInfo = document.getElementById('weather-info');

// Regrouper les éléments par section pour une navigation bidimensionnelle
const videoControls = [replayBtn, playPauseBtn, rewindBtn, forwardBtn, muteBtn, volumeBar, fullscreenBtn];
const commentControls = [newCommentInput, sendCommentBtn];
const weatherControls = [weatherCityInput, weatherSubmitBtn, weatherGeoBtn];
const controlSections = [videoControls, commentControls, weatherControls];

// Index pour la section et l'élément dans la section
let currentSectionIndex = 0;
let currentElementIndex = 0;

// Fonction pour mettre à jour le focus
function updateFocus() {
    const currentSection = controlSections[currentSectionIndex];
    const element = currentSection[currentElementIndex];
    element.focus();
}

// Forcer l'ouverture du clavier virtuel sur les Smart TVs
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

// Détecter la saisie pour débogage
[newCommentInput, weatherCityInput, emailInput, passwordInput].forEach(input => {
    input.addEventListener('input', () => {
        console.log('Saisie détectée dans', input.id, ':', input.value);
    });
});

// Initialisation du focus
updateFocus();

document.addEventListener('keydown', (e) => {
    if (loginScreen.style.display !== 'none') {
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
                if (element.tagName !== 'INPUT') {
                    element.click();
                }
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

// Contrôles vidéo
playPauseBtn.addEventListener('click', () => {
    if (video.paused) {
        video.play();
        playPauseBtn.innerHTML = '<i class="fas fa-pause"></i>';
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
    video.currentTime = Math.min(video.duration, video.currentTime + 10);
});

video.addEventListener('timeupdate', () => {
    const value = (video.currentTime / video.duration) * 100;
    seekBar.value = value;
});

seekBar.addEventListener('input', () => {
    const time = video.duration * (seekBar.value / 100);
    video.currentTime = time;
});

muteBtn.addEventListener('click', () => {
    video.muted = !video.muted;
    muteBtn.innerHTML = video.muted ? '<i class="fas fa-volume-mute"></i>' : '<i class="fas fa-volume-up"></i>';
});

volumeBar.addEventListener('input', () => {
    video.volume = volumeBar.value;
    video.muted = volumeBar.value === 0;
    muteBtn.innerHTML = video.muted ? '<i class="fas fa-volume-mute"></i>' : '<i class="fas fa-volume-up"></i>';
});

fullscreenBtn.addEventListener('click', () => {
    if (!document.fullscreenElement) {
        video.requestFullscreen();
    } else {
        document.exitFullscreen();
    }
});

// Gestion de la connexion
loginBtn.addEventListener('click', () => {
    const email = emailInput.value;
    const password = passwordInput.value;
    fetch('http://localhost:5000/auth/login', {
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
            sendComment();
        }
    }
});

function sendComment() {
    const commentText = newCommentInput.value.trim();
    if (commentText && token) {
        if (!socket || !socket.connected) {
            console.error('WebSocket non connecté. Tentative de reconnexion...');
            initializeWebSocket();
            const waitForConnection = setInterval(() => {
                if (socket && socket.connected) {
                    clearInterval(waitForConnection);
                    sendCommentRequest(commentText);
                }
            }, 500);
            setTimeout(() => {
                clearInterval(waitForConnection);
                if (!socket || !socket.connected) {
                    console.error('Échec de la reconnexion WebSocket. Envoi du commentaire sans mise à jour en temps réel.');
                    sendCommentRequest(commentText);
                }
            }, 5000);
        } else {
            sendCommentRequest(commentText);
        }
    }
}

function sendCommentRequest(commentText) {
    fetch('http://localhost:5000/live/comment', {
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
        console.log('Réponse envoi commentaire:', data);
        if (data.message === "Commentaire ajouté") {
            newCommentInput.value = '';
            tokenExpiration = new Date(Date.now() + 10 * 60 * 1000);
            console.log('Token expiration mise à jour à:', tokenExpiration);
            if (!socket || !socket.connected) {
                fetch('http://localhost:5000/auth/me', {
                    headers: {
                        'Authorization': `Bearer ${token}`
                    }
                })
                .then(response => response.json())
                .then(userData => {
                    const commentData = {
                        username: userData.username || 'Vous',
                        comment: commentText,
                        created_at: new Date().toISOString(),
                        isLocal: true
                    };
                    addComment(commentData);
                })
                .catch(error => {
                    console.error('Erreur lors de la récupération du nom d’utilisateur:', error);
                    const commentData = {
                        username: 'Vous',
                        comment: commentText,
                        created_at: new Date().toISOString(),
                        isLocal: true
                    };
                    addComment(commentData);
                });
            }
            currentSectionIndex = 1;
            currentElementIndex = 0;
            updateFocus();
        }
    })
    .catch(error => console.error('Erreur lors de l’envoi du commentaire:', error));
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
                weatherInfo.textContent = 'Impossible d’obtenir votre position.';
            }
        );
    } else {
        weatherInfo.textContent = 'Géolocalisation non supportée par votre appareil.';
    }
}

function fetchWeatherByCity(city) {
    const url = `http://localhost:5000/weather/local?city=${encodeURIComponent(city)}`;
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
    const url = `http://localhost:5000/weather/local?lat=${lat}&lon=${lon}`;
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
            <span>Température: ${data.temperature}°C</span>
            <span>Description: ${data.description}</span>
            <span>Humidité: ${data.humidity}%</span>
            <span>Vitesse du vent: ${data.wind_speed} m/s</span>
        `;
    }
}

// WebSocket pour les commentaires en temps réel
let socket;

function initializeWebSocket() {
    if (typeof io === 'undefined') {
        console.error('Socket.IO non chargé. Vérifiez la balise <script> dans live_comments.html');
        const script = document.createElement('script');
        script.src = 'https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.7.4/socket.io.js';
        script.onload = () => {
            console.log('Socket.IO chargé avec succès via fallback');
            setupWebSocket();
        };
        script.onerror = () => {
            console.error('Échec du chargement de Socket.IO via fallback. Les commentaires ne seront pas en temps réel.');
        };
        document.head.appendChild(script);
    } else {
        setupWebSocket();
    }
}

function setupWebSocket() {
    socket = io('http://localhost:5000/live', {
        transports: ['websocket'],
        reconnection: true,
        reconnectionAttempts: 5,
        reconnectionDelay: 1000
    });

    socket.on('connect', () => {
        console.log('Connecté au serveur WebSocket');
        console.log('Socket ID:', socket.id);
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
    });

    socket.on('reconnect', (attempt) => {
        console.log('Reconnecté après', attempt, 'tentatives');
    });

    socket.on('reconnect_failed', () => {
        console.error('Échec de la reconnexion au serveur WebSocket');
    });

    socket.on('message', (msg) => {
        console.log('Message WebSocket reçu:', msg);
    });
}

function fetchInitialComments() {
    fetch('http://localhost:5000/live/comments')
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
    const existingComments = Array.from(commentsContainer.children);
    const commentExists = existingComments.some(comment => {
        const text = comment.querySelector('.text').textContent;
        const time = comment.querySelector('.time').textContent;
        return text === data.comment && time === new Date(data.created_at).toLocaleString();
    });
    if (commentExists) return;

    const commentDiv = document.createElement('div');
    commentDiv.className = 'comment';
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

// Initialisation immédiate du WebSocket
initializeWebSocket();

// Initialisation au chargement pour le reste
window.addEventListener('load', () => {
    console.log('Chargement de la page');
    fetchWeatherByGeolocation();
    fetchInitialComments();
    const commentsContainer = document.getElementById('comments');
    if (commentsContainer) {
        commentsContainer.scrollTop = commentsContainer.scrollHeight;
    }
});