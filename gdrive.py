import os

from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
from agent3dp import Agent3DP


def authDrive():
    gauth = GoogleAuth()
    #gauth.LocalWebserverAuth()
    gauth.CommandLineAuth()
    drive = GoogleDrive(gauth)
    return drive


# By https://qiita.com/u48/items/322dc8d81427717a86e4
def download_recursively(drive, save_folder, drive_folder_id):
    # 保存先フォルダがなければ作成
    if not os.path.exists(save_folder):
        os.makedirs(save_folder)

    max_results = 100
    query = "'{}' in parents and trashed=false".format(drive_folder_id)

    for file_list in drive.ListFile({'q': query, 'maxResults': max_results}):
        for file in file_list:
            # mimeTypeでフォルダか判別
            if file['mimeType'] == 'application/vnd.google-apps.folder':
                download_recursively(drive, os.path.join(save_folder, file['title']), file['id'])
            else:
                file.GetContentFile(os.path.join(save_folder, file['title']))


def searchDrive(
            drive,
            filename,
            drive_folder_id,
            accept_folder=True,
            recursion=True
            ):
    max_results = 100
    query = "'{}' in parents and trashed=false".format(drive_folder_id)

    for file_list in drive.ListFile({'q': query, 'maxResults': max_results}):
        for file in file_list:
            # mimeTypeでフォルダか判別
            if file['mimeType'] == 'application/vnd.google-apps.folder':
                if accept_folder and file['title'] == filename:
                    return file
                if recursion:
                    print('searching into', file['title'])
                    file1 = searchDrive(
                                drive,
                                filename,
                                file['id'],
                                accept_folder,
                                True)
                    if file1 is not None:
                        print('file was found in', file['title'])
                        return file1
                    else:
                        print('file not found in', file['title']) 
            else:
                if file['title'] == filename:
                    print('file was found')
                    return file

    print('file not found.')
    return None