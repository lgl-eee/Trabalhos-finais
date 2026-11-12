"""Achados & Perdidos Senac — aplicação Flask (SQLite + Jinja2)."""
import os
import re
import secrets
import sqlite3
import unicodedata
from datetime import datetime
from functools import wraps

from flask import (Flask, abort, flash, g, jsonify, redirect, render_template,
                   request, session, url_for)
from werkzeug.security import check_password_hash, generate_password_hash

import db

app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.environ.get("SECRET_KEY", "dev-troque-esta-chave-em-producao"),
)
app.teardown_appcontext(db.close_db)

# --------------------------------------------------------------------------
# Domínio
# --------------------------------------------------------------------------
TIPOS = {
    "perdido": {"nome": "Perdi este item", "rotulo": "Perdido", "classe": "tipo-perdido"},
    "achado": {"nome": "Encontrei este item", "rotulo": "Encontrado", "classe": "tipo-achado"},
}
STATUS_ITEM = {
    "aberto": {"rotulo": "Em aberto", "classe": "status-aberto"},
    "devolvido": {"rotulo": "Devolvido", "classe": "status-devolvido"},
    "arquivado": {"rotulo": "Arquivado", "classe": "status-arquivado"},
}
STATUS_REIVINDICACAO = {
    "pendente": "aguardando",
    "confirmada": "confirmada",
    "recusada": "recusada",
    "retirada": "retirada",
}
CATEGORIAS = [
    "Material escolar", "Eletrônicos", "Vestuário", "Documentos", "Chaves",
    "Acessórios", "Mochilas e bolsas", "Garrafas e copos", "Livros e apostilas", "Outros",
]
UNIDADES = [
    "Senac Centro", "Senac Zona Norte", "Senac Zona Sul",
    "Senac Zona Leste", "Senac Zona Oeste", "Outra unidade",
]

ITEM_SELECT = """
    SELECT i.*, u.username AS autor_username, u.nome AS autor_nome
    FROM itens i
    JOIN usuarios u ON u.id = i.usuario_id
"""


# --------------------------------------------------------------------------
# Utilitários
# --------------------------------------------------------------------------
def gerar_codigo():
    alfabeto = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    while True:
        codigo = "SNC-" + "".join(secrets.choice(alfabeto) for _ in range(10))
        if not db.get_db().execute("SELECT 1 FROM itens WHERE codigo = ?", (codigo,)).fetchone():
            return codigo


def slugify(texto, limite=28):
    texto = unicodedata.normalize("NFD", (texto or "").lower())
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    texto = re.sub(r"[^a-z0-9]+", "-", texto).strip("-")
    return texto[:limite].strip("-")


def destino_seguro(destino):
    """Só aceita caminhos internos no parâmetro ?next=."""
    if destino and destino.startswith("/") and not destino.startswith("//"):
        return destino
    return url_for("index")


def voltar_para(padrao):
    """Redireciona para o campo 'voltar' do formulário (se for interno) ou para o padrão."""
    return redirect(destino_seguro(request.form.get("voltar", "")) if request.form.get("voltar") else padrao)


def login_required(funcao):
    @wraps(funcao)
    def envolver(*args, **kwargs):
        if g.usuario is None:
            flash("Entre com sua conta Senac para continuar.", "warning")
            return redirect(url_for("entrar", next=request.full_path.rstrip("?")))
        return funcao(*args, **kwargs)
    return envolver


def buscar_item_ou_404(item_id):
    item = db.get_db().execute(ITEM_SELECT + " WHERE i.id = ?", (item_id,)).fetchone()
    if item is None:
        abort(404)
    return item


def exigir_dono(item):
    if g.usuario is None or g.usuario["id"] != item["usuario_id"]:
        abort(403)


