# Googleカレンダーや空き時間検索関連のルート

# controllers/calendar_controller.py
from flask import Blueprint, session, render_template, request, flash, redirect, url_for
from services.calendar_service import fetch_free_times
from datetime import datetime
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

calendar_bp = Blueprint('calendar', __name__)

@calendar_bp.route('/free_times', methods=['GET', 'POST'])
def free_times():
    if request.method == 'POST':

        # フォームから入力されたデータを取得
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        include_holidays = request.form.get('include_holidays') == 'on'
        day_start_hour = int(request.form.get('day_start_hour'))
        day_end_hour = int(request.form.get('day_end_hour'))

        # 入力内容をセッションに保存
        session['start_date'] = start_date
        session['end_date'] = end_date
        session['include_holidays'] = include_holidays
        session['day_start_hour'] = day_start_hour
        session['day_end_hour'] = day_end_hour

        # グーグルアカウントでログインされていなかったら除外する。
        if 'credentials' not in session:
            return redirect('login_google')

        # Google Calendarから空き時間を取得して処理
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        credentials = Credentials(**session['credentials'])
        service = build('calendar', 'v3', credentials=credentials)
        free_times_dict = fetch_free_times(service, start_date, end_date, day_start_hour, day_end_hour, not include_holidays, [])

        return render_template('free_times.html', start_date=start_date, end_date=end_date, include_holidays=include_holidays, day_start_hour=day_start_hour, day_end_hour=day_end_hour, free_times=free_times_dict)

    # 通常のログイン確認
    if 'logged_in' not in session or not session['logged_in']:
        flash('まずログインをしてください。', 'error')
        return redirect(url_for('auth.login'))

    # GETリクエストの場合、セッションのデータを引き出し初期値としてフォームに設定
    start_date = session.get('start_date', '')
    end_date = session.get('end_date', '')
    include_holidays = session.get('include_holidays', False)
    day_start_hour = session.get('day_start_hour', 8)
    day_end_hour = session.get('day_end_hour', 19)

    return render_template('free_times.html', start_date=start_date, end_date=end_date, include_holidays=include_holidays, day_start_hour=day_start_hour, day_end_hour=day_end_hour)
