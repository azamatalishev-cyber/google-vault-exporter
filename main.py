import subprocess
import sys
from time import sleep
from datetime import datetime
from slack_webhook import Slack
import os

GET_LATEST_ALUMNI_OU_LIST = "/opt/gam/src/gam.py " \
                            "print " \
                            "users query " \
                            "orgUnitPath='/Alumni' > AlumniOU_new.txt"
GET_ALUMNI_OU_LIST_FROM_DRIVE = '/opt/gam/src/gam.py ' \
                                'user ' \
                                'docker-gam@docker-gam-275723.iam' \
                                '.gserviceaccount.com get ' \
                                'drivefile id ' \
                                '1HNF9-wh7Mawgab5FSL5crMqU1FfGI8PDZx7_bIPx' \
                                '-ZA format txt targetfolder ' \
                                '/opt/gam/src/'
INITIATE_MAIL_EXPORT = '/opt/gam/src/gam.py create ' \
                       'export matter uid:' \
                       '"{}" ' \
                       'corpus mail ' \
                       'name "{}" accounts {}'
GET_EXPORT_STATUS = '/opt/gam/src/gam.py info export ' \
                    'uid:"{}" "{}" | grep status:'
DOWNLOAD_EXPORT = '/opt/gam/src/gam.py download ' \
                  'export ' \
                  'uid:"{}" {} noextract ' \
                  'targetfolder ' \
                  '/tmp/'
UPLOAD_EXPORT = '/opt/gam/src/gam.py user ' \
                'docker-gam@docker-gam-275723.iam.gserviceaccount.com add ' \
                'drivefile ' \
                'localfile ' \
                '/tmp/{} parentid {} '
UPDATE_DRIVE_FILE = \
    '/opt/gam/src/gam.py user ' \
    'docker-gam@docker-gam-275723.iam.gserviceaccount.com update drivefile ' \
    'id ' \
    '1HNF9-wh7Mawgab5FSL5crMqU1FfGI8PDZx7_bIPx-ZA localfile ' \
    'AlumniOU_new.txt newfilename AlumniOU.txt'
CREATE_FOLDER_IN_DRIVE = "/opt/gam/src/gam.py user " \
                         "docker-gam@docker-gam-275723.iam.gserviceaccount" \
                         ".com create " \
                         "drivefile " \
                         "drivefilename '{}' mimetype gfolder parentid " \
                         "0AOOb5eIIkqg5Uk9PVA "
CHECK_IF_FILE_EXISTS = \
    "/opt/gam/src/gam.py user " \
    "docker-gam@docker-gam-275723.iam.gserviceaccount.com show filelist " \
    "corpora " \
    "onlyteamdrives filenamematchpattern '{}' "
MAIL_EXPORT_NAME = '{}.mail'
LIST_ALL_DOWNLOADED_FILES = 'ls /tmp/| grep .zip$ '
REMOVE_ALL_FILES = 'rm -rf /tmp/*'
CREATE_MATTER = '/opt/gam/src/gam.py create ' \
                'vaultmatter name "{}" '


def execute_bash(command):
    return subprocess.check_output(command, shell=True,
                                   stderr=subprocess.STDOUT)


def read_file(file):
    with open(file, "r", encoding='utf-8-sig') as file:
        file_list = file.readlines()
        return [item.strip() for item in file_list]


def check_for_content_in_drive(content):
    try:
        output = execute_bash(CHECK_IF_FILE_EXISTS.format(content)).decode(
            sys.stdout.encoding).strip()
        return output.rsplit(content)[-1].split('/')[-1]
    except subprocess.CalledProcessError:
        return 1


def clean_up():
    sleep(5)
    execute_bash(UPDATE_DRIVE_FILE)


