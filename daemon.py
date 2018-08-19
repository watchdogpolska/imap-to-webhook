import time
import requests

from config import get_config
import os

from parser import serialize_mail
from connection import get_mail_ids, connection_initialize, connection_close


def move(client, msg_id, folder):
    print("Going to move {} to {}".format(msg_id, folder))
    copy(client, folder, msg_id)
    mark_delete(client, msg_id)


def mark_delete(client, msg_id):
    print("Going to mark as deleted {}".format(msg_id))
    mark_delete_result, data = client.uid('STORE', msg_id, '+FLAGS', '(\Deleted)')
    if mark_delete_result != 'OK':
        raise Exception("Failed to mark as deleted msg {}".format(msg_id))


def copy(client, folder, msg_id):
    print("Going to copy {} to {}".format(msg_id, folder))
    copy_result, data = client.uid('COPY', msg_id, folder)
    print("Copy data", data)
    if copy_result != 'OK':
        raise Exception("Failed to copy msg {} to {}".format(msg_id, folder))


def main():
    config = get_config(os.environ)
    session = requests.Session()
    while True:
        client = connection_initialize(config)
        msg_ids = get_mail_ids(client)
        print("Found {} mails to download".format(len(msg_ids)))

        for msg_id in msg_ids:
            print("Fetch message ID {}".format(msg_id))
            result_fetch, data = client.uid('FETCH', "{0}:{0} RFC822".format(msg_id))
            if result_fetch != 'OK':
                raise Exception("Fetch failed!")

            raw_mail = data[0][1]

            try:
                body = serialize_mail(raw_mail, config['compress_eml'])
                try:
                    print("Delivered message id {} :".format(msg_id), session.post(config['webhook'], json=body).json())
                    if config['imap']['on_success'] == 'delete':
                        mark_delete(client, msg_id)
                    elif config['imap']['on_success'] == 'move':
                        move(client, msg_id, config['imap']['success'])
                    else:
                        print("Nothing do for message id {}".format(msg_id))
                except Exception as e:
                    move(client, msg_id, config['imap']['error'])
                    print("Unable to delivery message", e)
            except Exception as e:
                move(client, msg_id, config['imap']['error'])
                print("Unable to parse msg", e)
        connection_close(client)
        delay(config)


def delay(config):
    print("Waiting {} seconds".format(config['delay']))
    time.sleep(config['delay'])
    print("Resume after delay")


if __name__ == '__main__':
    main()
