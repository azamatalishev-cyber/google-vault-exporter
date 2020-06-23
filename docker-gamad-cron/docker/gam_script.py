import subprocess
import sys
from time import sleep
from slack_webhook import Slack

GET_LATEST_ALUMNI_OU_LIST = "/opt/gam/src/gam.py print users query " \
                            "orgUnitPath='/Alumni' > AlumniOU_new.txt"
GET_ALUMNI_OU_LIST_FROM_DRIVE = '/opt/gam/src/gam.py user ' \
                                'admin-alishev get ' \
                                'drivefile id 1HNF9-wh7Mawgab5FSL5crMqU1FfGI8PDZx7_bIPx-ZA format txt targetfolder ' \
                                '/opt/gam/src/ '
INITIATE_MAIL_EXPORT = '/opt/gam/src/gam.py create export matter Test corpus mail ' \
                       'name "{}" accounts {}'
INITIATE_DRIVE_EXPORT = '/opt/gam/src/gam.py create export matter Test corpus drive ' \
                        'name "{}" accounts {}'
GET_EXPORT_STATUS = '/opt/gam/src/gam.py info export Test "{}" | grep status:'
DOWNLOAD_EXPORT = '/opt/gam/src/gam.py download export Test {} targetfolder /tmp/'
UPLOAD_EXPORT = '/opt/gam/src/gam.py user admin-alishev add drivefile ' \
                'localfile /tmp/{} parentid 0AOOb5eIIkqg5Uk9PVA '
EXPORT_COMPLETE_MESSAGE = " status: COMPLETED"
UPDATE_DRIVE_FILE = '/opt/gam/src/gam.py user admin-alishev update drivefile id ' \
                    '1HNF9-wh7Mawgab5FSL5crMqU1FfGI8PDZx7_bIPx-ZA localfile AlumniOU_new.txt newfilename AlumniOU.txt'
CREATE_FOLDER_IN_DRIVE = '/opt/gam/src/gam.py user admin-alishev create drivefile ' \
                         'drivefilename {} mimetype gfolder parentid 0AOOb5eIIkqg5Uk9PVA '
CHECK_IF_FILE_EXISTS = "/opt/gam/src/gam.py user admin-alishev show filelist corpora " \
                       "onlyteamdrives filenamematchpattern {}"                         
DRIVE_EXPORT_NAME = '{}.drive'
MAIL_EXPORT_NAME = '{}.mail'
LIST_ALL_DOWNLOADED_FILES = 'ls /tmp/'



def execute_bash(command):
    return subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT)


def read_file(file):
    with open(file, "r", encoding='utf-8-sig') as file:
        file_list = file.readlines()
        return [item.strip() for item in file_list]


def check_for_file_in_drive(file):

    try:
        execute_bash(CHECK_IF_FILE_EXISTS.format(file))
        return 0
    except subprocess.CalledProcessError:
        return 1


def clean_up():
    sleep(5)
    execute_bash(UPDATE_DRIVE_FILE)


def initiate_exports(off_boarded_users):
    export_names = []
    for name in off_boarded_users:
        try:
            execute_bash(INITIATE_MAIL_EXPORT.format(MAIL_EXPORT_NAME.format(name).strip(), name))
            sleep(5)
            # execute_bash(INITIATE_DRIVE_EXPORT.format(DRIVE_EXPORT_NAME.format(name).strip(), name))
            notify_slack('Initiating Export for {}'.format(name))
            sleep(5)
        except subprocess.CalledProcessError:
            notify_slack('Export for {} already exists'.format(name))
            sleep(5)
            pass
        export_names.append(MAIL_EXPORT_NAME.format(name))
        # export_names.append(DRIVE_EXPORT_NAME.format(name))
    return export_names


def download_export(export_id):
    execute_bash(DOWNLOAD_EXPORT.format(export_id))


def get_export_status(export_id):
    return execute_bash(GET_EXPORT_STATUS.format(export_id)).decode(sys.stdout.encoding).strip()


def notify_slack(post):
    slack = Slack(url='https://hooks.slack.com/services/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')
    slack.post(text=post)


def create_drive_folder_for_user(user):
    first_name = user.rsplit("@")[0].split(".")[0].capitalize()
    last_name = user.rsplit("@")[0].split(".")[1].capitalize()
    return first_name + " " + last_name


def list_of_files_downloaded():
    return list(execute_bash(LIST_ALL_DOWNLOADED_FILES).decode(sys.stdout.encoding).strip().split("\n"))


def main():
    execute_bash(GET_LATEST_ALUMNI_OU_LIST)
    sleep(5)
    execute_bash(GET_ALUMNI_OU_LIST_FROM_DRIVE)
    sleep(5)
    off_boarded_users = [name for name in read_file('AlumniOU_new.txt') if name not in read_file('AlumniOU.txt')]

    if len(off_boarded_users) == 0:
        print('No offboardings...')
        exit()
    else:
        print('Initiating export for users....')
        export_names = initiate_exports(off_boarded_users)

        for export_id in export_names:
            status = get_export_status(export_id)
            sleep(5)
            print(status)
            while status != "status: COMPLETED":
                notify_slack("Export: {} is still in progress".format(export_id))
                print(status)
                sleep(5)
                print("Checking Export Status")
                status = get_export_status(export_id)
                sleep(5)
            print('Downloading Export: {}'.format(export_id))
            download_export(export_id)
            sleep(5)
            for file in list_of_files_downloaded():
                if check_for_file_in_drive(file) == 1:
                    notify_slack("Uploading Export: {}".format(file))
                    sleep(5)
                    execute_bash(UPLOAD_EXPORT.format(file))
                else:
                    print('Export already exists')
        clean_up()


if __name__ == "__main__":
    main()