def initiate_exports(off_boarded_users, matter_id):
    export_names = []
    for name in off_boarded_users:
        try:
            execute_bash(INITIATE_MAIL_EXPORT.format(matter_id,
                                                     MAIL_EXPORT_NAME.format(
                                                         name).strip(), name))
            print('Initiating Mail Export for {}'.format(name))
            export_names.append(MAIL_EXPORT_NAME.format(name))
        except subprocess.CalledProcessError as e:
            print(e)
            print('ERROR Initiating: Check user account {}'.format(name))
            pass
    if not export_names:
        log('No Exports have been initiated...exiting job')
        exit()
    return export_names


def download_export(matter_id, export_id):
    try:
        execute_bash(DOWNLOAD_EXPORT.format(matter_id, export_id))
    except subprocess.CalledProcessError as e:
        log('ERROR DOWNLOADING: Check container logs, pod terminating')
        print(e)
        exit()


def get_export_status(matter_id, export_id):
    return execute_bash(
        GET_EXPORT_STATUS.format(matter_id, export_id)).decode(
        sys.stdout.encoding).strip()


def create_matter():
    matter_name = datetime.today().strftime("%d/%m/%Y %H:%M:%S - offboarding")
    return execute_bash(CREATE_MATTER.format(matter_name)).decode().strip(
    ).split('(')[1].split(')')[0]


def create_user_folder_name(user):
    try:
        split_content = user.split('@')
        extracted_name = split_content[0].split('.')
        first_name = extracted_name[0].capitalize()
        last_name = extracted_name[1].capitalize()

        return first_name + ' ' + last_name + ' ' + 'Archive'

    except IndexError:
        return user.split('@')[0].capitalize()


def create_folder(folder_name):
    output = execute_bash(CREATE_FOLDER_IN_DRIVE.format(folder_name)).decode(
        sys.stdout.encoding).strip()
    return output.split('(')[1].split(')')[0]


def notify_slack(post):
    slack = Slack(url=os.environ.get('SLACK_URL'))
    slack.post(text=post)


def list_of_files_downloaded():
    return list(execute_bash(LIST_ALL_DOWNLOADED_FILES).decode(
        sys.stdout.encoding).strip().split("\n"))


def upload_export(file, folder_id):
    try:
        execute_bash(UPLOAD_EXPORT.format(file, folder_id))
    except subprocess.CalledProcessError as e:
        log('ERROR UPLOADING: Check container logs, pod terminating..')
        print(e)
        exit()


def log(text):
    print(text)
    notify_slack(text)


def main():
    # Compare two lists and get delta to check for off boarded users.
    execute_bash(GET_LATEST_ALUMNI_OU_LIST)
    execute_bash(GET_ALUMNI_OU_LIST_FROM_DRIVE)
    off_boarded_users = [name for name in read_file('AlumniOU_new.txt') if
                         name not in read_file('AlumniOU.txt')]

    # Start the exports for off boarded users if condition is met
    if not off_boarded_users:
        log('No offboardings...')
        exit()

    log('Initiating export for users....')
    matter_id = create_matter()
    log("Created Matter ID: {}".format(matter_id))
    export_names = initiate_exports(off_boarded_users, matter_id)

    # Start archiving process, create folder name in Google Drive
    for export_id in export_names:
        folder_name = create_user_folder_name(export_id)
        log("Checking for duplicate folders for {}".format(folder_name))
        folder_id = check_for_content_in_drive(folder_name)

        if folder_id == 1:
            log('Creating folder...')
            folder_id = create_folder(folder_name)

        # Check repeatedly until the export is ready
        status = get_export_status(matter_id, export_id)
        while status != "status: COMPLETED":
            log('Export: {} is still in progress'.format(export_id))
            sleep(1800)
            status = get_export_status(matter_id, export_id)

        # Download export
        log("Download Starting")
        download_export(matter_id, export_id)
        log("Export: {} download finished".format(export_id))

        # Uploading to Google Drive
        for file in list_of_files_downloaded():
            log("Uploading Export: {}".format(file))
            upload_export(file, folder_id)
            log("Export Uploaded: {}".format(file))

        # Clean up
        execute_bash(REMOVE_ALL_FILES)
    clean_up()


if __name__ == "__main__":
    main()
