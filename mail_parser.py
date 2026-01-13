import base64
import binascii
import gzip
import json
import quopri
import re
import uuid
from email import policy
from email.parser import BytesParser
from email.utils import getaddresses
from io import BytesIO

import mailparser
from email_validator import validate_email
from html2text import html2text

from extract_raw_content.html import strip_email_quote
from extract_raw_content.text import (
    exctract_quoted_from_plain,
    extract_non_quoted_from_plain,
)

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
_BASIC_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+$")  # intentionally permissive


def validate_and_normalize(addr: str) -> str | None:
    if not addr:
        return None
    addr = addr.strip().strip("<>").strip().strip('"').strip("'")

    # First try strict/standard validation
    try:
        v = validate_email(addr, check_deliverability=False)
        return v.normalized.lower()
    except Exception:
        # Fallback: accept internal domains if they look like an email
        if _BASIC_EMAIL_RE.match(addr):
            return addr.lower()
        return None


def _coerce_addresses(source):
    """
    Normalize various address shapes into list[tuple(display_name, email)].
    Supports:
      - list/tuple/set of (name, email)
      - string headers: "Name <a@b>", "a@b, c@d"
      - dicts: {"email": ...} / {"address": ...} / {"name": ..., "email": ...}
      - list of dicts (common in some parsers)
    """
    if not source:
        return []

    # Already in [(name, email), ...] form
    if isinstance(source, (list, tuple, set)):
        src_list = list(source)
        if (
            src_list
            and isinstance(src_list[0], (list, tuple))
            and len(src_list[0]) >= 2
        ):
            return [(x[0], x[1]) for x in src_list if x and len(x) >= 2]
        # list of dicts
        if src_list and isinstance(src_list[0], dict):
            out = []
            for d in src_list:
                if not d:
                    continue
                email = d.get("email") or d.get("address")
                name = d.get("name") or d.get("display_name") or ""
                if email:
                    out.append((name, email))
            return out

    # Single dict
    if isinstance(source, dict):
        email = source.get("email") or source.get("address")
        name = source.get("name") or source.get("display_name") or ""
        return [(name, email)] if email else []

    # Raw header string
    if isinstance(source, str):
        return getaddresses([source])

    return []


def extract_emails(source):
    pairs = _coerce_addresses(source)
    normalized = [validate_and_normalize(email) for _, email in pairs if email]
    return [x for x in normalized if x]


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
    to_plus = set(extract_emails(mail.to)) if mail.to else set()

    to_plus.update(extract_emails(mail.delivered_to))
    to_plus.update(extract_emails(mail.cc))
    to_plus.update(extract_emails(mail.bcc))
    to_plus.update(
        normalized
        for r in mail.received
        if "others" in r
        for match in [
            re.search(
                r"for ([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)", r["others"]
            )
        ]
        if match
        for normalized in [validate_and_normalize(match.group(1))]
        if normalized
    )
    to_plus.update(
        normalized
        for r in mail.received
        if "for" in r
        for normalized in [validate_and_normalize(r["for"])]
        if normalized
    )
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


def _has_any_email(x) -> bool:
    if not x:
        return False
    # list/tuple of (name, email)
    if isinstance(x, (list, tuple, set)):
        for item in x:
            if not item:
                continue
            if isinstance(item, (list, tuple)) and len(item) >= 2 and item[1]:
                return True
        return False
    # string header
    if isinstance(x, str):
        return bool(x.strip())
    # dict
    if isinstance(x, dict):
        return bool(x.get("email") or x.get("address") or x.get("From"))
    return False


def _pick_addresses(*candidates):
    for c in candidates:
        if _has_any_email(c):
            return c
    return None


def get_manifest(mail, compress_eml):
    from_source = _pick_addresses(
        getattr(mail, "_from", None),  # prefer _from
        getattr(mail, "from_", None),  # then from_
        getattr(mail, "from", None),  # then from
        getattr(mail, "headers", {}).get("From"),
        getattr(mail, "mail", {}).get("from"),
    )
    from_result = extract_emails(from_source)
    return {
        "headers": {
            "subject": mail.subject,
            "to": extract_emails(mail.to),
            "to+": get_to_plus(mail),
            "from": from_result,
            "date": mail.date.isoformat() if mail.date else [],
            "cc": extract_emails(mail.cc),
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


def _patch_addresses_from_stdlib(mp, raw_bytes):
    """
    Patch mp._from/mp.to/mp.cc when mailparser fails to parse addresses.
    Uses Python stdlib email parsing as a reliable fallback.
    """
    msg = BytesParser(policy=policy.default).parsebytes(raw_bytes)

    def header_pairs(name: str):
        # returns list[(display_name, email)]
        pairs = getaddresses(msg.get_all(name, []))
        return [(n, a) for (n, a) in pairs if a]

    # Patch only if mailparser produced empty/invalid address tuples
    from_pairs = header_pairs("From")
    if from_pairs and (
        not getattr(mp, "_from", None) or all(not x[1] for x in mp._from if x)
    ):
        mp._from = from_pairs
        if getattr(mp, "from_", None) is not None:
            mp.from_ = from_pairs

    to_pairs = header_pairs("To")
    if to_pairs and (not getattr(mp, "to", None) or all(not x[1] for x in mp.to if x)):
        mp.to = to_pairs

    cc_pairs = header_pairs("Cc")
    if cc_pairs and (not getattr(mp, "cc", None) or all(not x[1] for x in mp.cc if x)):
        mp.cc = cc_pairs

    return mp


def parse_mail_from_bytes(raw_bytes):
    """
    Patch for mailparser bug.
    Return a MailParser.MailParser object whose UTF-8 text parts are always
    decoded correctly, even when the original message uses 7bit/8bit CTE.
    """
    mp = mailparser.parse_from_bytes(raw_bytes)

    # Patch addresses if mailparser produced empty ones
    mp = _patch_addresses_from_stdlib(mp, raw_bytes)

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
