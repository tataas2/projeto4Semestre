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
import bcrypt
import secrets

sns.set(style="whitegrid")

# ---------------------------------------------
# CONFIGURAÇÃO DO FLASK
# ---------------------------------------------
app = Flask(
    __name__,
    template_folder=os.path.join(os.path.dirname(__file__), "templates"),
    static_folder=os.path.join(os.path.dirname(__file__), "static")
)

# Chave segura para sessões
app.secret_key = secrets.token_hex(32)

# Usuário admin padrão, para equipe de desenvolvimento
ADMIN_USER = {"nome": "admin", "senha": "admin123"}

# ---------------------------------------------
# Função para gerar gráficos em base64
# ---------------------------------------------
def gerar_grafico_base64(figura):
    img = BytesIO()
    figura.savefig(img, format='png', bbox_inches='tight')
    img.seek(0)
    grafico_base64 = base64.b64encode(img.getvalue()).decode()
    plt.close(figura)
    return grafico_base64


# ---------------------------------------------
# LOGIN
# ---------------------------------------------
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        usuario = request.form.get("usuario") or request.form.get("telefone")
        senha = request.form.get("senha")

        # Login ADMIN
        if usuario == ADMIN_USER["nome"] and senha == ADMIN_USER["senha"]:
            session["user"] = ADMIN_USER["nome"]
            session["is_admin"] = True
            return redirect(url_for("pageAdmin"))

        # Login CLIENTE com hash
        try:
            conn = get_connection()
            cur = conn.cursor()

            query = """
                SELECT idCliente, nome, telefone, senha
                FROM Cliente
                WHERE nome = %s OR telefone = %s;
            """
            cur.execute(query, (usuario, usuario))
            cliente = cur.fetchone()

            cur.close()
            conn.close()

            if cliente:
                senha_hash = cliente[3]

                if bcrypt.checkpw(senha.encode('utf-8'), senha_hash.encode('utf-8')):
                    # Login OK
                    session["id_cliente"] = cliente[0]
                    session["user"] = cliente[1]
                    session["is_admin"] = False
                    return redirect(url_for("home"))
                else:
                    return render_template("cadastro.html", erro_login="Senha incorreta.")

            return render_template("cadastro.html", erro_login="Usuário não encontrado.")

        except Exception as e:
            print("Erro ao conectar no banco:", e)
            return render_template("cadastro.html", erro_login="Erro no servidor.")

    return render_template("cadastro.html")