def ler_formulario_item(form, item_id=None):
    """Valida o formulário de item. Devolve (dados, erros)."""
    dados = {
        "tipo": form.get("tipo", "perdido"),
        "titulo": form.get("titulo", "").strip(),
        "descricao": form.get("descricao", "").strip(),
        "categoria": form.get("categoria", ""),
        "unidade": form.get("unidade", ""),
        "local": form.get("local", "").strip(),
        "curso": form.get("curso", "").strip(),
        "contato": form.get("contato", "").strip(),
        "data_ocorrido": form.get("data_ocorrido", "").strip() or None,
        "apelido": slugify(form.get("apelido", "")) or None,
    }
    erros = {}
    if dados["tipo"] not in TIPOS:
        erros["tipo"] = "Escolha se você perdeu ou encontrou o item."
    if len(dados["titulo"]) < 3:
        erros["titulo"] = "Descreva o objeto com pelo menos 3 caracteres."
    if len(dados["titulo"]) > 90:
        erros["titulo"] = "O título pode ter no máximo 90 caracteres."
    if len(dados["descricao"]) > 800:
        erros["descricao"] = "A descrição pode ter no máximo 800 caracteres."
    if dados["categoria"] not in CATEGORIAS:
        erros["categoria"] = "Escolha uma categoria da lista."
    if dados["unidade"] not in UNIDADES:
        erros["unidade"] = "Escolha a unidade Senac."
    if dados["data_ocorrido"]:
        try:
            ocorrido = datetime.strptime(dados["data_ocorrido"], "%Y-%m-%d").date()
            if ocorrido > datetime.now().date():
                erros["data_ocorrido"] = "A data não pode estar no futuro."
        except ValueError:
            erros["data_ocorrido"] = "Informe uma data válida."
    if dados["apelido"]:
        repetido = db.get_db().execute(
            "SELECT 1 FROM itens WHERE (apelido = ? OR codigo = ?) AND id IS NOT ?",
            (dados["apelido"], dados["apelido"].upper(), item_id),
        ).fetchone()
        if repetido:
            erros["apelido"] = "Este apelido já está em uso. Tente outro."
    return dados, erros


# --------------------------------------------------------------------------
# Sessão, CSRF e contexto dos templates
# --------------------------------------------------------------------------
@app.before_request
def carregar_usuario_e_csrf():
    usuario_id = session.get("usuario_id")
    g.usuario = None
    if usuario_id:
        g.usuario = db.get_db().execute(
            "SELECT id, username, nome, email FROM usuarios WHERE id = ?", (usuario_id,)
        ).fetchone()
        if g.usuario is None:
            session.pop("usuario_id", None)
    if request.method == "POST":
        token = session.get("_csrf")
        if not token or not secrets.compare_digest(token, request.form.get("_csrf", "")):
            abort(400)


def csrf_token():
    if "_csrf" not in session:
        session["_csrf"] = secrets.token_hex(16)
    return session["_csrf"]


@app.context_processor
def contexto_global():
    return {
        "csrf_token": csrf_token,
        "usuario": g.get("usuario"),
        "TIPOS": TIPOS,
        "STATUS_ITEM": STATUS_ITEM,
        "STATUS_REIVINDICACAO": STATUS_REIVINDICACAO,
        "CATEGORIAS": CATEGORIAS,
        "UNIDADES": UNIDADES,
        "ano_atual": datetime.now().year,
    }


@app.template_filter("data_br")
def data_br(valor):
    if not valor:
        return "—"
    for formato in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(valor, formato).strftime("%d/%m/%Y")
        except ValueError:
            continue
    return valor


# --------------------------------------------------------------------------
# Páginas públicas
# --------------------------------------------------------------------------
@app.route("/")
def index():
    conexao = db.get_db()
    contadores = conexao.execute(
        """SELECT
               SUM(tipo = 'achado' AND status = 'aberto')  AS achados,
               SUM(tipo = 'perdido' AND status = 'aberto') AS perdidos,
               SUM(status = 'devolvido')                   AS devolvidos
           FROM itens"""
    ).fetchone()
    recentes = conexao.execute(
        ITEM_SELECT + " WHERE i.status = 'aberto' ORDER BY i.criado_em DESC, i.id DESC LIMIT 8"
    ).fetchall()
    passos = [
        ("bi-pencil-square", "Registre o item", "Escreva a descrição, o local (sala, laboratório, cantina) e a data do ocorrido."),
        ("bi-search", "Procure no mural", "Filtre por unidade, tipo de objeto e categoria para achar rapidamente o que sumiu."),
        ("bi-hand-thumbs-up", "Reivindique", "Envie uma mensagem com detalhes que só o dono saberia. Quem registrou confirma."),
        ("bi-shield-check", "Devolução registrada", "Após a entrega, o item é marcado como devolvido e sai do mural, com histórico preservado."),
    ]
    return render_template("index.html", contadores=contadores, recentes=recentes, passos=passos)


