# 認証とログイン関連のルート

# controllers/auth_controller.py
from flask import Blueprint, redirect, session, url_for, flash, render_template,  request
from services.auth_service import create_auth_flow, get_authorization_url, fetch_token_from_callback
from firebase_admin import auth, credentials, exceptions
import os
from dotenv import load_dotenv
import pyrebase

# .env ファイルの読み込み
load_dotenv()

# Firebase 設定の読み込み
firebase_config = {
    "apiKey": os.getenv("FIREBASE_API_KEY"),
    "authDomain": os.getenv("FIREBASE_AUTH_DOMAIN"),
    "databaseURL": os.getenv("FIREBASE_DATABASE_URL"),
    "projectId": os.getenv("FIREBASE_PROJECT_ID"),
    "storageBucket": os.getenv("FIREBASE_STORAGE_BUCKET"),
    "messagingSenderId": os.getenv("FIREBASE_MESSAGING_SENDER_ID"),
    "appId": os.getenv("FIREBASE_APP_ID")
}

# Pyrebase の初期化
firebase = pyrebase.initialize_app(firebase_config)
auth = firebase.auth()

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/')
def index():
    # 通常のログイン確認
    if 'logged_in' not in session or not session['logged_in']:
        flash('まずログインをしてください。', 'error')
        return redirect(url_for('auth.login'))
    return render_template('index.html')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['username']
        password = request.form['password']
        
        try:
            # メールアドレスとパスワードの検証
            user = auth.sign_in_with_email_and_password(email, password)
            
            # ログイン成功時にトークンをセッションに保存
            session['firebase_token'] = user['idToken']
            session['logged_in'] = True

            # 認証が成功したらリダイレクト
            return redirect('/')
        
        except Exception as e:
            # エラーメッセージの処理
            flash('メールアドレスまたはパスワードが間違っています。', 'error')
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
