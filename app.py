from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date
from functools import wraps

app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev-secret-key-12345'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///pitstop.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# ── Models ────────────────────────────────────────────────────────────────────

class User(db.Model):
    id            = db.Column(db.Integer, primary_key=True)
    username      = db.Column(db.String(80), unique=True, nullable=False)
    email         = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)
    tasks    = db.relationship('Task',    backref='owner', lazy=True, cascade='all, delete-orphan')
    journals = db.relationship('Journal', backref='owner', lazy=True, cascade='all, delete-orphan')
    finances = db.relationship('Finance', backref='owner', lazy=True, cascade='all, delete-orphan')
    def set_password(self, pw):   self.password_hash = generate_password_hash(pw)
    def check_password(self, pw): return check_password_hash(self.password_hash, pw)

class Task(db.Model):
    id           = db.Column(db.Integer, primary_key=True)
    title        = db.Column(db.String(200), nullable=False)
    description  = db.Column(db.Text, default='')
    deadline     = db.Column(db.Date, nullable=True)
    best_lap     = db.Column(db.Integer, default=0) # Planned time in minutes
    actual_time  = db.Column(db.Integer, default=0) # Actual time in minutes
    priority     = db.Column(db.String(10), default='medium')
    completed    = db.Column(db.Boolean, default=False)
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)
    user_id      = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    @property
    def is_overdue(self):
        return bool(self.deadline and not self.completed and self.deadline < date.today())

    @property
    def is_improved(self):
        # "Green sector" - completed faster than planned
        return bool(self.completed and self.best_lap > 0 and self.actual_time < self.best_lap)

    @property
    def time_diff(self):
        # Improve performance by showing the gap
        if not self.completed or self.best_lap == 0: return 0
        return self.best_lap - self.actual_time

class Journal(db.Model):
    id         = db.Column(db.Integer, primary_key=True)
    title      = db.Column(db.String(200), nullable=False)
    content    = db.Column(db.Text, default='')
    mood       = db.Column(db.String(20), default='neutral')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id    = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class Finance(db.Model):
    id         = db.Column(db.Integer, primary_key=True)
    title      = db.Column(db.String(200), nullable=False)
    amount     = db.Column(db.Float, nullable=False)
    type       = db.Column(db.String(10), nullable=False)
    category   = db.Column(db.String(50), default='другое')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id    = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

