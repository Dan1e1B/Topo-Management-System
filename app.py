from flask import Flask, request, redirect, render_template_string
import sqlite3
 
import os
import shutil
from datetime import date
from datetime import datetime

from flask import Flask, request, redirect, render_template_string, session
from functools import wraps
import hashlib



app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "your-secret-key-here")


USER = os.environ.get("ADMIN_USER", "admin")
PASS_HASH = hashlib.sha256(os.environ.get("ADMIN_PASSWORD", "defaultpassword").encode()).hexdigest()
DB = os.environ.get("DATABASE_PATH", "trabalhos.db")
BACKUP_DIR = os.environ.get("BACKUP_DIR", "backup")

os.makedirs(os.path.dirname(DB), exist_ok=True)
os.makedirs(BACKUP_DIR, exist_ok=True)


MAX_BACKUPS = 50


def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("logged"):
            return redirect("/login")
        return f(*args, **kwargs)
    return wrapper


@app.route("/login", methods=["GET", "POST"])
def login():
    erro = ""

    if request.method == "POST":
        user = request.form.get("user", "")
        pw = request.form.get("password", "")

        pw_hash = hashlib.sha256(pw.encode()).hexdigest()

        if user == USER and pw_hash == PASS_HASH:
            session["logged"] = True
            return redirect("/")
        else:
            erro = "Login inválido"

    html = PAGE_START + """
    <div class="box" style="max-width:400px;margin:auto">
    <h3>Login</h3>
    <form method="post">
        <label>Utilizador</label><br>
        <input name="user" class="medium"><br><br>

        <label>Password</label><br>
        <input type="password" name="password" class="medium"><br><br>

        <button>Entrar</button>
    </form>
    <p style="color:red;">{{erro}}</p>
    </div>
    """ + PAGE_END

    return render_template_string(html, erro=erro)

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")



def limpar_backups():
    backups = sorted(
        [f for f in os.listdir(BACKUP_DIR) if f.startswith("trabalhos_")],
        reverse=True
    )
    for f in backups[MAX_BACKUPS:]:
        os.remove(os.path.join(BACKUP_DIR, f))


def backup_bd():
    if os.path.exists(DB):
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        destino = os.path.join(BACKUP_DIR, f"trabalhos_{ts}.db")
        shutil.copy2(DB, destino)
        limpar_backups()


# ---------------- BD ----------------
def ligar_bd():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def coluna_existe(c, nome):
    c.execute("PRAGMA table_info(trabalhos)")
    return nome in [r["name"] for r in c.fetchall()]

