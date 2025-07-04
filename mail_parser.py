import base64
import binascii
import gzip
import json
import quopri
import re
import uuid
from email import policy
from email.parser import BytesParser
from io import BytesIO

import mailparser
from html2text import html2text

from extract_raw_content.html import strip_email_quote
from extract_raw_content.text import (
    exctract_quoted_from_plain,
    extract_non_quoted_from_plain,
)

# from extract_raw_content.utils import register_xpath_extensions

decoder_map = {
    "base64": base64.b64decode,
    "": lambda payload: payload.encode("utf-8"),
    "7bit": lambda payload: payload.encode("utf-8"),
    "8bit": lambda payload: payload.encode("utf-8"),
    "quoted-printable": quopri.decodestring,
}

JSON_MIME = "application/json"
GZ_MIME = "application/gzip"
EML_MIME = "message/rfc822"
BINARY_MIME = "application/octet-stream"

# register_xpath_extensions()


def get_text(mail):
    raw_content, html_content, plain_content, html_quote, plain_quote = (
        "",
        "",
        "",
        "",
        "",
    )

    if mail.text_html:
        raw_content = "".join(mail.text_html).replace("\r\n", "\n")
        html_content, html_quote = strip_email_quote(raw_content)
        # extract_from_html(raw_content)
        plain_content = html2text(html_content)

    if mail.text_plain or not plain_content:
        raw_content = "".join(mail.text_plain)
        plain_content = extract_non_quoted_from_plain(raw_content)
        plain_quote = exctract_quoted_from_plain(raw_content, plain_content)

    # 'content' item holds plain_content and 'quote' item holds plain_quote
    # (with HTML stripped off).
    # These names are used for backward compatibility.
    return {
        "html_content": html_content,
        "content": plain_content,
        "html_quote": html_quote,
        "quote": plain_quote,
    }


def get_auto_reply_type(mail):
    if "report-type=disposition-notification" in mail.content_type:
        return "disposition-notification"
    if mail.auto_submitted and mail.auto_submitted.lower() == "auto-replied":
        return "vacation-reply"
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
        for match in [
            re.search(r"for ([a-zA-Z0-9\-]+@[a-zA-Z.]+)", r["others"])
            for r in mail.received
            if "others" in r
        ]
        if match
    )
    to_plus.update(r["for"] for r in mail.received if "for" in r)
    return list(to_plus)


def get_attachments(mail):
    attachments = []
    for attachment in mail.attachments:
        if attachment["content_transfer_encoding"] not in decoder_map:
            msg = "Invalid Content-Transfer Encoding ({}) in msg {}.".format(
                attachment["content_transfer_encoding"], mail.message_id
            )
            raise Exception(msg)
        decoder = decoder_map[attachment["content_transfer_encoding"]]

        filename = attachment["filename"]

        try:
            content = decoder(attachment["payload"])
            attachments.append((filename, BytesIO(content), BINARY_MIME))
        except (binascii.Error, ValueError):
            print(
                "Unable to parse attachment '{}' in {} \n".format(
                    filename, mail.message_id
                )
            )
    return attachments


def get_eml(raw_mail, compress_eml):
    content = raw_mail

    if compress_eml:
        file = BytesIO()
        with gzip.open(file, "wb") as f:
            f.write(raw_mail)
        content = file.getvalue()
    return content


def get_manifest(mail, compress_eml):
    return {
        "headers": {
            "subject": mail.subject,
            "to": [x[1] for x in mail.to] if mail.to else [],
            "to+": get_to_plus(mail),
            "from": [x[1] for x in mail._from] if mail.from_ else [],
            "date": mail.date.isoformat() if mail.date else [],
            "cc": [x[1] for x in mail.cc] if mail.cc else [],
            "message_id": mail.message_id,
            "auto_reply_type": get_auto_reply_type(mail),
        },
        "version": "v2",
        "text": get_text(mail),
        "files_count": len(mail.attachments),
        "eml": {
            "compressed": compress_eml,
        },
    }


def parse_mail_from_bytes(raw_bytes):
    """
    Patch for mailparser bug.
    Return a MailParser.MailParser object whose UTF-8 text parts are always
    decoded correctly, even when the original message uses 7bit/8bit CTE.
    """
    mp = mailparser.parse_from_bytes(raw_bytes)

    # Fast-exit if the message never uses 7bit/8bit encodings
    _CTE_78BIT_RE = re.compile(rb"^Content-Transfer-Encoding:\s*[78]bit\b", re.I | re.M)
    if not _CTE_78BIT_RE.search(raw_bytes):
        return mp

    # Re-parse with the std-lib email package
    msg = BytesParser(policy=policy.default).parsebytes(raw_bytes)

    plain_parts, html_parts, other_text_parts = [], [], []
    for part in msg.walk():
        if part.is_multipart():
            continue
        if part.get_content_maintype() != "text":
            continue

        txt = part.get_content()
        ctype = part.get_content_type()
        if ctype == "text/plain":
            plain_parts.append(txt)
        elif ctype == "text/html":
            html_parts.append(txt)
        else:
            other_text_parts.append(txt)

    # Patch MailParser’s internal lists
    mp._text_plain = plain_parts
    mp._text_html = html_parts
    mp._text_not_managed = other_text_parts

    # Invalidate the cached body so the property recomputes on demand
    if hasattr(mp, "_body"):
        mp._body = None

    return mp


def serialize_mail(raw_mail, compress_eml=False):
    mail = parse_mail_from_bytes(raw_mail)
    files = []
    # Build manifest
    body = get_manifest(mail, compress_eml)
    files.append(
        (
            "manifest",
            ("manifest.json", BytesIO(json.dumps(body).encode("utf-8")), JSON_MIME),
        )
    )
    # Build eml
    eml_ext = "eml.gz" if compress_eml else "eml"
    eml_name = "{}.{}".format(uuid.uuid4().hex, eml_ext)
    eml_mime = GZ_MIME if compress_eml else EML_MIME

    files.append(
        ("eml", (eml_name, BytesIO(get_eml(raw_mail, compress_eml)), eml_mime))
    )
    # Build attachments
    for att in get_attachments(mail):
        files.append(("attachment", att))
    return files


if __name__ == "__main__":
    import sys

    with open(sys.argv[1], "rb") as fp:
        raw_mail = fp.read()
        mail = parse_mail_from_bytes(raw_mail)
        body = get_manifest(mail, False)
        json.dump(body, sys.stdout, indent=4)
