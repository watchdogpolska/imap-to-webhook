import os
import json
import unittest

from parser import serialize_mail


def get_email_as_bytes(name):
    with open(
            os.path.join(
                os.path.dirname(__file__),
                'mails',
                name,
            ),
            'rb'
    ) as f:
        return f.read()


class TestMain(unittest.TestCase):
    def test_disposition_notification(self):
        mail = get_email_as_bytes('disposition-notification.eml')
        body = serialize_mail(mail)
        body_map = {k:v for k, v in body}
        manifest = json.loads(body_map['manifest'][1].read().decode('utf-8'))
        self.assertTrue(
            manifest['headers']['auto_reply_type'],
            'disposition-notification'
        )

    def test_vacation_reply(self):
        mail = get_email_as_bytes('vacation-reply.eml')
        body = serialize_mail(mail)
        body_map = {k:v for k, v in body}
        manifest = json.loads(body_map['manifest'][1].read().decode('utf-8'))
        self.assertTrue(
            manifest['headers']['auto_reply_type'],
            'vacation-reply'
        )

    def test_html_only(self):
        mail = get_email_as_bytes('html_only.eml')
        body = serialize_mail(mail)
        body_map = {k:v for k, v in body}
        manifest = json.loads(body_map['manifest'][1].read().decode('utf-8'))
        self.assertTrue(manifest['text']['content'])
        self.assertTrue(manifest['text']['html_content'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