# ---------------------------------------------
# CADASTRO
# ---------------------------------------------
@app.route("/cadastro", methods=["GET", "POST"])
def cadastro():
    if request.method == "POST":
        nome = request.form["nome"]
        cpf = request.form.get("cpf")
        telefone = request.form["telefone"]
        senha = request.form["senha"]

        # Criptografa a senha
        senha_hash = bcrypt.hashpw(senha.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        try:
            conn = get_connection()
            cur = conn.cursor()

            # Verifica telefone duplicado
            cur.execute("SELECT idCliente FROM Cliente WHERE telefone = %s;", (telefone,))
            if cur.fetchone():
                cur.close()
                conn.close()
                return render_template("cadastro.html", erro_cadastro="Telefone já cadastrado.")

            query = """
                INSERT INTO Cliente (nome, email, telefone, endereco, bairro, numero_residencia, complemento, cpf, senha)
                VALUES (%s, NULL, %s, NULL, NULL, NULL, NULL, NULL, %s);
            """
            cur.execute(query, (nome, telefone, senha_hash))
            conn.commit()

            cur.close()
            conn.close()

            return redirect(url_for("login"))

        except Exception as e:
            print("Erro ao cadastrar cliente:", e)
            return render_template("cadastro.html", erro_cadastro="Erro ao cadastrar.")

    return render_template("cadastro.html")


# ---------------------------------------------
# LOGOUT
# ---------------------------------------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ---------------------------------------------
# HOME DO CLIENTE
# ---------------------------------------------
@app.route("/home")
def home():
    if "user" not in session:
        return redirect(url_for("login"))
    if session.get("is_admin"):
        return redirect(url_for("pageAdmin"))
    return render_template("homePage.html", user=session["user"])


# ---------------------------------------------
# SALVAR PEDIDO
# ---------------------------------------------
@app.route("/salvar_pedido", methods=["POST"])
def confirmar_pedido():
    data = request.get_json()
    itens = data.get("itens", [])
    valor_total = data.get("valor_total")

    id_cliente = session.get("id_cliente")
    if not id_cliente:
        return jsonify({"erro": "Usuário não autenticado"}), 401

    try:
        conn = get_connection()
        cur = conn.cursor()

        # Criar entrega
        cur.execute("""
            INSERT INTO Entrega (idCliente, data_entrega)
            VALUES (%s, %s)
            RETURNING idEntrega
        """, (id_cliente, date.today()))
        id_entrega = cur.fetchone()[0]

        # Criar pedido
        cur.execute("""
            INSERT INTO Pedido (data_pedido, idCliente, idEntrega, valor_total, status)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING idPedido
        """, (datetime.now(), id_cliente, id_entrega, valor_total, "Solicitado"))
        id_pedido = cur.fetchone()[0]

        # Itens
        for item in itens:
            cur.execute("""
                INSERT INTO ItemPedido (idPedido, idProduto, quantidade, preco_unitario)
                SELECT %s, idProduto, %s, %s FROM Produto WHERE nome = %s
            """, (id_pedido, item["quantidade"], item["preco"], item["nome"]))

        conn.commit()
        return jsonify({"mensagem": "Pedido salvo!", "idPedido": id_pedido})

    except Exception as e:
        conn.rollback()
        return jsonify({"erro": str(e)}), 500

    finally:
        cur.close()
        conn.close()


# ---------------------------------------------
# PÁGINA ADMIN
# ---------------------------------------------
@app.route("/pageAdmin")
def pageAdmin():
    if "user" not in session or not session.get("is_admin"):
        return redirect(url_for("login"))

    try:
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
        df = pd.read_sql(query, conn)
        conn.close()

    except Exception:
        df = pd.DataFrame(columns=["id", "cliente", "status", "data", "valor"])

    pedidos = df.to_dict(orient="records")
    return render_template("pageAdmin.html", pedidos=pedidos)


# ---------------------------------------------
# ATUALIZAR STATUS DE PEDIDO
# ---------------------------------------------
@app.route("/atualizar_status", methods=["POST"])
def atualizar_status():
    data = request.get_json()
    id_pedido = data.get("id_pedido")
    novo_status = data.get("novo_status")

    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("UPDATE Pedido SET status = %s WHERE idPedido = %s", (novo_status, id_pedido))
        conn.commit()

        cur.close()
        conn.close()
        return jsonify({"mensagem": "Status atualizado!"})

    except Exception as e:
        return jsonify({"erro": str(e)}), 500


# ---------------------------------------------
# DASHBOARD (mesmo da sua versão)
# ---------------------------------------------
@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    if 'user' not in session or not session.get("is_admin"):
        return redirect(url_for('login'))

    try:
        conn = get_connection()
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
    except Exception:
        df = pd.DataFrame(columns=['id', 'cliente', 'status', 'data', 'valor', 'sabores'])

    df['data'] = pd.to_datetime(df['data'], errors='coerce')
    df = df.dropna(subset=['data'])
    df['valor'] = pd.to_numeric(df['valor'], errors='coerce')

    data_inicio = request.form.get("dataInicio")
    data_fim = request.form.get("dataFim")

    df_filtrado = df.copy()
    if data_inicio:
        df_filtrado = df_filtrado[df_filtrado['data'] >= data_inicio]
    if data_fim:
        df_filtrado = df_filtrado[df_filtrado['data'] <= data_fim]

    total_pedidos = len(df_filtrado)
    total_finalizados = len(df_filtrado[df_filtrado['status'].str.lower() == 'entregue'])
    total_cancelados = len(df_filtrado[df_filtrado['status'].str.lower() == 'cancelado'])
    faturamento = df_filtrado['valor'].sum()

    fig1 = plt.figure(figsize=(5,5))
    if not df_filtrado.empty:
        df_filtrado['status'].value_counts().plot.pie(autopct='%1.1f%%')
    plt.title("Pedidos por Status")
    grafico_status = gerar_grafico_base64(fig1)

    fig2 = plt.figure(figsize=(6,4))
    if not df_filtrado.empty:
        sabores = df_filtrado['sabores'].dropna().str.split(',', expand=True).stack()
        sabores.value_counts().plot.bar()
    plt.title("Sabores Mais Pedidos")
    grafico_sabores = gerar_grafico_base64(fig2)

    fig3 = plt.figure(figsize=(6,4))
    if not df_filtrado.empty:
        df_filtrado.groupby(df_filtrado['data'].dt.date)['valor'].sum().plot(kind='bar')
        plt.xticks(rotation=45)
    plt.title("Faturamento Diário")
    grafico_faturamento = gerar_grafico_base64(fig3)

    fig4 = plt.figure(figsize=(6,4))
    if not df_filtrado.empty:
        df_filtrado['dia_semana'] = df_filtrado['data'].dt.day_name()
        finalizados = df_filtrado[df_filtrado['status'].str.lower() == 'entregue']
        finalizados['dia_semana'].value_counts().plot.bar()
    plt.title("Dias com Mais Entregas")
    grafico_dias = gerar_grafico_base64(fig4)

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
        pedidos=df_filtrado.to_dict(orient='records'),
        data_inicio=data_inicio,
        data_fim=data_fim
    )

# ---------------------------------------------
# RUN
# ---------------------------------------------
if __name__ == '__main__':
    app.run(debug=True)
