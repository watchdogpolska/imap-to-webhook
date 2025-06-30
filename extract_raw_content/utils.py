import re

from lxml import html

from . import constants as const


def _replace_link_brackets(msg_body):
    """
    Normalize links i.e. replace '<', '>' wrapping the link with some symbols
    so that '>' closing the link couldn't be mistakenly taken for quotation
    marker.

    Converts msg_body into a unicode
    """
    if isinstance(msg_body, bytes):
        msg_body = msg_body.decode("utf8")

    def link_wrapper(link):
        newline_index = msg_body[: link.start()].rfind("\n")
        if msg_body[newline_index + 1] == ">":
            return link.group()
        else:
            return "@@%s@@" % link.group(1)

    msg_body = re.sub(const.RE_LINK, link_wrapper, msg_body)
    return msg_body


def _wrap_splitter_with_newline(msg_body, delimiter, content_type="text/plain"):
    """
    Splits line in two if splitter pattern preceded by some text on the same
    line (done only for 'On <date> <person> wrote:' pattern.
    """

    def splitter_wrapper(splitter):
        """Wraps splitter with new line"""
        if splitter.start() and msg_body[splitter.start() - 1] != "\n":
            return "{}{}".format(delimiter, splitter.group())
        else:
            return splitter.group()

    if content_type == "text/plain":
        msg_body = re.sub(const.RE_ON_DATE_SMB_WROTE, splitter_wrapper, msg_body)
    return msg_body


def preprocess(msg_body, delimiter, content_type="text/plain"):
    """Prepares msg_body for being stripped.

    Replaces link brackets so that they couldn't be taken for quotation marker.
    Splits line in two if splitter pattern preceded by some text on the same
    line (done only for 'On <date> <person> wrote:' pattern).

    Converts msg_body into a unicode.
    """
    msg_body = _replace_link_brackets(msg_body)
    msg_body = _wrap_splitter_with_newline(msg_body, delimiter, content_type)
    return msg_body


def is_splitter(line):
    """
    Returns Matcher object if provided string is a splitter and
    None otherwise.
    """
    for pattern in const.SPLITTER_PATTERNS:
        matcher = re.match(pattern, line)
        if matcher:
            return matcher


def html_fromstring(s: str) -> html.HtmlElement | None:
    """Parse html tree from string. Return None if the string can't be parsed."""
    try:
        return html.fromstring(s)
    except Exception:
        return None
