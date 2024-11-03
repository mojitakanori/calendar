# 認証とセッション関連のロジック
# services/auth_service.py
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from flask import url_for, session, request

CLIENT_SECRETS_FILE = 'client_secret.json'
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']

def create_auth_flow():
    """認証フローを作成"""
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        redirect_uri=url_for('auth.oauth2callback', _external=True)
    )
    return flow

def get_authorization_url(flow):
    """認証用のURLを取得し、ステートをセッションに保存"""
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true'
    )
    session['state'] = state
    return authorization_url

def fetch_token_from_callback(state):
    """コールバックからトークンを取得し、セッションに保存"""
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        state=state,
        redirect_uri=url_for('auth.oauth2callback', _external=True)
    )
    flow.fetch_token(authorization_response=request.url)
    credentials = flow.credentials
    session['credentials'] = credentials_to_dict(credentials)

def credentials_to_dict(credentials):
    """資格情報を辞書形式に変換"""
    return {
        'token': credentials.token,
        'refresh_token': credentials.refresh_token,
        'token_uri': credentials.token_uri,
        'client_id': credentials.client_id,
        'client_secret': credentials.client_secret,
        'scopes': credentials.scopes
    }
