let metodoCadastro = '';

window.onload = verificaLogin;

function verificaLogin() {
    if (!document.cookie.includes("usuarioLogado=")) {
        window.location.href = 'cadastro.html';
    }
}