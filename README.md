# Remote3DP
3Dプリンタとシリアル接続し、外部からのコマンドを受信してGoogleDriveからgcodeファイルを取得し自動プリントするスクリプト

# Requirements
- Python 3.5~
- paho-mqtt
- pydrive (内部でGoogleDrive APIを使用しているでそちらも必要)

# Setup
## Google Drive APIのセットアップ&OAuthクライアントIDの取得
↓の記事を参考にしてください  
https://python.keicode.com/advanced/pydrive-install.php  
取得したクライアントIDファイル: `client_secrets.json`をこのフォルダ内に移動します。
## mqtt_settings.yaml
コマンドメッセージの送受信に用いるMQTTサーバに関する設定情報を保持する`mqtt_settings.yaml`をこのフォルダ内に用意します。
以下のように設定してください
```
host: my_mqtt.hostname.com
username: myuser
password: mypassword
port: 0000
use_ssl: true(またはfalse)
topic: topic_name
```

# Usage
実行するPC/RaspberryPiと3DプリンタをUSBケーブルで接続し、デバイス名を控えておきます。

以下のように実行します。`/dev/ttyxxx`の部分は接続したプリンタのデバイス名を指定してください。
```
python start.py /dev/ttyxxx
```

初回実行時は、コマンドラインにGoogleDriveの認証用のURLが表示されるので、URLをブラウザで開いて指示に従って認証します。一度認証されると、プロジェクトフォルダ内に`credentials.json`が生成され、認証情報が保存されます。

シリアルデバイス名・MQTTサーバ設定・ドライブ認証が正しく行われると、
`started mqtt connection.`  と表示され、コマンドが送信されるのを待つ状態になります。

この状態で、別のMQTTクライアントからJSON形式のpayloadを送信すると、3Dプリンタを制御できます。以下のようにpayloadを構成します。
```
{
    command: 'print'|'reserve'|'abort',
    filename: 'gcode_file_name',
    schedule: 'yyyy/MM/dd hh/mm'
}
```
## 'print'コマンド
payload['command']に'print'を指定すると、
payload['filename']で指定された名前のgcodeファイルをGoogleDriveから読み出し、
即座にプリントを開始します。既に別のプリントが実行中であればキャンセルされます。
## 'reserve'コマンド
payload['command']に'reserve'を指定すると、
payload['filename']で指定された名前のgcodeファイルをGoogleDriveから読み出し、
payload['schedule']で指定された日時にプリントを開始します。
この時に既に別のプリントが実行中であればキャンセルされます。
payload['schedule']で指定する日時の形式は'yyyy/MM/dd hh/mm'のみ対応しています。
## 'abort'コマンド
payload['command']に'abort'を指定すると、実行中のプリントを停止し、
3DプリンタのノズルヘッドのXY座標を初期位置に戻します。
