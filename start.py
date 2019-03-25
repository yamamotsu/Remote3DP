# -*- coding:utf-8 -*-
import paho.mqtt.client as mqtt
import ssl
import os
import re
import argparse
from gdrive import searchDrive
from gdrive import authDrive
from agent3dp import Agent3DP
from print_scheduler import printScheduler
from datetime import datetime
import json
import yaml

parser = argparse.ArgumentParser()
parser.add_argument('device_name', help='3DPのシリアルデバイス名。"/dev/ttyACM0"など。')
parser.add_argument('--mqtt_settings_file', default='mqtt_settings.yaml', help='MQTTの設定ファイル。yaml形式')
args = parser.parse_args()

#-------------------------
# MQTTサーバに関する設定
#-------------------------
mqtt_settings_filename = 'mqtt_settings.yaml'
with open(mqtt_settings_filename, 'r') as f:
    mqtt_settings = yaml.load(f)

host = mqtt_settings['host']
username = mqtt_settings['username']
password = mqtt_settings['password']
# SSL関連の設定の読み込み
use_ssl = mqtt_settings['use_ssl']
port = mqtt_settings['port']
topic = mqtt_settings['topic']

cwd = os.path.dirname(os.path.abspath(__file__)) + '/'

printer = Agent3DP(args.device_name)
scheduler = printScheduler(printer=printer)

def downloadGcode(
            drive,
            remote_filename,
            local_filepath,
            remote_foldername='',
            recursion=True
            ):
    if remote_foldername == '':
        folderid = 'root'
    else:
        print('searching foldername...')
        folder = searchDrive(drive, remote_foldername, 'root', accept_folder=True)
        if folder is None:
            return False
        else:
            print('folder "' + remote_foldername + '"was found.',
                    'ID: ', folder['id'])
            folderid = folder['id']

    remote_file = searchDrive(
            drive, remote_filename, folderid,
            accept_folder=False, recursion=recursion
            )

    if remote_file is None:
        return False

    print('Downloading the file into', local_filepath)
    remote_file.GetContentFile(
            os.path.join(local_filepath, remote_filename),
            'text/html'
            )
    return True


def on_connect(client, userdata, flags, respons_code):
    """broker接続時のcallback関数
    """
    print('status {0}'.format(respons_code))
    client.subscribe(topic)


def on_message(client, userdata, msg):
    print(msg.topic + ' ' + str(msg.payload, 'utf-8'))
    payload = msg.payload.decode('utf-8')

    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        print('JSONDecodeError')
        return

    if 'command' not in data:
        print('invalid message.')
        return

    if data['command'] == 'print':
        if printer.is_printing:
            print('printer is busy.')
        else:
            if 'filename' not in data:
                print('filename is not indicated. ')
                return

            filename = data['filename']
            # drive_file = searchDrive(drive, filename, 'root', False)
            print('Downloading gcode file from GoogleDrive...')
            print(filename)

            is_success = downloadGcode(
                            drive,
                            remote_filename=filename,
                            local_filepath='./tmp',
                            remote_foldername='gcode'
                            )

            if not is_success:
                print('The file ', filename, 'was not found.')
                return
            else:
                print(
                    'File ', filename,
                    ' has downloaded from drive to local tempolary folder'
                    )
                local_file = os.path.join('./tmp', filename)
                printer.startPrint(local_file)

                print('Started printing ', local_file)
    elif data['command'] == 'reserve':
        if 'filename' not in data:
            print('filename is not indicated. ')
            return

        filename = data['filename']
        # drive_file = searchDrive(drive, filename, 'root', False)
        is_success = downloadGcode(
                        drive,
                        remote_filename=filename,
                        local_filepath='./tmp',
                        remote_foldername='gcode'
                        )
        if not is_success:
            print('The file ', filename, 'was not found.')
            return
        else:
            print(
                'File', filename,
                ' has downloaded from drive to local tempolary folder'
                )
            if 'schedule' not in data:
                print('printing time is not indicated.')
                return

            try:
                date = datetime.strptime(data['schedule'], '%Y/%m/%d %H:%M')
                print('date', date)
                local_file = os.path.join('./tmp', filename)
                scheduler.add(date, local_file)
                print(
                    'Added schedule for printing ', local_file,
                    '. Start printing on ', data['schedule']
                )
            except:
                print('ERROR')
                import traceback
                traceback.print_exc()
    elif data['command'] == 'abort':
        printer.abortPrint()
    else:
        print('Invalid command')


if __name__ == '__main__':
    drive = authDrive()
    scheduler.start()

    # インスタンス作成時にprotocol v3.1.1を指定
    client = mqtt.Client(protocol=mqtt.MQTTv311)

    # パスワード認証を使用する時に使用する
    client.username_pw_set(username, password=password)
    # SSLを使用する場合の設定
    if use_ssl:
        client.tls_set(tls_version=ssl.PROTOCOL_TLSv1_2)
        client.tls_insecure_set(True)

    # callback function
    client.on_connect = on_connect
    client.on_message = on_message
    # client.on_message = on_message
    print('begin connection...')
    client.connect(host, port=port, keepalive=60)

    print('started mqtt connection.')
    client.loop_forever()
