from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
from collections import defaultdict
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "your_secret_key"
DB_FILE = "data.db"

def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                currency TEXT DEFAULT 'USD'
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                category TEXT NOT NULL,
                amount REAL NOT NULL,
                description TEXT,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        """)
        conn.commit()

def get_user_id():
    return session.get('user_id')

@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = get_user_id()
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        expenses = cursor.execute("SELECT * FROM expenses WHERE user_id = ? ORDER BY date DESC", (user_id,)).fetchall()
        user_currency = cursor.execute("SELECT currency FROM users WHERE id = ?", (user_id,)).fetchone()[0]

    total = sum([row[4] for row in expenses])
    category_data = defaultdict(float)
    for row in expenses:
        category_data[row[3]] += row[4]

    categories = list(category_data.keys())
    category_totals = list(category_data.values())

    return render_template('index.html', expenses=expenses, total=round(total, 2),
                           categories=categories, category_totals=category_totals,
                           currency=user_currency)

@app.route('/add', methods=['POST'])
def add():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    date = request.form['date']
    category = request.form['category']
    amount = request.form['amount']
    description = request.form['description']
    user_id = get_user_id()

    with sqlite3.connect(DB_FILE) as conn:
        conn.execute("INSERT INTO expenses (user_id, date, category, amount, description) VALUES (?, ?, ?, ?, ?)",
                     (user_id, date, category, float(amount), description))
        conn.commit()
    return redirect(url_for('index'))

@app.route('/delete/<int:expense_id>')
def delete(expense_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    with sqlite3.connect(DB_FILE) as conn:
        conn.execute("DELETE FROM expenses WHERE id = ? AND user_id = ?", (expense_id, get_user_id()))
        conn.commit()
    return redirect(url_for('index'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = generate_password_hash(request.form['password'])
        currency = request.form['currency']

        with sqlite3.connect(DB_FILE) as conn:
            try:
                conn.execute("INSERT INTO users (username, password, currency) VALUES (?, ?, ?)",
                             (username, password, currency))
                conn.commit()
            except sqlite3.IntegrityError:
                return "Username already taken"
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        with sqlite3.connect(DB_FILE) as conn:
            user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
            if user and check_password_hash(user[2], password):
                session['user_id'] = user[0]
                return redirect(url_for('index'))
        return "Invalid username or password"
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    init_db()
    app.run(debug=True)