# 認証とログイン関連のルート

# controllers/auth_controller.py
from flask import Blueprint, redirect, session, url_for, flash, render_template,  request
from services.auth_service import create_auth_flow, get_authorization_url, fetch_token_from_callback

auth_bp = Blueprint('auth', __name__)


# ログインに使用するユーザー情報のダミーデータ
users = {
    "doshisha": "mojitakanori",
    "a": "a"
}

@auth_bp.route('/')
def index():
    # 通常のログイン確認
    if 'logged_in' not in session or not session['logged_in']:
        return redirect(url_for('auth.login'))
    return render_template('index.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # ユーザー名とパスワードのチェック
        if username in users and users[username] == password:
            session['logged_in'] = True
            return redirect('/')
        else:
            flash('ユーザー名またはパスワードが間違っています。', 'error')
            return render_template('login.html')
    
    return render_template('login.html')

@auth_bp.route('/login_google')
def login_google():
    # 元のURLをセッションに保存
    session['next_url'] = request.referrer
    
    # 認証フローの作成と認証URLの取得
    flow = create_auth_flow()
    authorization_url = get_authorization_url(flow)
    return redirect(authorization_url)

@auth_bp.route('/oauth2callback')
def oauth2callback():
    state = session.get('state')
    if not state:
        flash('セッションのステートが見つかりません。再度ログインしてください。', 'error')
        return redirect(url_for('auth.login_google'))

    try:
        # トークンの取得と保存
        fetch_token_from_callback(state)
        flash('Google認証が完了しました。', 'success')
    except Exception as e:
        flash(f'Google認証中にエラーが発生しました: {e}', 'error')
        return redirect('/')

    # ログイン前のページに戻る
    next_url = session.pop('next_url', '/')
    return redirect(next_url)
