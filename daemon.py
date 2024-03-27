import copy
import os
import time

import requests
import sentry_sdk

from config import get_config
from connection import IMAPClient
from mail_parser import serialize_mail

__version__ = "1.0.01"


def main():
    config = get_config(os.environ)
    config_printout = copy.deepcopy(config)
    if "password" in config_printout.get("imap", {}):
        config_printout["imap"]["password"] = "********"
        print("Configuration to print: ", config_printout)
        print("Configuration: ", config)

    session = requests.Session()
    print(f"Starting daemon version {__version__}")
    print("Configuration: ", config_printout)
    sentry_sdk.init(dsn=config["sentry_dsn"], traces_sample_rate=1.0)
    if config["sentry_dsn"]:
        try:
            loop(config, session)
        except Exception as e:
            sentry_sdk.capture_exception(e)
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
            print("Waiting {} seconds".format(config["delay"]))
            time.sleep(config["delay"])
            print("Resume after delay")


def process_msg(client, msg_id, config, session, sentry_client=None):
    print("Fetch message ID {}".format(msg_id))
    start = time.time()
    raw_mail = client.fetch(msg_id)
    end = time.time()
    print("Message downloaded in {} seconds".format(end - start))

    try:
        start = time.time()
        body = serialize_mail(raw_mail, config["compress_eml"])
        end = time.time()
        print("Message serialized in {} seconds".format(end - start))
        res = session.post(config["webhook"], files=body)
        print("Received response:", res.text)
        res.raise_for_status()
        response = res.json()
        print("Delivered message id {} :".format(msg_id), response)
        if config["imap"]["on_success"] == "delete":
            client.mark_delete(msg_id)
        elif config["imap"]["on_success"] == "move":
            client.move(msg_id, config["imap"]["success"])
        else:
            print("Nothing to do for message id {}".format(msg_id))
    except Exception as e:
        sentry_sdk.capture_exception(e)
        client.move(msg_id, config["imap"]["error"])
        print("Unable to parse or delivery msg", e)


if __name__ == "__main__":
    main()