@app.route("/explorar")
def explorar():
    filtros = {
        "q": request.args.get("q", "").strip(),
        "tipo": request.args.get("tipo", ""),
        "categoria": request.args.get("categoria", ""),
        "unidade": request.args.get("unidade", ""),
        "status": request.args.get("status", "aberto"),
        "ordem": request.args.get("ordem", "recentes"),
    }
    itens = consultar_itens(filtros)
    return render_template("explorar.html", itens=itens, filtros=filtros)


def consultar_itens(filtros, limite=60):
    """Consulta com JOIN entre itens e usuarios, usada pela página e pela API."""
    condicoes, parametros = [], []
    if filtros.get("q"):
        condicoes.append("(i.titulo LIKE ? OR i.descricao LIKE ?)")
        parametros += [f"%{filtros['q']}%"] * 2
    if filtros.get("tipo") in TIPOS:
        condicoes.append("i.tipo = ?")
        parametros.append(filtros["tipo"])
    if filtros.get("categoria"):
        condicoes.append("i.categoria = ?")
        parametros.append(filtros["categoria"])
    if filtros.get("unidade"):
        condicoes.append("i.unidade = ?")
        parametros.append(filtros["unidade"])
    status = filtros.get("status") or "aberto"
    condicoes.append("i.status = ?")
    parametros.append(status if status in STATUS_ITEM else "aberto")
    ordem = "ASC" if filtros.get("ordem") == "antigos" else "DESC"
    sql = f"{ITEM_SELECT} WHERE {' AND '.join(condicoes)} ORDER BY i.criado_em {ordem}, i.id {ordem} LIMIT ?"
    return db.get_db().execute(sql, parametros + [limite]).fetchall()


@app.route("/item/<codigo>")
def item(codigo):
    conexao = db.get_db()
    registro = conexao.execute(
        ITEM_SELECT + " WHERE i.codigo = ? OR i.apelido = ?", (codigo.upper(), codigo.lower())
    ).fetchone()
    if registro is None:
        abort(404)
    dono = g.usuario is not None and g.usuario["id"] == registro["usuario_id"]
    reivindicacoes = []
    if g.usuario is not None:
        # O dono vê todas as reivindicações; quem reivindicou vê apenas as suas.
        sql = """SELECT r.*, u.username AS autor_username, u.nome AS autor_nome
                 FROM reivindicacoes r
                 JOIN usuarios u ON u.id = r.usuario_id
                 WHERE r.item_id = ?"""
        parametros = [registro["id"]]
        if not dono:
            sql += " AND r.usuario_id = ?"
            parametros.append(g.usuario["id"])
        reivindicacoes = conexao.execute(sql + " ORDER BY r.criado_em DESC, r.id DESC", parametros).fetchall()
    return render_template("item.html", item=registro, dono=dono, reivindicacoes=reivindicacoes)


@app.route("/perfil/<username>")
def perfil(username):
    conexao = db.get_db()
    pessoa = conexao.execute(
        "SELECT id, username, nome, bio, criado_em FROM usuarios WHERE username = ?", (username.lower(),)
    ).fetchone()
    if pessoa is None:
        abort(404)
    itens = conexao.execute(
        ITEM_SELECT + " WHERE i.usuario_id = ? ORDER BY i.criado_em DESC, i.id DESC", (pessoa["id"],)
    ).fetchall()
    devolvidos = sum(1 for registro in itens if registro["status"] == "devolvido")
    return render_template("perfil.html", pessoa=pessoa, itens=itens, devolvidos=devolvidos)


@app.route("/acessibilidade")
def acessibilidade():
    recursos = [
        ("Alto contraste", "Botão na barra superior que troca as cores por um tema escuro de alto contraste."),
        ("Tamanho da fonte", "Botões A−, A e A+ aumentam ou diminuem todo o texto do site."),
        ("Link para o conteúdo", "Pressione Tab ao abrir a página para pular direto ao conteúdo principal."),
        ("Navegação por teclado", "Todos os botões e links têm foco visível e funcionam sem mouse."),
        ("Leitores de tela", "Rótulos em todos os campos e avisos anunciados automaticamente."),
        ("Preferências lembradas", "O contraste e o tamanho da fonte escolhidos ficam salvos neste navegador."),
    ]
    return render_template("acessibilidade.html", recursos=recursos)


