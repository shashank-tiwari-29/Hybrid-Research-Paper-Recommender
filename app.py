from flask import Flask, render_template, request, redirect, session
from flask_caching import Cache
from hybrid_ranker import hybrid_ranking

import requests
import xml.etree.ElementTree as ET
import sqlite3
from urllib.parse import quote

# =========================
# Initialize App
# =========================
app = Flask(__name__)
app.secret_key = "supersecretkey"
cache = Cache(app, config={'CACHE_TYPE': 'simple'})


# =========================
# Database Initialization
# =========================
def init_db():
    with sqlite3.connect('users.db') as conn:
        c = conn.cursor()

        c.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE,
                password TEXT
            )
        ''')

        c.execute('''
            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT,
                query TEXT
            )
        ''')

        conn.commit()

init_db()


# =========================
# Fetch Papers from arXiv
# =========================
@cache.memoize(timeout=3600)
def fetch_arxiv_papers(query):

    safe_query = quote(query)
    url = f"http://export.arxiv.org/api/query?search_query=all:{safe_query}&start=0&max_results=20"

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        root = ET.fromstring(response.content)
    except Exception as e:
        print("arXiv error:", e)
        return []

    papers = []

    for entry in root.findall("{http://www.w3.org/2005/Atom}entry"):

        title = entry.find("{http://www.w3.org/2005/Atom}title").text
        summary = entry.find("{http://www.w3.org/2005/Atom}summary").text
        published = entry.find("{http://www.w3.org/2005/Atom}published").text
        year = int(published[:4])

        pdf_link = ""
        for link in entry.findall("{http://www.w3.org/2005/Atom}link"):
            if link.attrib.get("type") == "application/pdf":
                pdf_link = link.attrib["href"]

        primary_category = entry.find("{http://arxiv.org/schemas/atom}primary_category")
        subject = primary_category.attrib.get("term") if primary_category is not None else ""

        papers.append({
            "title": title,
            "summary": summary,
            "pdf": pdf_link,
            "year": year,
            "citations": 0,
            "subject": subject,
            "source": "arxiv"
        })

    return papers


# =========================
# Fetch Papers from Semantic Scholar
# =========================
def fetch_semantic_scholar_papers(query):

    url = "https://api.semanticscholar.org/graph/v1/paper/search"

    params = {
        "query": query,
        "limit": 10,
        "fields": "title,abstract,year,citationCount,url"
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
    except:
        return []

    papers = []

    if "data" in data:
        for item in data["data"]:
            papers.append({
                "title": item.get("title"),
                "summary": item.get("abstract"),
                "year": item.get("year", 0),
                "citations": item.get("citationCount", 0),
                "pdf": item.get("url"),
                "subject": "",
                "source": "semantic"
            })

    return papers


# =========================
# Routes
# =========================
@app.route('/')
def home():
    return render_template("index.html")


@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        with sqlite3.connect('users.db') as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM users WHERE username=? AND password=?",
                      (username, password))
            user = c.fetchone()

        if user:
            session['username'] = username
            return redirect('/')
        else:
            error = "Invalid username or password"

    return render_template('login.html', error=error)


@app.route('/register', methods=['GET', 'POST'])
def register():
    error = None

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        with sqlite3.connect('users.db') as conn:
            c = conn.cursor()

            c.execute("SELECT * FROM users WHERE username=?", (username,))
            if c.fetchone():
                error = "Username already exists"
                return render_template('register.html', error=error)

            c.execute("INSERT INTO users (username, password) VALUES (?, ?)",
                      (username, password))
            conn.commit()

        return redirect('/login')

    return render_template('register.html')


@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect('/')


@app.route('/history')
def history():
    username = session.get('username')

    if not username:
        return redirect('/login')

    with sqlite3.connect('users.db') as conn:
        c = conn.cursor()
        c.execute("SELECT query FROM history WHERE username=?", (username,))
        searches = c.fetchall()

    return render_template('history.html', searches=searches)


@app.route('/results', methods=['POST'])
def results():

    query = request.form['domain']
    subject_filter = request.form['subject']

    sim_weight = float(request.form['sim_weight'])
    cite_weight = float(request.form['cite_weight'])
    rec_weight = float(request.form['rec_weight'])

    username = session.get('username', 'guest')

    # Save history
    with sqlite3.connect('users.db') as conn:
        c = conn.cursor()
        c.execute("INSERT INTO history (username, query) VALUES (?, ?)",
                  (username, query))
        conn.commit()

    # Fetch papers
    arxiv_papers = fetch_arxiv_papers(query)
    semantic_papers = fetch_semantic_scholar_papers(query)

    papers = arxiv_papers + semantic_papers

    # Subject filtering
    if subject_filter != "all":
        papers = [p for p in papers if subject_filter in p.get("subject", "")]

    if not papers:
        return render_template("results.html",
                               query=query,
                               papers=[])

    # Hybrid ranking
    papers = hybrid_ranking(query, papers,
                            sim_weight, cite_weight, rec_weight)

    return render_template("results.html",
                           query=query,
                           papers=papers)


# =========================
# Run App
# =========================
if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)