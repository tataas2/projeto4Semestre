from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
from io import BytesIO
import base64
import os
from db import get_connection
from datetime import date, datetime
import logging


sns.set(style="whitegrid")

app = Flask(
    __name__,
    template_folder=os.path.join(os.path.dirname(__file__), "templates"),
    static_folder=os.path.join(os.path.dirname(__file__), "static")
)

app.secret_key = 'chave_secreta_super_segura'

# Usuário admin
ADMIN_USER = {"nome": "admin", "senha": "admin123"}

# -------------------------
# Função para gerar gráfico
# -------------------------
def gerar_grafico_base64(figura):
    img = BytesIO()
    figura.savefig(img, format='png', bbox_inches='tight')
    img.seek(0)
    grafico_base64 = base64.b64encode(img.getvalue()).decode()
    plt.close(figura)
    return grafico_base64

# -------------------------
# ROTAS
# -------------------------

# LOGIN
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        usuario = request.form.get("usuario") or request.form.get("telefone")
        senha = request.form.get("senha")

        # 🔹 Login do administrador
        if usuario == ADMIN_USER["nome"] and senha == ADMIN_USER["senha"]:
            session["user"] = ADMIN_USER["nome"]
            session["is_admin"] = True
            return redirect(url_for("pageAdmin"))

        # 🔹 Login de cliente (busca no banco)
        try:
            conn = get_connection()
            cur = conn.cursor()

            # Verifica se o usuário existe (pode logar por nome OU telefone)
            query = """
                SELECT idCliente, nome, telefone 
                FROM Cliente
                WHERE (nome = %s OR telefone = %s) AND senha = %s;
            """
            cur.execute(query, (usuario, usuario, senha))
            cliente = cur.fetchone()

            cur.close()
            conn.close()

            if cliente:
                session["id_cliente"] = cliente[0]  # ✅ salva o ID do cliente
                session["user"] = cliente[1]        # nome do cliente
                session["is_admin"] = False
                logging.info(f"Cliente logado: {cliente[1]} (id {cliente[0]})")
                return redirect(url_for("home"))
            else:
                return render_template("cadastro.html", erro_login="Usuário ou senha inválidos.")


        except Exception as e:
            print("Erro ao conectar no banco:", e)
            return render_template("cadastro.html", erro_login="Erro no servidor, tente novamente.")
    
    # GET: mostra a página de login
    return render_template("cadastro.html")

# CADASTRO
@app.route("/cadastro", methods=["GET", "POST"])

def cadastro():
    if request.method == "POST":
        nome = request.form["nome"]
        cpf = request.form["cpf"]
        telefone = request.form["telefone"]
        senha = request.form["senha"]

        try:
            conn = get_connection()
            cur = conn.cursor()

            # Verifica se o telefone já existe
            cur.execute("SELECT idCliente FROM Cliente WHERE telefone = %s;", (telefone,))
            existente = cur.fetchone()

            if existente:
                cur.close()
                conn.close()
                return render_template("cadastro.html", erro_cadastro="Telefone já cadastrado.")

            # Faz o INSERT
            query = """
                INSERT INTO Cliente (nome, email, telefone, endereco, bairro, numero_residencia, complemento, cpf, senha)
                VALUES (%s, NULL, %s, NULL, NULL, NULL, NULL, NULL, %s);
            """
            cur.execute(query, (nome, telefone, senha))
            conn.commit()

            cur.close()
            conn.close()

            return redirect(url_for("login"))

        except Exception as e:
            print("Erro ao cadastrar cliente:", e)
            return render_template("cadastro.html", erro_cadastro="Erro ao cadastrar. Tente novamente mais tarde.")

    # GET → renderiza o formulário
    return render_template("cadastro.html")


# LOGOUT
@app.route("/logout")
def logout():
    session.pop("user", None)
    session.pop("is_admin", None)
    return redirect(url_for("login"))

# HOME PARA USUÁRIO COMUM
@app.route("/home")
def home():
    if "user" not in session:
        return redirect(url_for("login"))
    if session.get("is_admin"):
        return redirect(url_for("pageAdmin"))
    return render_template("homePage.html", user=session["user"])