# --------------------------------------------------------------------------
# API JSON
# --------------------------------------------------------------------------
def item_para_dict(registro):
    return {
        "codigo": registro["codigo"],
        "apelido": registro["apelido"],
        "titulo": registro["titulo"],
        "descricao": registro["descricao"],
        "categoria": registro["categoria"],
        "tipo": registro["tipo"],
        "status": registro["status"],
        "local": registro["local"],
        "unidade": registro["unidade"],
        "data_ocorrido": registro["data_ocorrido"],
        "registrado_por": registro["autor_username"],
        "url": url_for("item", codigo=registro["apelido"] or registro["codigo"], _external=True),
    }


@app.route("/api/itens")
def api_itens():
    """Lista itens em JSON. Aceita ?q=, ?tipo=, ?categoria=, ?unidade=, ?status=."""
    filtros = {chave: request.args.get(chave, "") for chave in ("q", "tipo", "categoria", "unidade", "status")}
    itens = consultar_itens(filtros, limite=100)
    return jsonify({"total": len(itens), "itens": [item_para_dict(registro) for registro in itens]})


@app.route("/api/estatisticas")
def api_estatisticas():
    """Resumo por unidade e tipo, usando JOIN e GROUP BY."""
    linhas = db.get_db().execute(
        """SELECT i.unidade, i.tipo, COUNT(*) AS total, COUNT(r.id) AS reivindicacoes
           FROM itens i
           LEFT JOIN reivindicacoes r ON r.item_id = i.id
           GROUP BY i.unidade, i.tipo
           ORDER BY i.unidade, i.tipo"""
    ).fetchall()
    return jsonify([dict(linha) for linha in linhas])


# --------------------------------------------------------------------------
# Autenticação
# --------------------------------------------------------------------------
@app.route("/cadastrar", methods=["GET", "POST"])
def cadastrar():
    if g.usuario:
        return redirect(url_for("painel"))
    dados, erros = {"nome": "", "username": "", "email": ""}, {}
    if request.method == "POST":
        dados = {
            "nome": request.form.get("nome", "").strip(),
            "username": slugify(request.form.get("username", ""), 20).replace("-", "_"),
            "email": request.form.get("email", "").strip().lower(),
        }
        senha = request.form.get("senha", "")
        if len(dados["nome"]) < 3:
            erros["nome"] = "Informe seu nome completo."
        if len(dados["username"]) < 3:
            erros["username"] = "Use pelo menos 3 letras ou números."
        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", dados["email"]):
            erros["email"] = "Informe um e-mail válido."
        if len(senha) < 6:
            erros["senha"] = "A senha precisa ter pelo menos 6 caracteres."
        if not erros:
            try:
                conexao = db.get_db()
                cursor = conexao.execute(
                    "INSERT INTO usuarios (username, nome, email, senha_hash) VALUES (?, ?, ?, ?)",
                    (dados["username"], dados["nome"], dados["email"], generate_password_hash(senha)),
                )
                conexao.commit()
                session["usuario_id"] = cursor.lastrowid
                flash("Conta criada! Você já pode publicar no mural.", "success")
                return redirect(url_for("painel"))
            except sqlite3.IntegrityError:
                erros["email"] = "Já existe uma conta com este e-mail ou nome de usuário."
    return render_template("cadastrar.html", dados=dados, erros=erros)


@app.route("/entrar", methods=["GET", "POST"])
def entrar():
    if g.usuario:
        return redirect(url_for("painel"))
    destino = request.args.get("next", "")
    erro, login = None, ""
    if request.method == "POST":
        login = request.form.get("login", "").strip().lower()
        senha = request.form.get("senha", "")
        pessoa = db.get_db().execute(
            "SELECT * FROM usuarios WHERE email = ? OR username = ?", (login, login)
        ).fetchone()
        if pessoa and check_password_hash(pessoa["senha_hash"], senha):
            session["usuario_id"] = pessoa["id"]
            flash(f"Olá, {pessoa['nome'].split()[0]}!", "success")
            proximo = request.form.get("next") or destino
            return redirect(destino_seguro(proximo) if proximo else url_for("painel"))
        erro = "E-mail ou senha incorretos."
    return render_template("entrar.html", erro=erro, login=login, destino=destino)


@app.route("/sair", methods=["POST"])
def sair():
    session.pop("usuario_id", None)
    flash("Você saiu da sua conta.", "info")
    return redirect(url_for("index"))