# ── Helpers ───────────────────────────────────────────────────────────────────

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session or User.query.get(session['user_id']) is None:
            session.pop('user_id', None) # Clear invalid session
            flash('Войдите в систему.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def get_user():
    return User.query.get(session['user_id']) if 'user_id' in session else None

# ── Auth ──────────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return redirect(url_for('dashboard') if 'user_id' in session else url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email    = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        if not all([username, email, password]):
            flash('Заполните все поля.', 'error')
        elif User.query.filter_by(username=username).first():
            flash('Имя пользователя занято.', 'error')
        elif User.query.filter_by(email=email).first():
            flash('Email уже используется.', 'error')
        else:
            u = User(username=username, email=email)
            u.set_password(password)
            db.session.add(u); db.session.commit()
            session['user_id'] = u.id
            flash(f'Добро пожаловать, {username}!', 'success')
            return redirect(url_for('dashboard'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        u = User.query.filter_by(username=username).first()
        if u and u.check_password(password):
            session['user_id'] = u.id
            flash(f'С возвращением, {username}!', 'success')
            return redirect(url_for('dashboard'))
        flash('Неверный логин или пароль.', 'error')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))

# ── Dashboard ─────────────────────────────────────────────────────────────────

@app.route('/dashboard')
@login_required
def dashboard():
    u = get_user()
    tasks    = Task.query.filter_by(user_id=u.id, completed=False).order_by(Task.created_at.desc()).limit(5).all()
    journals = Journal.query.filter_by(user_id=u.id).order_by(Journal.created_at.desc()).limit(3).all()
    finances = Finance.query.filter_by(user_id=u.id).all()
    income   = sum(f.amount for f in finances if f.type == 'income')
    expense  = sum(f.amount for f in finances if f.type == 'expense')
    stats = {
        'tasks_total':   Task.query.filter_by(user_id=u.id).count(),
        'tasks_done':    Task.query.filter_by(user_id=u.id, completed=True).count(),
        'tasks_overdue': sum(1 for t in Task.query.filter_by(user_id=u.id, completed=False).all() if t.is_overdue),
        'journal_count': Journal.query.filter_by(user_id=u.id).count(),
        'balance':       round(income - expense, 2),
        'income':        round(income, 2),
        'expense':       round(expense, 2),
        'best_laps_count': sum(1 for t in Task.query.filter_by(user_id=u.id, completed=True).all() if t.is_improved)
    }
    return render_template('dashboard.html', user=u, tasks=tasks, journals=journals, stats=stats)

# ── Tasks ─────────────────────────────────────────────────────────────────────

@app.route('/tasks')
@login_required
def tasks():
    u = get_user()
    f = request.args.get('filter', 'all')
    p = request.args.get('priority', 'all')
    q = Task.query.filter_by(user_id=u.id)
    if f == 'active': q = q.filter_by(completed=False)
    elif f == 'done': q = q.filter_by(completed=True)
    if p != 'all':    q = q.filter_by(priority=p)
    return render_template('tasks.html', user=u, tasks=q.order_by(Task.created_at.desc()).all(),
                           filter_by=f, priority=p, today=date.today())

@app.route('/tasks/add', methods=['POST'])
@login_required
def add_task():
    u = get_user()
    title = request.form.get('title', '').strip()
    if not title:
        flash('Название не может быть пустым.', 'error')
        return redirect(url_for('tasks'))
    deadline = None
    dl = request.form.get('deadline', '')
    if dl:
        try: deadline = datetime.strptime(dl, '%Y-%m-%d').date()
        except: pass
    
    # Pit-Stop: Planned Best Lap
    try: best_lap = int(request.form.get('best_lap', 0))
    except: best_lap = 0

    db.session.add(Task(
        title=title, 
        description=request.form.get('description','').strip(),
        deadline=deadline, 
        priority=request.form.get('priority','medium'), 
        best_lap=best_lap,
        user_id=u.id
    ))
    db.session.commit()
    flash('Race started! Task added.', 'success')
    return redirect(url_for('tasks'))

@app.route('/tasks/<int:tid>/toggle', methods=['POST'])
@login_required
def toggle_task(tid):
    t = Task.query.filter_by(id=tid, user_id=session['user_id']).first_or_404()
    t.completed = not t.completed
    
    # If completing, check for actual time input
    actual = request.form.get('actual_time')
    if actual and t.completed:
        try: t.actual_time = int(actual)
        except: pass
    
    db.session.commit()
    return redirect(url_for('tasks'))

@app.route('/tasks/<int:tid>/delete', methods=['POST'])
@login_required
def delete_task(tid):
    t = Task.query.filter_by(id=tid, user_id=session['user_id']).first_or_404()
    db.session.delete(t); db.session.commit()
    flash('Задача удалена.', 'info')
    return redirect(url_for('tasks'))

@app.route('/tasks/<int:tid>/edit', methods=['GET', 'POST'])
@login_required
def edit_task(tid):
    t = Task.query.filter_by(id=tid, user_id=session['user_id']).first_or_404()
    if request.method == 'POST':
        t.title       = request.form.get('title', t.title).strip()
        t.description = request.form.get('description', '').strip()
        t.priority    = request.form.get('priority', 'medium')
        
        try: t.best_lap = int(request.form.get('best_lap', t.best_lap))
        except: pass
        
        try: t.actual_time = int(request.form.get('actual_time', t.actual_time))
        except: pass

        dl = request.form.get('deadline', '')
        t.deadline = datetime.strptime(dl, '%Y-%m-%d').date() if dl else None
        db.session.commit()
        flash('Pit-stop complete! Task updated.', 'success')
        return redirect(url_for('tasks'))
    return render_template('edit_task.html', task=t, user=get_user())

# ── Journal ───────────────────────────────────────────────────────────────────

@app.route('/journal')
@login_required
def journal():
    u = get_user()
    search = request.args.get('search', '').strip()
    q = Journal.query.filter_by(user_id=u.id)
    if search:
        q = q.filter(Journal.title.ilike(f'%{search}%') | Journal.content.ilike(f'%{search}%'))
    return render_template('journal.html', user=u, entries=q.order_by(Journal.created_at.desc()).all(), search=search)

@app.route('/journal/add', methods=['GET', 'POST'])
@login_required
def add_journal():
    u = get_user()
    if request.method == 'POST':
        title   = request.form.get('title', '').strip()
        content = request.form.get('content', '').strip()
        mood    = request.form.get('mood', 'neutral')
        if not title:
            flash('Введите заголовок.', 'error')
        else:
            db.session.add(Journal(title=title, content=content, mood=mood, user_id=u.id))
            db.session.commit()
            flash('Запись добавлена!', 'success')
            return redirect(url_for('journal'))
    return render_template('journal_form.html', user=u, entry=None)

@app.route('/journal/<int:jid>/edit', methods=['GET', 'POST'])
@login_required
def edit_journal(jid):
    j = Journal.query.filter_by(id=jid, user_id=session['user_id']).first_or_404()
    if request.method == 'POST':
        j.title      = request.form.get('title', j.title).strip()
        j.content    = request.form.get('content', '').strip()
        j.mood       = request.form.get('mood', 'neutral')
        j.updated_at = datetime.utcnow()
        db.session.commit()
        flash('Запись обновлена!', 'success')
        return redirect(url_for('journal'))
    return render_template('journal_form.html', user=get_user(), entry=j)

@app.route('/journal/<int:jid>/delete', methods=['POST'])
@login_required
def delete_journal(jid):
    j = Journal.query.filter_by(id=jid, user_id=session['user_id']).first_or_404()
    db.session.delete(j); db.session.commit()
    flash('Запись удалена.', 'info')
    return redirect(url_for('journal'))

# ── Finances ──────────────────────────────────────────────────────────────────

CATEGORIES = ['еда', 'транспорт', 'жильё', 'здоровье', 'развлечения', 'одежда', 'зарплата', 'фриланс', 'другое']

@app.route('/finances')
@login_required
def finances():
    u = get_user()
    ftype    = request.args.get('type', 'all')
    q        = Finance.query.filter_by(user_id=u.id)
    if ftype in ('income', 'expense'): q = q.filter_by(type=ftype)
    all_recs = Finance.query.filter_by(user_id=u.id).all()
    income   = sum(f.amount for f in all_recs if f.type == 'income')
    expense  = sum(f.amount for f in all_recs if f.type == 'expense')
    cat_data = {}
    for f in all_recs:
        if f.type == 'expense':
            cat_data[f.category] = round(cat_data.get(f.category, 0) + f.amount, 2)
    return render_template('finances.html', user=u, records=q.order_by(Finance.created_at.desc()).all(),
                           income=round(income,2), expense=round(expense,2),
                           balance=round(income-expense,2), ftype=ftype,
                           categories=CATEGORIES, cat_data=cat_data)

@app.route('/finances/add', methods=['POST'])
@login_required
def add_finance():
    u = get_user()
    title    = request.form.get('title', '').strip()
    category = request.form.get('category', 'другое')
    ftype    = request.form.get('type', 'expense')
    try:
        amount = float(request.form.get('amount', ''))
        if amount <= 0: raise ValueError
    except:
        flash('Введите корректную сумму.', 'error')
        return redirect(url_for('finances'))
    if not title:
        flash('Введите описание.', 'error')
        return redirect(url_for('finances'))
    db.session.add(Finance(title=title, amount=amount, type=ftype, category=category, user_id=u.id))
    db.session.commit()
    flash('Транзакция добавлена!', 'success')
    return redirect(url_for('finances'))

@app.route('/finances/<int:fid>/delete', methods=['POST'])
@login_required
def delete_finance(fid):
    f = Finance.query.filter_by(id=fid, user_id=session['user_id']).first_or_404()
    db.session.delete(f); db.session.commit()
    flash('Запись удалена.', 'info')
    return redirect(url_for('finances'))

# ── Run ───────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
