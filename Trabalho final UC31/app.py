import os
import json
from datetime import date, timedelta
from statistics import mean
from functools import wraps

from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import check_password_hash, generate_password_hash

DATA_DIR = 'dados'
CURSOS_FILE = os.path.join(DATA_DIR, 'cursos.json')
AVAL_FILE = os.path.join(DATA_DIR, 'avaliacoes.json')

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'trocar-por-uma-chave-secreta')
app.permanent_session_lifetime = timedelta(hours=2)

ADMIN_USER = os.environ.get('ADMIN_USER', 'admin')
ENV_ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD')
ENV_ADMIN_PASSWORD_HASH = os.environ.get('ADMIN_PASSWORD_HASH')
if ENV_ADMIN_PASSWORD_HASH:
    ADMIN_PASSWORD_HASH = ENV_ADMIN_PASSWORD_HASH
else:
    ADMIN_PASSWORD_HASH = generate_password_hash(ENV_ADMIN_PASSWORD or 'admin123')

def ensure_data_dir():
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR, exist_ok=True)

def load_json(path):
    ensure_data_dir()
    if not os.path.exists(path):
        return []
    with open(path, 'r', encoding='utf-8') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []

def save_json_atomic(path, data):
    ensure_data_dir()
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)

def next_id(items):
    if not items:
        return 1
    return max(item.get('id', 0) for item in items) + 1

def annotate_cursos(cursos, avaliacoes):
    for c in cursos:
        notas = [a['estrela'] for a in avaliacoes if a.get('curso_id') == c.get('id')]
        c['num_avaliacoes'] = len(notas)
        c['media'] = round(mean(notas), 1) if notas else 0
    return cursos

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('is_admin'):
            return redirect(url_for('login', next=request.path))
        return f(*args, **kwargs)
    return decorated

