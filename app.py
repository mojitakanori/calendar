from flask import Flask, redirect, url_for, session, request, render_template, flash
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from datetime import datetime, timedelta, time
import pytz
import os
from dateutil.parser import isoparse
import openai 

app = Flask(__name__)
app.secret_key = os.urandom(24)

# HTTPSでない場合は以下を設定（開発環境用）
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

# Google APIの設定
CLIENT_SECRETS_FILE = 'client_secret.json'
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']

# ChatGPT APIキーを設定
openai.api_key = os.getenv('OPENAI_API_KEY')

# ログインに使用するユーザー情報のダミーデータ
users = {
    "a": "a"
}

@app.route('/')
def index():
    # 通常のログイン確認
    # 今だけログイン画面無視
    # if 'logged_in' not in session or not session['logged_in']:
    #     return redirect(url_for('login'))
    return render_template('index.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # ユーザー名とパスワードのチェック
        if username in users and users[username] == password:
            session['logged_in'] = True
            return redirect('/')
        else:
            # flash('ユーザー名またはパスワードが違います。')
            return render_template('login.html')
    
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    session.pop('credentials', None)
    return redirect(url_for('login'))


@app.route('/login_google')
def login_google():
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        redirect_uri=url_for('oauth2callback', _external=True))
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true')
    session['state'] = state
    return redirect(authorization_url)


@app.route('/oauth2callback')
def oauth2callback():
    state = session['state']
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        state=state,
        redirect_uri=url_for('oauth2callback', _external=True))
    try:
        flow.fetch_token(authorization_response=request.url)
        credentials = flow.credentials
        # セッションに資格情報を保存
        session['credentials'] = credentials_to_dict(credentials)
    except Exception as e:
        flash(f'Google認証中にエラーが発生しました: {e}')
        return redirect('/')

    return redirect('/')


@app.route('/free_times', methods=['GET', 'POST'])
def free_times():
    if request.method == 'POST':
        if 'credentials' not in session:
            return redirect('login_google')

        # フォームから入力されたデータを取得
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        include_holidays = request.form.get('include_holidays') == 'on'
        day_start_hour = int(request.form.get('day_start_hour'))
        day_end_hour = int(request.form.get('day_end_hour'))

        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()

        # Google Calendarから空き時間を取得
        credentials = Credentials(**session['credentials'])
        service = build('calendar', 'v3', credentials=credentials)
        free_times_dict = fetch_free_times(service, start_date, end_date, day_start_hour, day_end_hour, not include_holidays, [])

        return render_template('free_times.html', free_times=free_times_dict)

    # GETリクエストの場合は単純にフォームを表示
    return render_template('free_times.html')


##################################
#　GPTへの問い合わせ
##################################
@app.route('/get_reply', methods=['GET', 'POST'])
def get_reply():
    if request.method == 'GET':
        # GETリクエストが来た場合、返信メール作成ページを表示
        return render_template('reply.html')

    if request.method == 'POST':
        received_email = request.form.get('received_email')
        if not received_email:
            return render_template('reply.html')  # フォームに戻す

        # GPTに問い合わせを行い、返信メールを生成
        reply_email = chatgpt_generate_reply(received_email)

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
        return render_template('reply.html', reply_email=reply_email)


def chatgpt_generate_reply(received_email):
    system_message = (
        "あなたは、ビジネスメールの作成をサポートするアシスタントです。以下のメールに対して、ユーザーが企業またはOBOGに対して丁寧でフォーマルな返信を作成してください。"
        "メールの内容は、敬意を持ち、ビジネスコミュニケーションにふさわしい言葉遣いを使用することを心掛けます。"
        "返信内容には次の要素を含めてください。"
        "1. メールの宛先として、相手の会社名や名前を最初に記載してください。"
        "2. メールの冒頭では「お世話になっております。○○所属の○○（名前）です。ご返信いただきありがとうございます。」としてください。"
        "3. 本文では、相手のメールに対して適切な感謝の意を伝えつつ、質問やリクエストに答えてください。"
        "日程調整が必要な場合は、『以下が私の都合の良い日程です。』のように改行し、その後に [empty_day] タグを単体で使用して、空き時間を提案してください。文中に埋め込まず、改行して単体で表記してください。"
        "4. メールの最後には、以下の署名を含めてください。--- [ユーザーの名前] [ユーザーの大学名・所属] [ユーザーの連絡先情報] ---"
    )

    try:
        completion = openai.ChatCompletion.create(
            model="gpt-4o", 
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": f"相手からのメール内容は以下です： 「{received_email}」"}
            ]
        )
        # ChatCompletionMessage オブジェクトの正しいプロパティを参照
        refined_text = completion['choices'][0]['message']['content']
        print(refined_text)
        return refined_text
    except Exception as e:
        print(f"Error calling ChatGPT API: {e}")
        return received_email


