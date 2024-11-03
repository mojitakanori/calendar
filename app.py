from flask import Flask
from controllers.auth_controller import auth_bp
from controllers.calendar_controller import calendar_bp
from controllers.reply_controller import reply_bp
import os


# os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'  # ローカル環境でHTTPを許可
# 本番では消す！！！！！！！！！！！！！！！！

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Blueprintの登録
app.register_blueprint(auth_bp)
app.register_blueprint(calendar_bp)
app.register_blueprint(reply_bp)


if __name__ == '__main__':
    app.run(debug=True)