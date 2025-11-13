document.addEventListener('DOMContentLoaded', () => {
    let carrinho = [];
    const frete = 5;

    const listaCarrinho = document.getElementById("listaCarrinho");
    const totalCarrinho = document.getElementById("totalCarrinho");
    const valorEntrega = document.getElementById("valorEntrega");
    const totalFinal = document.getElementById("totalFinal");

    // Atualiza a lista e os totais do carrinho
    function atualizarCarrinho() {
        listaCarrinho.innerHTML = "";
        let total = 0;

        carrinho.forEach((item, index) => {
            total += item.preco * item.qtd;

            const li = document.createElement("li");
            li.innerHTML = `
                ${item.nome} - R$ ${item.preco.toFixed(2)} x ${item.qtd} = R$ ${(item.preco * item.qtd).toFixed(2)}
                <button onclick="alterarQtd(${index}, -1)">-</button>
                <button onclick="alterarQtd(${index}, 1)">+</button>
                <button onclick="removerItem(${index})">🗑️</button>
            `;
            listaCarrinho.appendChild(li);
        });

        totalCarrinho.textContent = total.toFixed(2);
        valorEntrega.textContent = frete.toFixed(2);
        totalFinal.textContent = (total + frete).toFixed(2);
    }

    // Adiciona item ao carrinho
    window.adicionarAoCarrinho = (id, nome, preco) => {
        // Verifica se item já existe
        const existingIndex = carrinho.findIndex(i => i.nome === nome);
        if (existingIndex >= 0) {
            carrinho[existingIndex].qtd += 1;
        } else {
            carrinho.push({ nome, preco, qtd: 1 });
        }
        atualizarCarrinho();

        // Abre o carrinho
        document.getElementById("carrinhoAside").classList.add("aberto");
        document.getElementById("openCarrinhoBtn").style.display = "none";
        document.getElementById("closeCarrinhoBtn").classList.add("mostrar");
    };

    // Alterar quantidade
    window.alterarQtd = (index, delta) => {
        carrinho[index].qtd += delta;
        if (carrinho[index].qtd <= 0) carrinho.splice(index, 1);
        atualizarCarrinho();
    };

    // Remover item
    window.removerItem = (index) => {
        carrinho.splice(index, 1);
        atualizarCarrinho();
    };

    // Abrir/fechar carrinho
    document.getElementById("openCarrinhoBtn").onclick = () => {
        document.getElementById("carrinhoAside").classList.add("aberto");
        document.getElementById("openCarrinhoBtn").style.display = "none";
        document.getElementById("closeCarrinhoBtn").classList.add("mostrar");
    };

    document.getElementById("closeCarrinhoBtn").onclick = () => {
        document.getElementById("carrinhoAside").classList.remove("aberto");
        document.getElementById("closeCarrinhoBtn").classList.remove("mostrar");
        document.getElementById("openCarrinhoBtn").style.display = "block";
    };

    // Buscar endereço via CEP
    document.getElementById("buscarCEP").onclick = () => {
        const cep = document.getElementById("cepInput").value.replace(/\D/g, "");
        const numero = document.getElementById("numeroInput").value;
        if (cep.length !== 8) return alert("Digite um CEP válido.");

        fetch(`https://viacep.com.br/ws/${cep}/json/`)
            .then(r => r.json())
            .then(data => {
                document.getElementById("enderecoText").textContent =
                    `${data.logradouro}, nº ${numero} - ${data.bairro}, ${data.localidade}/${data.uf}`;
            })
            .catch(() => alert("CEP não encontrado."));
    };

    // Confirmar compra
    document.getElementById("confirmarCompra").onclick = () => {
        if (carrinho.length === 0) return alert("O carrinho está vazio!");

        const total = carrinho.reduce((acc, item) => acc + item.preco * item.qtd, 0);
        const texto = `🦸 Pedido Pizzaria do Stan 🦸\n\n${
            carrinho.map(i => `• ${i.nome} — R$ ${i.preco.toFixed(2)} x ${i.qtd} = R$ ${(i.preco*i.qtd).toFixed(2)}`).join("\n")
        }\n\nEntrega: R$ ${frete.toFixed(2)}\nTotal Final: R$ ${(total+frete).toFixed(2)}`;

        const win = window.open("", "_blank");
        win.document.write(`<pre>${texto}</pre>`);
        win.print();
    };
});
