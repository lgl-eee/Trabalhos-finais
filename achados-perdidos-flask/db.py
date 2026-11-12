"""Acesso ao banco SQLite: conexão, criação das tabelas e dados de exemplo."""
import os
import sqlite3
from datetime import date, timedelta

from flask import g
from werkzeug.security import generate_password_hash

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATABASE = os.environ.get("DATABASE_PATH", os.path.join(BASE_DIR, "banco.db"))


def conectar():
    conexao = sqlite3.connect(DATABASE)
    conexao.row_factory = sqlite3.Row
    conexao.execute("PRAGMA foreign_keys = ON")  # ativa as chaves estrangeiras
    return conexao


def get_db():
    """Uma conexão por requisição, guardada em flask.g."""
    if "db" not in g:
        g.db = conectar()
    return g.db


def close_db(_erro=None):
    conexao = g.pop("db", None)
    if conexao is not None:
        conexao.close()


def init_db():
    """Cria as tabelas (se não existirem) e popula com dados de exemplo."""
    conexao = conectar()
    with open(os.path.join(BASE_DIR, "schema.sql"), encoding="utf-8") as arquivo:
        conexao.executescript(arquivo.read())
    if conexao.execute("SELECT COUNT(*) FROM usuarios").fetchone()[0] == 0:
        _popular(conexao)
    conexao.commit()
    conexao.close()


def _popular(conexao):
    """Dados de exemplo. Senha de todos os usuários: senac123"""
    senha = generate_password_hash("senac123")
    usuarios = [
        ("ana", "Ana Beatriz Lima", "ana@senac.br", "Aluna do Técnico em Informática."),
        ("bruno", "Bruno Carvalho", "bruno@senac.br", "Aluno de Administração."),
        ("recepcao", "Recepção Senac Centro", "recepcao@senac.br", "Setor oficial de achados e perdidos."),
    ]
    for username, nome, email, bio in usuarios:
        conexao.execute(
            "INSERT INTO usuarios (username, nome, email, senha_hash, bio) VALUES (?, ?, ?, ?, ?)",
            (username, nome, email, senha, bio),
        )

    def dia(atras):
        return (date.today() - timedelta(days=atras)).isoformat()

    itens = [
        ("SNC-7KQ2M9XA4P", "garrafa-azul", "Garrafa térmica azul", "Garrafa de aço inox azul com adesivo do curso de TI e o nome 'Ana' escrito na tampa.",
         "Garrafas e copos", "perdido", "aberto", "Laboratório 3", "Senac Centro", "Técnico em Informática", "ana@senac.br", dia(2), 1),
        ("SNC-H4R8TN3WC6", None, "Carteirinha de estudante", "Carteirinha do Senac com foto, encontrada no corredor do segundo andar.",
         "Documentos", "achado", "aberto", "Corredor 2º andar", "Senac Centro", "", "Recepção do Senac Centro", dia(1), 3),
        ("SNC-B9XD5LF2YM", "fone-preto", "Fone de ouvido preto sem fio", "Fone bluetooth preto em estojo cinza, sem marca aparente.",
         "Eletrônicos", "achado", "aberto", "Cantina", "Senac Zona Norte", "", "bruno@senac.br", dia(4), 2),
        ("SNC-Q3WP7VK8ZA", None, "Chave com chaveiro de gato", "Chaveiro de gato laranja com duas chaves pequenas.",
         "Chaves", "perdido", "aberto", "Sala 204", "Senac Zona Sul", "Administração - manhã", "bruno@senac.br", dia(5), 2),
        ("SNC-M2C6JH9RTE", None, "Apostila de Banco de Dados", "Apostila com capa azul e anotações a lápis nas primeiras páginas.",
         "Livros e apostilas", "perdido", "aberto", "Sala 101", "Senac Centro", "Técnico em Informática", "ana@senac.br", dia(7), 1),
        ("SNC-Y8N4GD5SUB", None, "Casaco cinza com capuz", "Casaco de moletom cinza, tamanho M, esquecido na biblioteca.",
         "Vestuário", "achado", "devolvido", "Biblioteca", "Senac Zona Leste", "", "Recepção", dia(12), 3),
        ("SNC-F5T3XK7LQW", None, "Mochila preta com chaveiro", "Mochila preta com chaveiro vermelho; dentro há cadernos e um estojo.",
         "Mochilas e bolsas", "achado", "aberto", "Auditório", "Senac Zona Oeste", "", "Recepção", dia(3), 3),
        ("SNC-D6V9PA2HNR", None, "Calculadora científica", "Calculadora científica preta com o nome gravado no verso.",
         "Material escolar", "perdido", "arquivado", "Sala 305", "Senac Centro", "Técnico em Contabilidade", "ana@senac.br", dia(30), 1),
    ]
    for (codigo, apelido, titulo, desc, cat, tipo, status, local, unidade, curso, contato, data, dono) in itens:
        conexao.execute(
            """INSERT INTO itens (codigo, apelido, titulo, descricao, categoria, tipo, status,
                                  local, unidade, curso, contato, data_ocorrido, usuario_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (codigo, apelido, titulo, desc, cat, tipo, status, local, unidade, curso, contato, data, dono),
        )

    reivindicacoes = [
        (2, 1, "É minha! O cartão está no nome de Ana Beatriz e tem um adesivo de estrela no verso.", "pendente"),
        (3, 1, "Meu fone é preto, estojo cinza com um arranhão na tampa; perdi na cantina na terça.", "pendente"),
        (6, 2, "O casaco tem uma mancha de tinta na manga esquerda e o tamanho é M.", "confirmada"),
    ]
    for item_id, usuario_id, mensagem, status in reivindicacoes:
        conexao.execute(
            "INSERT INTO reivindicacoes (item_id, usuario_id, mensagem, status) VALUES (?, ?, ?, ?)",
            (item_id, usuario_id, mensagem, status),
        )