def format_free_times(free_times):
    # 空き時間リストを文字列に整形し、改行を含めて結合
    free_times_list = []
    for date, times in free_times.items():
        free_times_list.append(f"{date}")
        for time in times:
            free_times_list.append(f"  {time}")  # 各時間帯を日付の下にインデントして追加

    return "\n".join(free_times_list)  # 改行で結合して返す


##################################
#　空き時間検索のロジック
##################################

def fetch_free_times(service, start_date, end_date, day_start_hour, day_end_hour, exclude_holidays, exclude_keywords):
    free_times = {}
    current_date = start_date

    while current_date <= end_date:
        if exclude_holidays and is_holiday(current_date, service):
            current_date += timedelta(days=1)
            continue

        tz = pytz.timezone('Asia/Tokyo')
        day_start = tz.localize(datetime.combine(current_date, time(day_start_hour, 0, 0)))
        day_end = tz.localize(datetime.combine(current_date, time(day_end_hour, 0, 0)))

        # 当日のイベントを取得
        events_result = service.events().list(
            calendarId='primary',
            timeMin=day_start.isoformat(),
            timeMax=day_end.isoformat(),
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        events = events_result.get('items', [])

        # 無視するキーワードに一致するイベントを除外
        filtered_events = []
        for event in events:
            summary = event.get('summary', '')
            if not any(keyword in summary for keyword in exclude_keywords):
                filtered_events.append(event)

        available_start = day_start
        merged_free_times = []

        # イベントを開始時間順に並べ替え
        filtered_events.sort(key=lambda x: parse_event_time(x['start']))

        # 各イベントに基づき空き時間を計算
        for event in filtered_events:
            event_start = parse_event_time(event['start'])
            event_end = parse_event_time(event['end'])

            if available_start < event_start:
                merged_free_times.append((available_start, event_start))

            available_start = max(available_start, event_end)

        if available_start < day_end:
            merged_free_times.append((available_start, day_end))

        # 日付のフォーマット
        day_names = ["月", "火", "水", "木", "金", "土", "日"]
        date_str = current_date.strftime(f"%m月%d日（{day_names[current_date.weekday()]}）")

        # 日付ごとに空き時間を追加
        if merged_free_times:
            if date_str not in free_times:
                free_times[date_str] = []
            for start, end in merged_free_times:
                time_range = format_time_range(start, end)
                free_times[date_str].append(time_range)

        current_date += timedelta(days=1)

    return free_times


def parse_event_time(event_time):
    if 'dateTime' in event_time:
        return isoparse(event_time['dateTime'])
    else:
        return isoparse(event_time['date'])


def is_holiday(date, service):
    # 休日のカレンダーID (GoogleカレンダーAPI)
    holidays_calendar_id = 'ja.japanese#holiday@group.v.calendar.google.com'
    
    # タイムゾーンを東京に設定
    tz = pytz.timezone('Asia/Tokyo')
    
    # その日の始まりと終わりの時間を設定
    day_start = tz.localize(datetime.combine(date, time(0, 0, 0)))
    day_end = tz.localize(datetime.combine(date, time(23, 59, 59)))

    # Googleカレンダーから当日のイベント（休日）を取得
    events_result = service.events().list(
        calendarId=holidays_calendar_id,
        timeMin=day_start.isoformat(),
        timeMax=day_end.isoformat(),
        singleEvents=True,
        orderBy='startTime'
    ).execute()

    # 休日のイベントがあればTrueを返す
    holidays = events_result.get('items', [])
    return len(holidays) > 0


def format_time_range(start_time, end_time):
    formatted_start = start_time.astimezone(pytz.timezone('Asia/Tokyo')).strftime("%H:%M")
    formatted_end = end_time.astimezone(pytz.timezone('Asia/Tokyo')).strftime("%H:%M")
    return f"{formatted_start}～{formatted_end}"


def credentials_to_dict(credentials):
    return {
        'token': credentials.token,
        'refresh_token': credentials.refresh_token,
        'token_uri': credentials.token_uri,
        'client_id': credentials.client_id,
        'client_secret': credentials.client_secret,
        'scopes': credentials.scopes
    }




if __name__ == '__main__':
    app.run(debug=True)