@app.route("/salvar_pedido", methods=["POST"])
def confirmar_pedido():
    data = request.get_json()
    itens = data.get("itens", [])
    valor_total = data.get("valor_total")

    id_cliente = session.get("id_cliente")
    if not id_cliente:
        logging.warning("Tentativa de pedido sem usuário autenticado.")
        return jsonify({"erro": "Usuário não autenticado"}), 401

    conn = None
    try:
        logging.info(f"Iniciando criação de pedido para cliente {id_cliente}")
        conn = get_connection()
        cur = conn.cursor()

        # 1️⃣ Criar entrega
        cur.execute("""
            INSERT INTO Entrega (idCliente, data_entrega)
            VALUES (%s, %s)
            RETURNING idEntrega
        """, (id_cliente, date.today()))
        id_entrega = cur.fetchone()[0]
        logging.info(f"Entrega criada com id {id_entrega}")

        # 2️⃣ Criar pedido
        cur.execute("""
            INSERT INTO Pedido (data_pedido, idCliente, idEntrega, valor_total, status)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING idPedido
        """, (datetime.now(), id_cliente, id_entrega, valor_total, "Solicitado"))
        id_pedido = cur.fetchone()[0]
        logging.info(f"Pedido criado com id {id_pedido}")

        # 3️⃣ Inserir itens
        for item in itens:
            logging.info(f"Inserindo item: {item}")
            cur.execute("""
                INSERT INTO ItemPedido (idPedido, idProduto, quantidade, preco_unitario)
                SELECT %s, idProduto, %s, %s FROM Produto WHERE nome = %s
            """, (id_pedido, item["quantidade"], item["preco"], item["nome"]))
            if cur.rowcount == 0:
                raise Exception(f"Produto '{item['nome']}' não encontrado.")

        conn.commit()
        logging.info(f"Pedido {id_pedido} salvo com sucesso!")

        return jsonify({"mensagem": "Pedido salvo com sucesso!", "idPedido": id_pedido})

    except Exception as e:
        if conn:
            conn.rollback()
        logging.exception("Erro ao salvar pedido:")
        return jsonify({"erro": str(e)}), 500

    finally:
        if conn:
            cur.close()
            conn.close()

# PÁGINA ADMIN
@app.route("/pageAdmin")
def pageAdmin():
    if "user" not in session or not session.get("is_admin"):
        return redirect(url_for("login"))

    try:
        from db import get_connection
        conn = get_connection()

        query = """
            SELECT 
                p.idPedido AS id,
                c.nome AS cliente,
                p.status,
                p.data_pedido AS data,
                p.valor_total AS valor
            FROM Pedido p
            LEFT JOIN Cliente c ON p.idCliente = c.idCliente
            ORDER BY p.data_pedido DESC;
        """

        import pandas as pd
        df = pd.read_sql(query, conn)
        conn.close()

    except Exception as e:
        print("Erro ao carregar pedidos:", e)
        df = pd.DataFrame(columns=["id", "cliente", "status", "data", "valor"])

    pedidos = df.to_dict(orient="records")
    return render_template("pageAdmin.html", pedidos=pedidos)


# DASHBOARD
@app.route("/dashboard", methods=["GET", "POST"])

