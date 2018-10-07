import base64
import binascii
import quopri
import re
import uuid
from io import BytesIO
import gzip

from html2text import html2text
import talon
import mailparser

talon.init()

decoder_map = {
    'base64': base64.b64decode,
    '': lambda payload: payload.encode('utf-8'),
    '7bit': lambda payload: payload.encode('utf-8'),
    'quoted-printable': quopri.decodestring
}


def get_text(mail):
    raw_content, content, quote = '', '', ''

    if mail.text_html:
        raw_content = "".join(mail.text_html).replace("\r\n", "\n")
        content = talon.quotations.extract_from_html(raw_content)
        quote = raw_content.replace(content, '')
        content = html2text(content)

    if mail.text_plain or not content:
        raw_content = "".join(mail.text_plain)
        content = talon.quotations.extract_from_plain(raw_content)
        quote = raw_content.replace(content, '')

    return {
        'content': content,
        'quote': quote
    }


def get_auto_reply_type(mail):
    if 'report-type=disposition-notification' in mail.content_type:
        return 'disposition-notification'
    if mail.auto_submitted and mail.auto_submitted.lower() == 'auto-replied':
        return 'vacation-reply'
    return None


def get_to_plus(mail):
    to_plus = set([x[1] for x in mail.to] if mail.to else [])

    if mail.delivered_to:
        to_plus.update(x[1] for x in mail.delivered_to)
    if mail.cc:
        to_plus.update(x[1] for x in mail.cc)
    if mail.bcc:
        to_plus.update(x[1] for x in mail.bcc)
    to_plus.update(
        match.group(1)
        for match in
        [
            re.search('for ([a-zA-Z0-9\-]+@[a-zA-Z.]+)', r['others'])
            for r in mail.received
            if 'others' in r
        ]
        if match
    )
    to_plus.update(r['for'] for r in mail.received if 'for' in r)
    return list(to_plus)


def get_attachments(mail):
    attachments = []
    for attachment in mail.attachments:
        if attachment['content_transfer_encoding'] not in decoder_map:
            msg = "Invalid Content-Transfer Encoding ({}) in msg {}.".format(
                attachment['content_transfer_encoding'], mail.message_id
            )
            raise Exception(msg)
        decoder = decoder_map[attachment['content_transfer_encoding']]

        filename = attachment['filename']

        try:
            content = decoder(attachment['payload'])
            attachments.append({
                'filename': filename,
                'content': base64.b64encode(content).decode('utf-8')
            })
        except (binascii.Error, ValueError) as e:
            print("Unable to parse attachment '{}' in {} \n".
                  format(filename, mail.message_id))
    return attachments


def get_eml(raw_mail, compress_eml):
    content = raw_mail

    if compress_eml:
        file = BytesIO()
        with gzip.open(file, 'wb') as f:
            f.write(raw_mail)
        content = file.getvalue()

    ext = '.sql.gz' if compress_eml else '.gz'
    return {
        'filename': "{}.{}".format(uuid.uuid4().hex, ext),
        'content': base64.b64encode(content).decode('utf-8'),
        'compressed': True
    }


def serialize_mail(raw_mail, compress_eml=False):
    mail = mailparser.parse_from_bytes(raw_mail)

    body = {
        'headers': {
            'subject': mail.subject,
            'to': [x[1] for x in mail.to] if mail.to else [],
            'to+': get_to_plus(mail),
            'from': [x[1] for x in mail._from] if mail.from_ else [],
            'date': mail.date.isoformat() if mail.date else [],
            'cc': [x[1] for x in mail.cc] if mail.cc else [],
            'message_id': mail.message_id,
            'auto_reply_type': get_auto_reply_type(mail)
        },
        'text': get_text(mail),
        'eml': get_eml(raw_mail, compress_eml),
        'files_count': len(mail.attachments),
        'files': get_attachments(mail)
    }
    return body