# --------------------------------------------------------------------------
# CRUD de itens (somente usuários autenticados)
# --------------------------------------------------------------------------
@app.route("/registrar", methods=["GET", "POST"])
@login_required
def registrar():
    dados, erros = {"tipo": "perdido", "unidade": UNIDADES[0], "categoria": CATEGORIAS[0]}, {}
    if request.method == "POST":
        dados, erros = ler_formulario_item(request.form)
        if not erros:
            conexao = db.get_db()
            codigo = gerar_codigo()
            conexao.execute(
                """INSERT INTO itens (codigo, apelido, titulo, descricao, categoria, tipo, local,
                                      unidade, curso, contato, data_ocorrido, usuario_id)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (codigo, dados["apelido"], dados["titulo"], dados["descricao"], dados["categoria"],
                 dados["tipo"], dados["local"], dados["unidade"], dados["curso"], dados["contato"],
                 dados["data_ocorrido"], g.usuario["id"]),
            )
            conexao.commit()
            flash(f"Registro publicado no mural! Código de acesso: {dados['apelido'] or codigo}", "success")
            return redirect(url_for("item", codigo=dados["apelido"] or codigo))
    return render_template("form_item.html", item=None, dados=dados, erros=erros)


@app.route("/item/<int:item_id>/editar", methods=["GET", "POST"])
@login_required
def editar(item_id):
    registro = buscar_item_ou_404(item_id)
    exigir_dono(registro)
    dados, erros = dict(registro), {}
    if request.method == "POST":
        dados, erros = ler_formulario_item(request.form, item_id=item_id)
        if not erros:
            conexao = db.get_db()
            conexao.execute(
                """UPDATE itens SET apelido = ?, titulo = ?, descricao = ?, categoria = ?, tipo = ?,
                          local = ?, unidade = ?, curso = ?, contato = ?, data_ocorrido = ?,
                          atualizado_em = datetime('now')
                   WHERE id = ?""",
                (dados["apelido"], dados["titulo"], dados["descricao"], dados["categoria"], dados["tipo"],
                 dados["local"], dados["unidade"], dados["curso"], dados["contato"], dados["data_ocorrido"],
                 item_id),
            )
            conexao.commit()
            flash("Registro atualizado.", "success")
            return redirect(url_for("item", codigo=dados["apelido"] or registro["codigo"]))
    return render_template("form_item.html", item=registro, dados=dados, erros=erros)


@app.route("/item/<int:item_id>/status", methods=["POST"])
@login_required
def mudar_status(item_id):
    registro = buscar_item_ou_404(item_id)
    exigir_dono(registro)
    novo = request.form.get("status", "")
    if novo not in STATUS_ITEM:
        abort(400)
    conexao = db.get_db()
    conexao.execute("UPDATE itens SET status = ?, atualizado_em = datetime('now') WHERE id = ?", (novo, item_id))
    conexao.commit()
    flash(f"Situação atualizada: {STATUS_ITEM[novo]['rotulo'].lower()}.", "success")
    return voltar_para(url_for("painel"))


@app.route("/item/<int:item_id>/excluir", methods=["POST"])
@login_required
def excluir(item_id):
    registro = buscar_item_ou_404(item_id)
    exigir_dono(registro)
    conexao = db.get_db()
    conexao.execute("DELETE FROM itens WHERE id = ?", (item_id,))  # reivindicações caem em cascata
    conexao.commit()
    flash("Registro removido.", "info")
    return redirect(url_for("painel"))


# --------------------------------------------------------------------------
# Painel e reivindicações
# --------------------------------------------------------------------------
@app.route("/meus-registros")
@login_required
def painel():
    conexao = db.get_db()
    meus_itens = conexao.execute(
        ITEM_SELECT + " WHERE i.usuario_id = ? ORDER BY i.criado_em DESC, i.id DESC", (g.usuario["id"],)
    ).fetchall()
    recebidas = conexao.execute(
        """SELECT r.*, i.titulo AS item_titulo, i.codigo AS item_codigo, i.apelido AS item_apelido,
                  u.username AS autor_username, u.nome AS autor_nome
           FROM reivindicacoes r
           JOIN itens i    ON i.id = r.item_id
           JOIN usuarios u ON u.id = r.usuario_id
           WHERE i.usuario_id = ?
           ORDER BY r.criado_em DESC, r.id DESC""",
        (g.usuario["id"],),
    ).fetchall()
    enviadas = conexao.execute(
        """SELECT r.*, i.titulo AS item_titulo, i.codigo AS item_codigo, i.apelido AS item_apelido
           FROM reivindicacoes r
           JOIN itens i ON i.id = r.item_id
           WHERE r.usuario_id = ?
           ORDER BY r.criado_em DESC, r.id DESC""",
        (g.usuario["id"],),
    ).fetchall()
    return render_template("painel.html", itens=meus_itens, recebidas=recebidas, enviadas=enviadas)


@app.route("/item/<int:item_id>/reivindicar", methods=["POST"])
@login_required
def reivindicar(item_id):
    registro = buscar_item_ou_404(item_id)
    voltar = url_for("item", codigo=registro["apelido"] or registro["codigo"])
    mensagem = request.form.get("mensagem", "").strip()
    if registro["usuario_id"] == g.usuario["id"]:
        flash("Você não pode reivindicar um item que você mesmo registrou.", "danger")
    elif registro["status"] != "aberto":
        flash("Este item não está mais em aberto.", "danger")
    elif len(mensagem) < 10:
        flash("Descreva melhor: conte detalhes que comprovem que o objeto é seu (mínimo 10 caracteres).", "danger")
    else:
        conexao = db.get_db()
        pendente = conexao.execute(
            "SELECT 1 FROM reivindicacoes WHERE item_id = ? AND usuario_id = ? AND status = 'pendente'",
            (item_id, g.usuario["id"]),
        ).fetchone()
        if pendente:
            flash("Você já tem uma reivindicação aguardando resposta para este item.", "warning")
        else:
            conexao.execute(
                "INSERT INTO reivindicacoes (item_id, usuario_id, mensagem) VALUES (?, ?, ?)",
                (item_id, g.usuario["id"], mensagem[:600]),
            )
            conexao.commit()
            flash("Reivindicação enviada! Quem registrou o item vai avaliar sua descrição.", "success")
    return redirect(voltar)


@app.route("/reivindicacao/<int:reivindicacao_id>/responder", methods=["POST"])
@login_required
def responder(reivindicacao_id):
    conexao = db.get_db()
    reivindicacao = conexao.execute(
        """SELECT r.*, i.usuario_id AS dono_id FROM reivindicacoes r
           JOIN itens i ON i.id = r.item_id WHERE r.id = ?""",
        (reivindicacao_id,),
    ).fetchone()
    if reivindicacao is None:
        abort(404)
    if reivindicacao["dono_id"] != g.usuario["id"]:
        abort(403)
    acao = request.form.get("acao")
    novos = {"confirmar": "confirmada", "recusar": "recusada"}
    if acao not in novos or reivindicacao["status"] != "pendente":
        flash("Esta reivindicação já foi finalizada.", "warning")
    else:
        conexao.execute("UPDATE reivindicacoes SET status = ? WHERE id = ?", (novos[acao], reivindicacao_id))
        conexao.commit()
        flash("Reivindicação atualizada.", "success")
    return voltar_para(url_for("painel"))


@app.route("/reivindicacao/<int:reivindicacao_id>/retirar", methods=["POST"])
@login_required
def retirar(reivindicacao_id):
    conexao = db.get_db()
    reivindicacao = conexao.execute(
        "SELECT * FROM reivindicacoes WHERE id = ?", (reivindicacao_id,)
    ).fetchone()
    if reivindicacao is None:
        abort(404)
    if reivindicacao["usuario_id"] != g.usuario["id"]:
        abort(403)
    if reivindicacao["status"] == "pendente":
        conexao.execute("UPDATE reivindicacoes SET status = 'retirada' WHERE id = ?", (reivindicacao_id,))
        conexao.commit()
        flash("Reivindicação retirada.", "info")
    return redirect(url_for("painel"))


# --------------------------------------------------------------------------
# Erros
# --------------------------------------------------------------------------
@app.errorhandler(400)
def erro_400(_erro):
    return render_template("erro.html", codigo=400, titulo="Requisição inválida",
                           mensagem="A página expirou ou o formulário estava incompleto. Volte e tente de novo."), 400


@app.errorhandler(403)
def erro_403(_erro):
    return render_template("erro.html", codigo=403, titulo="Acesso negado",
                           mensagem="Somente quem registrou o item pode fazer isso."), 403


@app.errorhandler(404)
def erro_404(_erro):
    return render_template("erro.html", codigo=404, titulo="Página não encontrada",
                           mensagem="Nenhum registro responde por este endereço."), 404


# Cria o banco (com dados de exemplo) na primeira execução, inclusive sob o gunicorn.
db.init_db()

if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1")