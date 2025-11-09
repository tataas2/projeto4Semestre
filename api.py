from flask import Flask, render_template, request, redirect, url_for, session
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
from io import BytesIO
import base64
import os

sns.set(style="whitegrid")

app = Flask(
    __name__,
    template_folder=os.path.join(os.path.dirname(__file__), "templates"),
    static_folder=os.path.join(os.path.dirname(__file__), "static")
)

app.secret_key = 'chave_secreta_super_segura'

# -------------------------
# Banco temporário de usuários
# -------------------------
users = []

# Usuário admin
ADMIN_USER = {"nome": "admin", "senha": "admin123"}

# CSV de pedidos
CSV_PATH = 'pedidos.csv'

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

        # Admin
        if usuario == ADMIN_USER["nome"] and senha == ADMIN_USER["senha"]:
            session["user"] = ADMIN_USER["nome"]
            session["is_admin"] = True
            return redirect(url_for("pageAdmin"))

        # Usuário comum
        for user in users:
            if user["telefone"] == usuario and user["senha"] == senha:
                session["user"] = user["nome"]
                session["is_admin"] = False
                return redirect(url_for("home"))


        return render_template("cadastro.html", erro_login="Usuário ou senha inválidos.")
    return render_template("cadastro.html")

# CADASTRO
@app.route("/cadastro", methods=["GET", "POST"])
def cadastro():
    if request.method == "POST":
        nome = request.form["nome"]
        cpf = request.form["cpf"]
        telefone = request.form["telefone"]
        senha = request.form["senha"]

        if any(u["telefone"] == telefone for u in users):
            return render_template("cadastro.html", erro_cadastro="Telefone já cadastrado.")

        users.append({
            "nome": nome,
            "cpf": cpf,
            "telefone": telefone,
            "senha": senha
        })

        return redirect(url_for("login"))

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

# PÁGINA ADMIN
@app.route("/pageAdmin")
def pageAdmin():
    if "user" not in session or not session.get("is_admin"):
        return redirect(url_for("login"))
    return render_template("pageAdmin.html", user=session["user"])

# DASHBOARD
@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    if 'user' not in session or not session.get("is_admin"):
        return redirect(url_for('login'))

    try:
        df = pd.read_csv(CSV_PATH)
    except (FileNotFoundError, pd.errors.EmptyDataError):
        df = pd.DataFrame(columns=['id','nome','status','data','valor','sabores'])

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

    # Filtra por datas
    data_inicio = request.form.get("dataInicio")
    data_fim = request.form.get("dataFim")
    df_filtrado = df.copy()
    if data_inicio:
        df_filtrado = df_filtrado[df_filtrado['data'] >= data_inicio]
    if data_fim:
        df_filtrado = df_filtrado[df_filtrado['data'] <= data_fim]

    total_pedidos = len(df_filtrado)
    total_finalizados = len(df_filtrado[df_filtrado['status'] == 'finalizado'])
    total_cancelados = len(df_filtrado[df_filtrado['status'] == 'cancelado'])
    faturamento = df_filtrado['valor'].sum() if not df_filtrado.empty else 0

    # Gráficos
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
        finalizados = df_filtrado[df_filtrado['status'] == 'finalizado']
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
