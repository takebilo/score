from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy

import json
from os import environ as env
from urllib.parse import quote_plus, urlencode

from authlib.integrations.flask_client import OAuth
from dotenv import find_dotenv, load_dotenv

ENV_FILE = find_dotenv()
if ENV_FILE:
    load_dotenv(ENV_FILE)

app = Flask(__name__, static_folder="./static/")
# セッション管理の秘密鍵を設定
app.config['SECRET_KEY'] = b''
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///score.db'

db = SQLAlchemy(app)

# DBのクラス
class Score(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.String(30))
    title = db.Column(db.String(30))
    composer = db.Column(db.String(30))
    arranger = db.Column(db.String(30))

# ログイン機能(Auth0)の設定 
oauth = OAuth(app)

oauth.register(
    "auth0",
    client_id=env.get("AUTH0_CLIENT_ID"),
    client_secret=env.get("AUTH0_CLIENT_SECRET"),
    client_kwargs={
        "scope": "openid profile email",
    },
    server_metadata_url=f'https://{env.get("AUTH0_DOMAIN")}/.well-known/openid-configuration',
)

@app.route('/score', methods=['GET', 'POST'])
def index():
    if request.method == 'GET':
        scores = Score.query.all()
        return render_template('index.html', scores=scores)
    else:
        number = request.form.get('number')
        title = request.form.get('title')
        composer = request.form.get('composer')
        arranger = request.form.get('arranger')

        new_score = Score(number=number, title=title, composer=composer, arranger=arranger)

        db.session.add(new_score)
        db.session.commit()
        return redirect('/score')

# 楽譜の追加
@app.route('/add_score', methods=['GET', 'POST'])
def create():
    user = session.get('user')
    # ログインしていれば追加処理
    if user:
        if request.method == 'GET':
            return render_template('add.html')
        if request.method == 'POST':
            form_number = request.form.get("number")
            # 楽譜タイトル
            form_title = request.form.get("title")
            # 作曲者
            form_composer = request.form.get("composer")
            # 編曲者
            form_arranger = request.form.get("arranger")

            # フォームから取得した情報を変数に格納
            score = Score(
                number = form_number,
                title = form_title,
                composer = form_composer,
                arranger = form_arranger
            )

            # DBに書き込む
            db.session.add(score)
            db.session.commit()
            return render_template('add.html')
    # ログインしていなければログイン処理
    else:
        return redirect("/score_login")

# 楽譜の一覧
@app.route('/score_list')
def score_list():
    scores = Score.query.all()
    return render_template('score_list.html', scores=scores)

# 楽譜の削除
@app.route('/score_delete')
def score_list_delete():
    user = session.get('user')
    # ログインしていれば削除処理
    if user:
        scores = Score.query.all()
        return render_template('score_delete.html', scores=scores)
    # ログインしていなければログイン処理
    else:
        return redirect("/score_login")

# 楽譜検索
@app.route('/score_search', methods=['GET', 'POST'])
def score_search():
    if request.method == 'GET':
        return render_template('score_search.html')
    if request.method == 'POST':
        form_title = request.form.get("title")
        search_results = db.session.query(Score).filter(Score.title.contains(form_title))
        return render_template('result.html', search_results=search_results)

@app.route('/scores/<int:id>/delete', methods=['POST'])
def score_delete(id):
    score = Score.query.get(id)
    db.session.delete(score)
    db.session.commit()
    return redirect(url_for('score_list_delete'))

@app.route('/scores/<int:id>/edit', methods=['GET'])
def score_edit(id):
    # 編集ページ表示用
    score = Score.query.get(id)
    return render_template('score_edit.html', score=score)

# 楽譜更新
@app.route('/scores/<int:id>/update', methods=['POST'])
def score_update(id):
    score = Score.query.get(id) 
    score.number = request.form.get("number")
    score.title = request.form.get("title")
    score.composer = request.form.get("composer")
    score.arranger = request.form.get("arranger")

    db.session.merge(score)
    db.session.commit()
    return redirect(url_for('score_list'))

# ログイン後の処理
@app.route("/score_after_login", methods=["GET", "POST"])
def after_login():
    user = session.get('user')
    if user:
        return render_template("login.html")
    else:
        return redirect("/login")

@app.route("/score_callback", methods=["GET", "POST"])
def callback():
    token = oauth.auth0.authorize_access_token()
    session["user"] = token
    return redirect("/score_after_login")

# ログイン処理
@app.route("/score_login")
def login():
    return oauth.auth0.authorize_redirect(
        redirect_uri=url_for("callback", _external=True)
    )

# ログアウト処理
@app.route("/score_logout")
def logout():
    session.clear()
    return redirect(
        "https://"
        + env.get("AUTH0_DOMAIN")
        + "/v2/logout?"
        + urlencode(
            {
                "returnTo": url_for("index", _external=True),
                "client_id": env.get("AUTH0_CLIENT_ID"),
            },
            quote_via=quote_plus,
        )
    )

if __name__ == '__main__':
	app.run()