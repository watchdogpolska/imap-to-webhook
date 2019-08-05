import time
import requests

from config import get_config
import os

from parser import serialize_mail
from connection import IMAPClient
from raven import Client


def main():
    config = get_config(os.environ)
    session = requests.Session()
    session.headers = {
        'Content-Type': 'application/imap-to-webhook-v1+json'
    }
    print("Configuration: ", config)

    if config['sentry_dsn']:
        sentry_client = Client(config['sentry_dsn'])
        with sentry_client.capture_exceptions():
            loop(config, session, sentry_client)
    else:
        loop(config, session, None)


def loop(config, session, sentry_client=None):
    while True:
        client = IMAPClient(config)
        msg_ids = client.get_mail_ids()
        print("Found {} mails to download".format(len(msg_ids)))
        print("Identified following msg id", msg_ids)
        any_message = bool(msg_ids)
        if msg_ids:
            process_msg(client, msg_ids[0], config, session, sentry_client)
        client.expunge()
        client.connection_close()
        if not any_message:
            print("Waiting {} seconds".format(config['delay']))
            time.sleep(config['delay'])
            print("Resume after delay")


def process_msg(client, msg_id, config, session, sentry_client=None):
    print("Fetch message ID {}".format(msg_id))
    start = time.time()
    raw_mail = client.fetch(msg_id)
    end = time.time()
    print("Message downloaded in {} seconds".format(end - start))

    try:
        start = time.time()
        body = serialize_mail(raw_mail, config['compress_eml'])
        end = time.time()
        print("Message serialized in {} seconds".format(end - start))
        response = session.post(config['webhook'], json=body).json()
        print("Delivered message id {} :".format(msg_id), response)
        if config['imap']['on_success'] == 'delete':
            client.mark_delete(msg_id)
        elif config['imap']['on_success'] == 'move':
            client.move(msg_id, config['imap']['success'])
        else:
            print("Nothing to do for message id {}".format(msg_id))
    except Exception as e:
        if sentry_client:
            sentry_client.captureException()
        client.move(msg_id, config['imap']['error'])
        print("Unable to parse or delivery msg", e)


if __name__ == '__main__':
    main()