def dashboard():
    if 'user' not in session or not session.get("is_admin"):
        return redirect(url_for('login'))

    try:
        # 🔹 Conecta no banco
        conn = get_connection()

        # 🔹 Lê os pedidos com JOINs pra trazer dados ricos
        query = """
            SELECT 
                p.idPedido AS id,
                c.nome AS cliente,
                p.status,
                p.data_pedido AS data,
                p.valor_total AS valor,
                STRING_AGG(pr.nome, ', ') AS sabores
            FROM Pedido p
            LEFT JOIN Cliente c ON p.idCliente = c.idCliente
            LEFT JOIN ItemPedido ip ON p.idPedido = ip.idPedido
            LEFT JOIN Produto pr ON ip.idProduto = pr.idProduto
            GROUP BY p.idPedido, c.nome, p.status, p.data_pedido, p.valor_total
            ORDER BY p.data_pedido;
        """
        df = pd.read_sql(query, conn)

        conn.close()

    except Exception as e:
        print("Erro ao carregar dados do banco:", e)
        # Se der erro, cria DataFrame vazio pra não quebrar a tela
        df = pd.DataFrame(columns=['id', 'cliente', 'status', 'data', 'valor', 'sabores'])

    # 🔹 Conversões e filtros
    if 'data' in df.columns:
        df['data'] = pd.to_datetime(df['data'], errors='coerce')
        df = df.dropna(subset=['data'])
    else:
        df['data'] = pd.to_datetime([])

    if 'valor' in df.columns:
        df['valor'] = pd.to_numeric(df['valor'], errors='coerce')
        df = df.dropna(subset=['valor'])
    else:
        df['valor'] = pd.Series(dtype=float)

    # 🔹 Filtro de datas
    data_inicio = request.form.get("dataInicio")
    data_fim = request.form.get("dataFim")
    df_filtrado = df.copy()

    if data_inicio:
        df_filtrado = df_filtrado[df_filtrado['data'] >= data_inicio]
    if data_fim:
        df_filtrado = df_filtrado[df_filtrado['data'] <= data_fim]

    # 🔹 Indicadores
    total_pedidos = len(df_filtrado)
    total_finalizados = len(df_filtrado[df_filtrado['status'].str.lower() == 'entregue'])
    total_cancelados = len(df_filtrado[df_filtrado['status'].str.lower() == 'cancelado'])
    faturamento = df_filtrado['valor'].sum() if not df_filtrado.empty else 0

    # 🔹 Gráficos (mantidos)
    fig1 = plt.figure(figsize=(5,5))
    if not df_filtrado.empty and 'status' in df_filtrado.columns:
        df_filtrado['status'].value_counts().plot.pie(autopct='%1.1f%%')
    plt.title("Pedidos por Status")
    grafico_status = gerar_grafico_base64(fig1)

    fig2 = plt.figure(figsize=(6,4))
    if not df_filtrado.empty and 'sabores' in df_filtrado.columns:
        sabores = df_filtrado['sabores'].dropna().str.split(',', expand=True).stack()
        if not sabores.empty:
            sabores.value_counts().plot.bar()
    plt.title("Sabores Mais Pedidos")
    plt.ylabel("Quantidade")
    grafico_sabores = gerar_grafico_base64(fig2)

    fig3 = plt.figure(figsize=(6,4))
    if not df_filtrado.empty and df_filtrado['valor'].any():
        df_filtrado.groupby(df_filtrado['data'].dt.date)['valor'].sum().plot(kind='bar')
        plt.ylabel("R$")
        plt.xticks(rotation=45)
    plt.title("Faturamento Diário")
    grafico_faturamento = gerar_grafico_base64(fig3)

    fig4 = plt.figure(figsize=(6,4))
    if not df_filtrado.empty and 'data' in df_filtrado.columns:
        df_filtrado['dia_semana'] = df_filtrado['data'].dt.day_name()
        finalizados = df_filtrado[df_filtrado['status'].str.lower() == 'entregue']
        if not finalizados.empty:
            finalizados['dia_semana'].value_counts().sort_index().plot.bar()
            plt.ylabel("Quantidade de Entregas")
    plt.title("Dias da Semana com Mais Entregas")
    grafico_dias = gerar_grafico_base64(fig4)

    pedidos_lista = df_filtrado.to_dict(orient='records')

    return render_template(
        "dashboard.html",
        total_pedidos=total_pedidos,
        total_finalizados=total_finalizados,
        total_cancelados=total_cancelados,
        faturamento=faturamento,
        grafico_status=grafico_status,
        grafico_sabores=grafico_sabores,
        grafico_faturamento=grafico_faturamento,
        grafico_dias=grafico_dias,
        pedidos=pedidos_lista,
        data_inicio=data_inicio,
        data_fim=data_fim
    )
if __name__ == '__main__':
    app.run(debug=True)
