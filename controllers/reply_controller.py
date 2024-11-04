# GPTを使用した返信メール作成関連のルート

# controllers/reply_controller.py
from flask import Blueprint, request, render_template, session, redirect, url_for,flash
from services.gpt_service import generate_reply, format_free_times
from datetime import datetime
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from services.calendar_service import fetch_free_times

reply_bp = Blueprint('reply', __name__)

@reply_bp.route('/get_reply', methods=['GET', 'POST'])
def get_reply():
    if request.method == 'GET':
        # 通常のログイン確認
        if 'logged_in' not in session or not session['logged_in']:
            flash('まずログインをしてください。', 'error')
            return redirect(url_for('auth.login'))
        # セッションからデータを取得し初期値として利用
        start_date = session.get('start_date', '')
        end_date = session.get('end_date', '')
        day_start_hour = session.get('day_start_hour', 8)
        day_end_hour = session.get('day_end_hour', 19)
        include_holidays = session.get('include_holidays', False)
        # ファイルからデフォルトのメール内容を読み込む
        with open('static/default_email.txt', 'r', encoding='utf-8') as f:
            default_email_content = f.read()
        received_email = session.get('received_email', default_email_content)

        return render_template('reply.html', start_date=start_date, end_date=end_date,
                               day_start_hour=day_start_hour, day_end_hour=day_end_hour,
                               include_holidays=include_holidays, received_email=received_email)

    if request.method == 'POST':
        # ユーザが入力したデータを取得してセッションに保存
        received_email = request.form.get('received_email')
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        day_start_hour = int(request.form.get('day_start_hour'))
        day_end_hour = int(request.form.get('day_end_hour'))
        include_holidays = request.form.get('include_holidays') == 'on'

        session['received_email'] = received_email
        session['start_date'] = start_date
        session['end_date'] = end_date
        session['day_start_hour'] = day_start_hour
        session['day_end_hour'] = day_end_hour
        session['include_holidays'] = include_holidays

        if not received_email:
            reply_email = "入力欄が空です！  送られてきたメールを入力してください！"
            flash('入力欄が空です！', 'error')        
        else:
            # GPTに問い合わせを行い、返信メールを生成
            reply_email = generate_reply(received_email)

        # GPTが生成した返信メール内に[empty_day]があるか確認し、空き時間に置き換える
        if '[empty_day]' in reply_email:
            if 'credentials' not in session:
                return redirect('login_google')
            start_date = request.form.get('start_date')
            end_date = request.form.get('end_date')
            include_holidays = request.form.get('include_holidays') == 'on'
            day_start_hour = int(request.form.get('day_start_hour'))
            day_end_hour = int(request.form.get('day_end_hour'))

            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()

            credentials = Credentials(**session['credentials'])
            service = build('calendar', 'v3', credentials=credentials)

            free_times_dict = fetch_free_times(
                service, start_date, end_date, day_start_hour, day_end_hour, not include_holidays, []
            )

            # 空き時間を整形して[empty_day]を置き換える
            reply_email = reply_email.replace('[empty_day]', format_free_times(free_times_dict))

        # 結果の返信メールを表示
        return render_template('reply.html', reply_email=reply_email, received_email=received_email,
                               start_date=start_date, end_date=end_date, day_start_hour=day_start_hour,
                               day_end_hour=day_end_hour, include_holidays=include_holidays)
