-- Achados & Perdidos Senac — esquema relacional (SQLite)

CREATE TABLE IF NOT EXISTS usuarios (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    username    TEXT NOT NULL UNIQUE,
    nome        TEXT NOT NULL,
    email       TEXT NOT NULL UNIQUE,
    senha_hash  TEXT NOT NULL,
    bio         TEXT NOT NULL DEFAULT '',
    criado_em   TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS itens (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo         TEXT NOT NULL UNIQUE,
    apelido        TEXT UNIQUE,
    titulo         TEXT NOT NULL,
    descricao      TEXT NOT NULL DEFAULT '',
    categoria      TEXT NOT NULL DEFAULT 'Outros',
    tipo           TEXT NOT NULL DEFAULT 'perdido'
                   CHECK (tipo IN ('perdido', 'achado')),
    status         TEXT NOT NULL DEFAULT 'aberto'
                   CHECK (status IN ('aberto', 'devolvido', 'arquivado')),
    local          TEXT NOT NULL DEFAULT '',
    unidade        TEXT NOT NULL DEFAULT '',
    curso          TEXT NOT NULL DEFAULT '',
    contato        TEXT NOT NULL DEFAULT '',
    data_ocorrido  TEXT,
    imagem         TEXT,
    usuario_id     INTEGER NOT NULL,
    criado_em      TEXT NOT NULL DEFAULT (datetime('now')),
    atualizado_em  TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS reivindicacoes (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id     INTEGER NOT NULL,
    usuario_id  INTEGER NOT NULL,
    mensagem    TEXT NOT NULL,
    status      TEXT NOT NULL DEFAULT 'pendente'
                CHECK (status IN ('pendente', 'confirmada', 'recusada', 'retirada')),
    criado_em   TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (item_id)    REFERENCES itens(id)    ON DELETE CASCADE,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_itens_usuario ON itens(usuario_id);
CREATE INDEX IF NOT EXISTS idx_itens_status  ON itens(status, tipo);
CREATE INDEX IF NOT EXISTS idx_reiv_item     ON reivindicacoes(item_id);
CREATE INDEX IF NOT EXISTS idx_reiv_usuario  ON reivindicacoes(usuario_id);
