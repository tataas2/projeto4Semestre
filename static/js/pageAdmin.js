// pageAdmin.js — mover pedidos entre colunas e atualizar status no banco

// Torna os cards arrastáveis
document.querySelectorAll(".pedido-card").forEach(card => {
    card.draggable = true;
    card.addEventListener("dragstart", e => {
        const idTexto = card.querySelector("b").textContent.trim(); // ex: "#21"
        const id = idTexto.replace("#", "");
        e.dataTransfer.setData("id", id);
    });
});

// Permite soltar nas colunas
document.querySelectorAll(".pedido-list").forEach(area => {
    area.addEventListener("dragover", e => e.preventDefault());

    area.addEventListener("drop", e => {
        const id = e.dataTransfer.getData("id");
        const novoStatus = area.parentElement.dataset.status;

        // Busca o card correspondente pelo número do pedido
        const cards = document.querySelectorAll(".pedido-card");
        const card = Array.from(cards).find(c => 
            c.querySelector("b").textContent.replace("#", "").trim() === id
        );

        if (card) {
            area.appendChild(card);
            atualizarStatusNoBanco(id, novoStatus);
            atualizarContadores();
        }
    });
});

// Atualiza os números nas colunas
function atualizarContadores() {
    document.querySelectorAll(".column").forEach(col => {
        const count = col.querySelectorAll(".pedido-card").length;
        col.querySelector(".count").textContent = count;
    });

    const total = document.querySelectorAll(".pedido-card").length;
    document.getElementById("total-geral").textContent = `Total do Dia: ${total}`;
}

// Faz a requisição ao Flask pra salvar a mudança de status
function atualizarStatusNoBanco(idPedido, novoStatus) {
    fetch("/atualizar_status", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            id_pedido: idPedido,
            novo_status: capitalizarStatus(novoStatus)
        })
    })
    .then(res => res.json())
    .then(data => {
        console.log("✅ Status atualizado:", data);
    })
    .catch(err => {
        console.error("❌ Erro ao atualizar status:", err);
    });
}

// Coloca a primeira letra do status em maiúsculo
function capitalizarStatus(status) {
    return status.charAt(0).toUpperCase() + status.slice(1).toLowerCase();
}

// Atualiza os contadores ao carregar a página
atualizarContadores();