def criar_ou_migrar_bd():
    conn = ligar_bd()
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS trabalhos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,

        cliente_nome TEXT,
        cliente_nif INTEGER,
        cliente_morada TEXT,
        cliente_contato TEXT,
        cliente_extra TEXT,

        numero_obra TEXT,

        data_rececao TEXT,
        data_inicio TEXT,
        data_fecho TEXT,
        data_entrega TEXT,

        data_faturacao TEXT,
        numero_fatura TEXT,

        valor_orcamento REAL,
        valor_faturacao REAL,

        descricao_trabalho TEXT,
        nome_ficheiro TEXT,

        localidade TEXT,
        coordenadas TEXT,

        tarefas1 TEXT,
        tarefas2 TEXT
    )
    """)


    for col, tipo in [
        ("numero_fatura", "TEXT"),
        ("valor_orcamento", "REAL")
    ]:
        if not coluna_existe(c, col):
            c.execute(f"ALTER TABLE trabalhos ADD COLUMN {col} {tipo}")

    conn.commit()
    conn.close()

criar_ou_migrar_bd()

FIELDS = [
    "cliente_nome","cliente_nif","cliente_morada","cliente_contato","cliente_extra",
    "numero_obra",
    "data_rececao","data_inicio","data_fecho","data_entrega",
    "data_faturacao","numero_fatura",
    "valor_orcamento","valor_faturacao",
    "descricao_trabalho","nome_ficheiro",
    "localidade","coordenadas",
    "tarefas1","tarefas2"
]

HOJE = date.today().isoformat()

# ---------------- HTML BASE ----------------
PAGE_START = """
<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>Website Topo</title>
<style>
body { font-family: Arial; background:#f4f6f8; padding:20px; }
label { font-size:12px; font-weight:bold; }
input, textarea, button { padding:6px; }
input[type="date"] { width:150px; }
.small { width:120px; }
.medium { width:260px; }
.large { width:100%; }
textarea { width:100%; resize:vertical; }
.big { height:90px; }
.huge { height:140px; }
table { border-collapse:collapse; width:100%; background:white; }
th, td { border:1px solid #ccc; padding:6px; font-size:13px; }
th { background:#eee; }
.box { background:white; padding:15px; border-radius:6px; margin-bottom:20px; }
.grid { display:grid; grid-template-columns:1fr 1fr; gap:10px; }
.full { grid-column:1 / -1; }
.section { grid-column:1 / -1; font-weight:bold; margin-top:10px; }
</style>
</head>
<body>
<center><h2>Topo - Gestao de Trabalhos</h2></center>


"""

PAGE_END = """
<p style="text-align:center">
<a href="/logout">Logout</a>
</p>
</body></html>"""

# ---------------- INDEX / FILTROS ----------------

@app.route("/")
@login_required
def index():
    filtros = []
    params = []

    def add(cond, val=None):
        filtros.append(cond)
        if val is not None:
            params.append(val)
    ORDENACOES_PERMITIDAS = {
        "cliente": "cliente_nome",
        "rececao": "data_rececao",
        "inicio": "data_inicio",
        "fecho": "data_fecho",
        "entrega": "data_entrega",
        "faturacao": "data_faturacao"
    }

    ordenar = request.args.get("ordenar", "")
    sentido = request.args.get("sentido", "ASC").upper()

    campo_ordem = ORDENACOES_PERMITIDAS.get(ordenar)
    if sentido not in ["ASC", "DESC"]:
        sentido = "ASC"

    # filtros texto
    if request.args.get("cliente"):
        add("cliente_nome LIKE ?", f"%{request.args['cliente']}%")

    if request.args.get("obra"):
        add("numero_obra LIKE ?", f"%{request.args['obra']}%")

    if request.args.get("fatura"):
        add("numero_fatura LIKE ?", f"%{request.args['fatura']}%")

    if request.args.get("localidade"):
        add("localidade LIKE ?", f"%{request.args['localidade']}%")

    # filtros datas (desde data ate hoje)
    for campo in [
        "data_rececao",
        "data_inicio",
        "data_fecho",
        "data_entrega",
        "data_faturacao"
    ]:
        if request.args.get(campo):
            add(f"{campo} >= ?", request.args[campo])
            add(f"{campo} <= ?", HOJE)

    # estados
    if request.args.get("nao_iniciado"):
        add("data_rececao IS NOT NULL")
        add("data_inicio IS NULL")

    if request.args.get("em_campo"):
        add("data_inicio IS NOT NULL")
        add("data_fecho IS NULL")

    if request.args.get("fechado_nao_entregue"):
        add("data_fecho IS NOT NULL")
        add("data_entrega IS NULL")

    if request.args.get("entregue_nao_faturado"):
        add("data_entrega IS NOT NULL")
        add("data_faturacao IS NULL")

    sql = "SELECT * FROM trabalhos"
    if filtros:
        sql += " WHERE " + " AND ".join(filtros)
    if campo_ordem:
        sql += f" ORDER BY {campo_ordem} {sentido}"
    else:
        sql += " ORDER BY id DESC"


    conn = ligar_bd()
    c = conn.cursor()
    c.execute(sql, params)
    dados = c.fetchall()
    conn.close()

    html = PAGE_START + """
    <div class="box">
    <form>

    <b>Filtros texto</b><br>
    Cliente <input name="cliente">
    Obra <input name="obra">
    Fatura <input name="fatura">
    Localidade <input name="localidade"><br><br>

    <b>Filtros por data (desde)</b><br>
    Rececao <input type="date" name="data_rececao">
    Inicio <input type="date" name="data_inicio">
    Fecho campo <input type="date" name="data_fecho">
    Entrega <input type="date" name="data_entrega">
    Faturacao <input type="date" name="data_faturacao"><br><br>

    <b>Estados</b><br>
    <label><input type="checkbox" name="nao_iniciado"> Recebido nao iniciado</label><br>
    <label><input type="checkbox" name="em_campo"> Em trabalhos de campo</label><br>
    <label><input type="checkbox" name="fechado_nao_entregue"> Fechado nao entregue</label><br>
    <label><input type="checkbox" name="entregue_nao_faturado"> Entregue nao faturado</label><br><br>
    
    
    <b>Ordenar</b><br>
    Ordenar por
    <select name="ordenar">
        <option value="">-- nenhum --</option>
        <option value="cliente">Cliente</option>
        <option value="rececao">Data Rececao</option>
        <option value="inicio">Data Inicio</option>
        <option value="fecho">Data Fecho Campo</option>
        <option value="entrega">Data Entrega</option>
        <option value="faturacao">Data Faturacao</option>
    </select>

    <select name="sentido">
        <option value="ASC">Ascendente</option>
        <option value="DESC">Descendente</option>
    </select>

    <br><br>

    <button>Filtrar</button>
    </form>
    <br>
    <a href="/novo">+ Novo Trabalho</a>
    <br>
    <a href="/relatorio_cliente">Relatorio por cliente</a>

    </div>

    <table>
    <tr>
        <th>Cliente</th>
        <th>Obra</th>
        <th>Localidade</th>
        <th>Data Rececao</th>
        <th>Data Entrega</th>
        <th>Data Faturacao</th>
        <th>Mapa</th>
        <th>Acoes</th>
    </tr>

    {% for t in dados %}
    <tr>
        <td>{{t.cliente_nome}}</td>
        <td>{{t.numero_obra}}</td>
        <td>{{t.localidade}}</td>
        <td>{{t.data_rececao}}</td>
        <td>{{t.data_entrega}}</td>
        <td>{{t.data_faturacao}}</td>
        <td>
        {% if t.coordenadas %}
        <a target="_blank" href="https://www.google.com/maps?q={{t.coordenadas}}">Mapa</a>
        {% endif %}
        </td>
        <td>
            <a href="/editar/{{t.id}}">Editar</a> |
            <a href="/apagar/{{t.id}}" onclick="return confirm('Apagar?')">Apagar</a>
        </td>
    </tr>
    {% endfor %}
    </table>
    """ + PAGE_END

    return render_template_string(html, dados=dados)

# ---------------- FORM / NOVO ----------------
FORM_HTML = """
<div class="box">
<form method="post">
<div class="grid">

<div class="section">Cliente</div>

<div class="field full">
  <label>Nome</label>
  <input class="large" name="cliente_nome">
</div>

<div class="field">
  <label>NIF</label>
  <input class="small" name="cliente_nif">
</div>

<div class="field full">
  <label>Morada</label>
  <input class="large" name="cliente_morada">
</div>

<div class="field">
  <label>Contato</label>
  <input class="medium" name="cliente_contato">
</div>

<div class="field">
  <label>Campo livre</label>
  <input class="medium" name="cliente_extra">
</div>

<div class="section">Obra</div>

<div class="field">
  <label>Localidade</label>
  <input class="medium" name="localidade">
</div>

<div class="field">
  <label>Coordenadas (lat,lng)</label>
  <input class="medium" name="coordenadas">
</div>

<div class="field">
  <label>Numero da obra</label>
  <input class="medium" name="numero_obra">
</div>

<div class="field">
  <label>Data rececao</label>
  <input type="date" name="data_rececao">
</div>

<div class="field">
  <label>Data inicio</label>
  <input type="date" name="data_inicio">
</div>

<div class="field">
  <label>Data fecho de trabalho de campo</label>
  <input type="date" name="data_fecho">
</div>

<div class="field">
  <label>Data entrega</label>
  <input type="date" name="data_entrega">
</div>

<div class="section">Faturacao</div>

<div class="field">
  <label>Data faturacao</label>
  <input type="date" name="data_faturacao">
</div>

<div class="field">
  <label>Numero da fatura</label>
  <input class="medium" name="numero_fatura">
</div>

<div class="field">
  <label>Valor orcamento</label>
  <input type="number" step="0.01" class="small" name="valor_orcamento">
</div>

<div class="field">
  <label>Valor faturacao</label>
  <input type="number" step="0.01" class="small" name="valor_faturacao">
</div>

<div class="section">Detalhes</div>

<div class="field full">
  <label>Descricao trabalho</label>
  <textarea class="big" name="descricao_trabalho"></textarea>
</div>

<div class="field full">
  <label>Nome ficheiro</label>
  <input class="large" name="nome_ficheiro">
</div>

<div class="field full">
  <label>Tarefas executadas</label>
  <textarea class="huge" name="tarefas1"></textarea>
</div>

<div class="field full">
  <label>Tarefas executadas (2)</label>
  <textarea class="huge" name="tarefas2"></textarea>
</div>

</div>
<br>
<button>Guardar</button>
</form>
<br>
<a href="/">Voltar</a>
</div>
"""


@app.route("/novo", methods=["GET","POST"])
@login_required
def novo():
    if request.method == "POST":
        backup_bd()
        valores = [request.form.get(f) or None for f in FIELDS]
        conn = ligar_bd()
        conn.execute(
            f"INSERT INTO trabalhos ({','.join(FIELDS)}) VALUES ({','.join(['?']*len(FIELDS))})",
            valores
        )
        conn.commit()
        conn.close()
        return redirect("/")
    return render_template_string(PAGE_START + FORM_HTML + PAGE_END)

@app.route("/apagar/<int:id>")
@login_required
def apagar(id):
    backup_bd()
    conn = ligar_bd()
    conn.execute("DELETE FROM trabalhos WHERE id=?", (id,))
    conn.commit()
    conn.close()
    return redirect("/")


FORM_EDITAR_HTML  = """
<div class="box">
<form method="post">
<div class="grid">

<div class="section">Cliente</div>

<div class="field full">
  <label>Nome</label>
  <input class="large" name="cliente_nome" value="{{t.cliente_nome or ''}}">
</div>

<div class="field">
  <label>NIF</label>
  <input class="small" name="cliente_nif" value="{{t.cliente_nif or ''}}">
</div>

<div class="field full">
  <label>Morada</label>
  <input class="large" name="cliente_morada" value="{{t.cliente_morada or ''}}">
</div>

<div class="field">
  <label>Contato</label>
  <input class="medium" name="cliente_contato" value="{{t.cliente_contato or ''}}">
</div>

<div class="field">
  <label>Campo livre</label>
  <input class="medium" name="cliente_extra" value="{{t.cliente_extra or ''}}">
</div>

<div class="section">Obra</div>

<div class="field">
  <label>Localidade</label>
  <input class="medium" name="localidade" value="{{t.localidade or ''}}">
</div>

<div class="field">
  <label>Coordenadas (lat,lng)</label>
  <input class="medium" name="coordenadas" value="{{t.coordenadas or ''}}">
</div>

<div class="field">
  <label>Numero da obra</label>
  <input class="medium" name="numero_obra" value="{{t.numero_obra or ''}}">
</div>

<div class="field">
  <label>Data rececao</label>
  <input type="date" name="data_rececao" value="{{t.data_rececao or ''}}">
</div>

<div class="field">
  <label>Data inicio</label>
  <input type="date" name="data_inicio" value="{{t.data_inicio or ''}}">
</div>

<div class="field">
  <label>Data fecho de trabalho de campo</label>
  <input type="date" name="data_fecho" value="{{t.data_fecho or ''}}">
</div>

<div class="field">
  <label>Data entrega</label>
  <input type="date" name="data_entrega" value="{{t.data_entrega or ''}}">
</div>

<div class="section">Faturacao</div>

<div class="field">
  <label>Data faturacao</label>
  <input type="date" name="data_faturacao" value="{{t.data_faturacao or ''}}">
</div>

<div class="field">
  <label>Numero da fatura</label>
  <input class="medium" name="numero_fatura" value="{{t.numero_fatura or ''}}">
</div>

<div class="field">
  <label>Valor orcamento</label>
  <input type="number" step="0.01" class="small" name="valor_orcamento" value="{{t.valor_orcamento or ''}}">
</div>

<div class="field">
  <label>Valor faturacao</label>
  <input type="number" step="0.01" class="small" name="valor_faturacao" value="{{t.valor_faturacao or ''}}">
</div>

<div class="section">Detalhes</div>

<div class="field full">
  <label>Descricao trabalho</label>
  <textarea class="big" name="descricao_trabalho">{{t.descricao_trabalho or ''}}</textarea>
</div>

<div class="field full">
  <label>Nome ficheiro</label>
  <input class="large" name="nome_ficheiro" value="{{t.nome_ficheiro or ''}}">
</div>

<div class="field full">
  <label>Tarefas executadas</label>
  <textarea class="huge" name="tarefas1">{{t.tarefas1 or ''}}</textarea>
</div>

<div class="field full">
  <label>Tarefas executadas (2)</label>
  <textarea class="huge" name="tarefas2">{{t.tarefas2 or ''}}</textarea>
</div>

</div>
<br>
<button>Guardar</button>
</form>
<br>
<a href="/">Voltar</a>
</div>
"""

@app.route("/editar/<int:id>", methods=["GET", "POST"])
@login_required
def editar(id):
    conn = ligar_bd()
    c = conn.cursor()

    if request.method == "POST":
        backup_bd()
        valores = [request.form.get(f) or None for f in FIELDS]
        valores.append(id)

        c.execute(
            f"""
            UPDATE trabalhos
            SET {', '.join([f + '=?' for f in FIELDS])}
            WHERE id=?
            """,
            valores
        )
        conn.commit()
        conn.close()
        return redirect("/")

    c.execute("SELECT * FROM trabalhos WHERE id=?", (id,))
    t = c.fetchone()
    conn.close()

    return render_template_string(
        PAGE_START + FORM_EDITAR_HTML  + PAGE_END,
        t=t
    )


@app.route("/relatorio_cliente", methods=["GET"])
@login_required
def relatorio_cliente():
    cliente = request.args.get("cliente", "")
    data_inicio = request.args.get("data_inicio", "")
    data_fim = request.args.get("data_fim", "")

    filtros = ["data_faturacao IS NOT NULL"]
    params = []

    if cliente:
        filtros.append("cliente_nome LIKE ?")
        params.append(f"%{cliente}%")

    if data_inicio:
        filtros.append("data_faturacao >= ?")
        params.append(data_inicio)

    if data_fim:
        filtros.append("data_faturacao <= ?")
        params.append(data_fim)

    sql = """
        SELECT
            id,
            cliente_nome,
            numero_obra,
            numero_fatura,
            data_faturacao,
            valor_faturacao
        FROM trabalhos
    """

    if filtros:
        sql += " WHERE " + " AND ".join(filtros)

    sql += " ORDER BY data_faturacao ASC"

    conn = ligar_bd()
    c = conn.cursor()
    c.execute(sql, params)
    dados = c.fetchall()

    total = 0
    for d in dados:
        if d["valor_faturacao"]:
            total += float(d["valor_faturacao"])

    conn.close()

    html = PAGE_START + """
    <div class="box">
    <h3>Relatorio por cliente e periodo de faturacao</h3>

    <form>
        <label>Cliente</label><br>
        <input name="cliente" value="{{cliente}}" class="medium"><br><br>

        <label>Data inicio faturacao</label><br>
        <input type="date" name="data_inicio" value="{{data_inicio}}"><br><br>

        <label>Data fim faturacao</label><br>
        <input type="date" name="data_fim" value="{{data_fim}}"><br><br>

        <button>Calcular</button>
    </form>
    </div>

    {% if dados %}
    <div class="box">
    <table>
        <tr>
            <th>Cliente</th>
            <th>Obra</th>
            <th>Fatura</th>
            <th>Data faturacao</th>
            <th>Valor</th>
        </tr>
        {% for d in dados %}
        <tr>
            <td>{{d.cliente_nome}}</td>
            <td>{{d.numero_obra}}</td>
            <td>{{d.numero_fatura}}</td>
            <td>{{d.data_faturacao}}</td>
            <td>Valor: {{d.valor_faturacao}}</td>
        </tr>
        {% endfor %}
        <tr>
            <th colspan="4" style="text-align:right;">Total faturado</th>
            <th>Valor: {{total}}</th>
        </tr>
    </table>
    </div>
    {% endif %}

    <a href="/">Voltar</a>
    """ + PAGE_END

    return render_template_string(
        html,
        dados=dados,
        total=round(total, 2),
        cliente=cliente,
        data_inicio=data_inicio,
        data_fim=data_fim
    )



if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
