# GPT APIを使った返信メール生成のロジック


# services/gpt_service.py
import openai

def generate_reply(received_email):
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



# GPTのレスポンスに空き時間を挿入する際に整形する。
def format_free_times(free_times):
    # 空き時間リストを文字列に整形し、改行を含めて結合
    free_times_list = []
    for date, times in free_times.items():
        free_times_list.append(f"{date}")
        for time in times:
            free_times_list.append(f"  {time}")  # 各時間帯を日付の下にインデントして追加

    return "\n".join(free_times_list)  # 改行で結合して返す