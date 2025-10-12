let metodoCadastro = '';
let validador = null;

window.onload = loginCadastro;

function loginCadastro() {
    if (document.cookie.includes("usuarioLogado=")) {
        window.location.href = 'index.html';
    }

    if (globalThis.metodoCadastro) {
        const anterior = document.getElementById(globalThis.metodoCadastro);
        if (anterior) anterior.style.display = 'none';
    } else {
        globalThis.metodoCadastro = 'cadastro';
    }

    if (globalThis.validador == 1) {
        globalThis.metodoCadastro = 'login';
    } else if (globalThis.validador == 2) {
        globalThis.metodoCadastro = 'cadastro';
    } else {
        globalThis.metodoCadastro = 'login';
    }

    const atual = document.getElementById(globalThis.metodoCadastro);
    if (atual) atual.style.display = 'flex';
}

function cadastroPLogin() {
    globalThis.validador = 1;
    loginCadastro();
}

function loginPCadastro() {
    globalThis.validador = 2;
    loginCadastro();
}

function salvaLogin() {
    setCookie("usuarioLogado", "true", 3);
    loginCadastro();
}

function setCookie(nome, valor, horas) {
    const data = new Date();
    data.setTime(data.getTime() + (horas * 60 * 60 * 1000));
    const expires = "expires=" + data.toUTCString();
    document.cookie = `${nome}=${valor}; ${expires}; path=/`;
}