@app.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('is_admin'):
        return redirect(url_for('admin'))
    if request.method == 'POST':
        username = request.form.get('username', '')
        password = request.form.get('password', '')
        if username == ADMIN_USER and check_password_hash(ADMIN_PASSWORD_HASH, password):
            session.permanent = True
            session['is_admin'] = True
            flash('Login efetuado com sucesso.', 'success')
            next_url = request.args.get('next') or url_for('admin')
            return redirect(next_url)
        else:
            flash('Credenciais inválidas.', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('is_admin', None)
    flash('Logout efetuado.', 'success')
    return redirect(url_for('index'))

@app.route('/')
def index():
    cursos = load_json(CURSOS_FILE)
    avaliacoes = load_json(AVAL_FILE)
    annotate_cursos(cursos, avaliacoes)
    top_cursos = sorted(cursos, key=lambda x: x.get('media', 0), reverse=True)[:3]
    return render_template('index.html', top_cursos=top_cursos)

@app.route('/cursos')
def listar_cursos():
    q = request.args.get('q', '').strip().lower()
    ordenar = request.args.get('ordenar', 'media')
    cursos = load_json(CURSOS_FILE)
    avaliacoes = load_json(AVAL_FILE)
    annotate_cursos(cursos, avaliacoes)

    if q:
        cursos = [c for c in cursos if q in c.get('nome', '').lower() or q in c.get('unidade', '').lower()]

    if ordenar == 'nome':
        cursos = sorted(cursos, key=lambda x: x.get('nome', '').lower())
    else:
        cursos = sorted(cursos, key=lambda x: x.get('media', 0), reverse=True)

    return render_template('cursos.html', cursos=cursos, q=q, ordenar=ordenar)

@app.route('/cursos/<int:id>')
def detalhes_curso(id):
    cursos = load_json(CURSOS_FILE)
    avaliacoes = load_json(AVAL_FILE)
    curso = next((c for c in cursos if c.get('id') == id), None)
    if not curso:
        flash('Curso não encontrado.', 'danger')
        return redirect(url_for('listar_cursos'))

    notas = [a for a in avaliacoes if a.get('curso_id') == id]
    if not isinstance(notas, list):
        notas = []

    curso = curso.copy()
    curso['num_avaliacoes'] = len(notas)
    try:
        curso['media'] = round(mean([n.get('estrela', 0) for n in notas]), 1) if notas else 0
    except Exception:
        curso['media'] = 0

    return render_template('detalhes.html', curso=curso, avaliacoes=notas)

@app.route('/cadastrar', methods=['GET', 'POST'])
@admin_required
def cadastrar():
    if request.method == 'POST':
        cursos = load_json(CURSOS_FILE)
        novo = {
            'id': next_id(cursos),
            'nome': request.form.get('nome', '').strip(),
            'morada': request.form.get('morada', '').strip(),
            'unidade': request.form.get('unidade', '').strip(),
            'descricao': request.form.get('descricao', '').strip(),
            'vagas': int(request.form.get('vagas') or 0),
            'telefone': request.form.get('telefone', '').strip(),
            'site': request.form.get('site', '').strip()
        }
        if not novo['nome']:
            flash('O nome do curso é obrigatório.', 'danger')
            return render_template('cadastrar.html', curso=novo)
        cursos.append(novo)
        save_json_atomic(CURSOS_FILE, cursos)
        flash('Curso cadastrado com sucesso!', 'success')
        return redirect(url_for('listar_cursos'))
    return render_template('cadastrar.html')

@app.route('/editar/<int:id>', methods=['GET', 'POST'])
@admin_required
def editar(id):
    cursos = load_json(CURSOS_FILE)
    curso = next((c for c in cursos if c.get('id') == id), None)
    if not curso:
        flash('Curso não encontrado.', 'danger')
        return redirect(url_for('listar_cursos'))
    if request.method == 'POST':
        curso['nome'] = request.form.get('nome', curso.get('nome')).strip()
        curso['morada'] = request.form.get('morada', curso.get('morada')).strip()
        curso['unidade'] = request.form.get('unidade', curso.get('unidade')).strip()
        curso['descricao'] = request.form.get('descricao', curso.get('descricao')).strip()
        curso['vagas'] = int(request.form.get('vagas') or curso.get('vagas', 0))
        curso['telefone'] = request.form.get('telefone', curso.get('telefone')).strip()
        curso['site'] = request.form.get('site', curso.get('site')).strip()
        save_json_atomic(CURSOS_FILE, cursos)
        flash('Curso atualizado com sucesso!', 'success')
        return redirect(url_for('detalhes_curso', id=id))
    return render_template('editar.html', curso=curso)
@app.route('/deletar/<int:id>', methods=['POST'])
@admin_required
def deletar(id):
    cursos = load_json(CURSOS_FILE)
    avaliacoes = load_json(AVAL_FILE)
    cursos_novos = [c for c in cursos if c.get('id') != id]
    avaliacoes_novos = [a for a in avaliacoes if a.get('curso_id') != id]
    if len(cursos_novos) == len(cursos):
        flash('Curso não encontrado.', 'danger')
    else:
        save_json_atomic(CURSOS_FILE, cursos_novos)
        save_json_atomic(AVAL_FILE, avaliacoes_novos)
        flash('Curso e avaliações associadas removidos.', 'success')
    return redirect(url_for('listar_cursos'))

@app.route('/avaliar/<int:curso_id>', methods=['POST'])
def avaliar(curso_id):
    avaliacoes = load_json(AVAL_FILE)
    cursos = load_json(CURSOS_FILE)
    curso = next((c for c in cursos if c.get('id') == curso_id), None)
    if not curso:
        flash('Curso não encontrado.', 'danger')
        return redirect(url_for('listar_cursos'))
    try:
        estrela = int(request.form.get('estrela', 0))
    except ValueError:
        estrela = 0
    if estrela < 1 or estrela > 5:
        flash('A avaliação deve ter entre 1 e 5 estrelas.', 'danger')
        return redirect(url_for('detalhes_curso', id=curso_id))
    nova = {
        'id': next_id(avaliacoes),
        'curso_id': curso_id,
        'autor': request.form.get('autor', 'Anónimo').strip() or 'Anónimo',
        'estrela': estrela,
        'comentario': request.form.get('comentario', '').strip(),
        'data': date.today().isoformat()
    }
    avaliacoes.append(nova)
    save_json_atomic(AVAL_FILE, avaliacoes)
    flash('Avaliação registada. Obrigado!', 'success')
    return redirect(url_for('detalhes_curso', id=curso_id))

@app.route('/admin')
@admin_required
def admin():
    cursos = load_json(CURSOS_FILE)
    avaliacoes = load_json(AVAL_FILE)
    annotate_cursos(cursos, avaliacoes)
    total_cursos = len(cursos)
    total_avaliacoes = len(avaliacoes)
    top5 = sorted(cursos, key=lambda x: x.get('media', 0), reverse=True)[:5]
    return render_template('admin.html', total_cursos=total_cursos,
                           total_avaliacoes=total_avaliacoes, top5=top5)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)