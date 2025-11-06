let pedidos = Array.isArray(JSON.parse(localStorage.getItem("pedidos"))) ? JSON.parse(localStorage.getItem("pedidos")) : [];

function salvar() {
    localStorage.setItem("pedidos", JSON.stringify(pedidos));
}

function atualizarContadores() {
    document.querySelectorAll(".column").forEach(col => {
        const status = col.dataset.status;
        const total = pedidos.filter(p => p.status === status).length;
        col.querySelector(".count").textContent = total;
    });

    document.getElementById("total-geral").textContent = `Total do Dia: ${pedidos.length}`;
}

function desenhar() {
    document.querySelectorAll(".pedido-list").forEach(list => list.innerHTML = "");

    pedidos.forEach(p => {
        const div = document.createElement("div");
        div.classList.add("pedido");
        div.textContent = p.nome;
        div.draggable = true;
        div.dataset.id = p.id;

        div.addEventListener("dragstart", e => {
            e.dataTransfer.setData("id", p.id);
        });

        document.querySelector(`[data-status="${p.status}"] .pedido-list`).appendChild(div);
    });

    atualizarContadores();
}

document.getElementById("add-btn").onclick = () => {
    const input = document.getElementById("pedido-input");
    if (!input.value.trim()) return;

    pedidos.push({
        id: Date.now(),
        nome: input.value.trim(),
        status: "solicitado"
    });

    input.value = "";
    salvar();
    desenhar();
};

document.querySelectorAll(".pedido-list").forEach(area => {
    area.addEventListener("dragover", e => e.preventDefault());
    area.addEventListener("drop", e => {
        const id = e.dataTransfer.getData("id");
        const pedido = pedidos.find(p => p.id == id);
        pedido.status = area.parentElement.dataset.status;
        salvar();
        desenhar();
    });
});
localStorage.removeItem("pedidos");

desenhar();
