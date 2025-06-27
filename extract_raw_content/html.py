import re
from copy import deepcopy

from lxml import html
from lxml.cssselect import CSSSelector
from lxml.html import html5parser

from . import constants as const
from . import html_quotations, utils


def process_marked_lines(lines, markers, return_flags=[False, -1, -1]):
    """Run regexes against message's marked lines to strip quotations.

    Return only last message lines.
    >>> mark_message_lines(['Hello', 'From: foo@bar.com', '', '> Hi', 'tsem'])
    ['Hello']

    Also returns return_flags.
    return_flags = [were_lines_deleted, first_deleted_line,
                    last_deleted_line]
    """
    markers = "".join(markers)
    # if there are no splitter there should be no markers
    if "s" not in markers and not re.search("(me*){3}", markers):
        markers = markers.replace("m", "t")
    if re.match("[te]*f", markers):
        return_flags[:] = [False, -1, -1]
        return lines
    # inlined reply
    # use lookbehind assertions to find overlapping entries e.g. for 'mtmtm'
    # both 't' entries should be found
    for inline_reply in re.finditer("(?<=m)e*((?:t+e*)+)m", markers):
        # long links could break sequence of quotation lines but they shouldn't
        # be considered an inline reply
        links = const.RE_PARENTHESIS_LINK.search(
            lines[inline_reply.start() - 1]
        ) or const.RE_PARENTHESIS_LINK.match(lines[inline_reply.start()].strip())
        if not links:
            return_flags[:] = [False, -1, -1]
            return lines

    # cut out text lines coming after splitter if there are no markers there
    quotation = re.search("(se*)+((t|f)+e*)+", markers)
    if quotation:
        return_flags[:] = [True, quotation.start(), len(lines)]
        return lines[: quotation.start()]

    # handle the case with markers
    quotation = const.RE_QUOTATION.search(markers) or const.RE_EMPTY_QUOTATION.search(
        markers
    )
    if quotation:
        return_flags[:] = True, quotation.start(1), quotation.end(1)
        return lines[: quotation.start(1)] + lines[quotation.end(1) :]

    return_flags[:] = [False, -1, -1]
    return lines


def mark_message_lines(lines):
    """Mark message lines with markers to distinguish quotation lines.

    Markers:

    * e - empty line
    * m - line that starts with quotation marker '>'
    * s - splitter line
    * t - presumably lines from the last message in the conversation

    >>> mark_message_lines(['answer', 'From: foo@bar.com', '', '> question'])
    'tsem'
    """
    markers = ["e" for _ in lines]
    i = 0
    while i < len(lines):
        if not lines[i].strip():
            markers[i] = "e"  # empty line
        elif const.QUOT_PATTERN.match(lines[i]):
            markers[i] = "m"  # line with quotation marker
        elif const.RE_FWD.match(lines[i]):
            markers[i] = "f"  # ---- Forwarded message ----
        else:
            # in case splitter is spread across several lines
            splitter = utils.is_splitter(
                "\n".join(lines[i : i + const.SPLITTER_MAX_LINES])
            )

            if splitter:
                # append as many splitter markers as lines in splitter
                splitter_lines = splitter.group().splitlines()
                for j in range(len(splitter_lines)):
                    markers[i + j] = "s"

                # skip splitter lines
                i += len(splitter_lines) - 1
            else:
                # probably the line from the last message in the conversation
                markers[i] = "t"
        i += 1
    return "".join(markers)


def _rm_excessive_newlines(s):
    """Remove excessive newlines that often happen due to tons of divs"""
    return const._RE_EXCESSIVE_NEWLINES.sub("\n\n", s).strip()


def _encode_utf8(s):
    """Encode in 'utf-8' if unicode"""
    return s.encode("utf-8") if isinstance(s, str) else s


def html_too_big(s):
    if isinstance(s, str):
        s = s.encode("utf8")
    return s.count(b"<") > const._MAX_TAGS_COUNT


def html_document_fromstring(s):
    """Parse html tree from string. Return None if the string can't be parsed."""
    if isinstance(s, str):
        s = s.encode("utf8")
    try:
        if html_too_big(s):
            return None
        return html5parser.document_fromstring(s, parser=utils._html5lib_parser())
    except Exception:
        pass


def html_tree_to_text(tree):
    for style in CSSSelector("style")(tree):
        style.getparent().remove(style)
    for c in tree.xpath("//comment()"):
        parent = c.getparent()
        # comment with no parent does not impact produced text
        if parent is None:
            continue
        parent.remove(c)
    text = ""
    for el in tree.iter():
        el_text = (el.text or "") + (el.tail or "")
        if len(el_text) > 1:
            if el.tag in const._BLOCKTAGS:
                text += "\n"
            if el.tag == "li":
                text += "  * "
            text += el_text.strip() + " "

            # add href to the output
            href = el.attrib.get("href")
            if href:
                text += "(%s) " % href
        if el.tag in const._HARDBREAKS and text and not text.endswith("\n"):
            text += "\n"
    retval = _rm_excessive_newlines(text)
    return _encode_utf8(retval)


def _readable_text_empty(html_tree):
    return not bool(html_tree_to_text(html_tree).strip())


def _extract_from_html(msg_body):
    """
    Extract not quoted message from provided html message body
    using tags and plain text algorithm.

    Cut out the 'blockquote', 'gmail_quote' tags.
    Cut Microsoft quotations.

    Then use plain text algorithm to cut out splitter or
    leftover quotation.
    This works by adding checkpoint text to all html tags,
    then converting html to text,
    then extracting quotations from text,
    then checking deleted checkpoints,
    then deleting necessary tags.

    function returns two values:
        clean_html, quote_html = _extract_from_html(body)

    Both values are Unicode strings; quote_html is an empty string when
    no quotation is detected.
    """
    if msg_body.strip() == b"":
        empty = msg_body.decode("utf8") if isinstance(msg_body, bytes) else msg_body
        return empty, ""

    msg_body = msg_body.replace(b"\r\n", b"\n")
    html_tree = html_document_fromstring(msg_body)
    if html_tree is None:
        fallback = msg_body.decode("utf8") if isinstance(msg_body, bytes) else msg_body
        return fallback, ""

    cut_quotations = (
        html_quotations.cut_gmail_quote(html_tree)
        or html_quotations.cut_zimbra_quote(html_tree)
        or html_quotations.cut_blockquote(html_tree)
        or html_quotations.cut_microsoft_quote(html_tree)
        or html_quotations.cut_by_id(html_tree)
        or html_quotations.cut_from_block(html_tree)
    )

    # TWO working copies: one for the body, one for the quote
    html_tree_body = deepcopy(html_tree)  # -> cleaned message
    html_tree_quote = deepcopy(html_tree)  # -> quoted part only

    number_of_checkpoints = html_quotations.add_checkpoint(html_tree, 0)
    quotation_checkpoints = [False] * number_of_checkpoints
    plain_text = html_tree_to_text(html_tree)
    plain_text = utils.preprocess(plain_text, "\n", content_type="text/html")
    lines = plain_text.splitlines()
    # Don't process too long messages
    if len(lines) > const.MAX_LINES_COUNT:
        original = msg_body.decode("utf8") if isinstance(msg_body, bytes) else msg_body
        return original, ""
    # Collect checkpoints on each line
    line_checkpoints = [
        [
            int(i[4:-4])  # Only checkpoint number
            for i in re.findall(html_quotations.CHECKPOINT_PATTERN, line)
        ]
        for line in lines
    ]
    # Remove checkpoints
    lines = [re.sub(html_quotations.CHECKPOINT_PATTERN, "", line) for line in lines]

    # Use plain text quotation extracting algorithm
    markers = mark_message_lines(lines)
    return_flags = []
    process_marked_lines(lines, markers, return_flags)
    lines_were_deleted, first_deleted, last_deleted = return_flags

    if not lines_were_deleted and not cut_quotations:  # nothing to cut
        original = msg_body.decode("utf8") if isinstance(msg_body, bytes) else msg_body
        return original, ""

    # collect checkpoints that belong to quotation
    if lines_were_deleted:
        for i in range(first_deleted, last_deleted):
            for checkpoint in line_checkpoints[i]:
                quotation_checkpoints[checkpoint] = True

    # --- build the two trees ---------------------------------------------
    # 1. message without quotation
    html_quotations.delete_quotation_tags(html_tree_body, 0, quotation_checkpoints)

    # 2. quotation only  – delete the *other* checkpoints
    inverted = [not c for c in quotation_checkpoints]
    html_quotations.delete_quotation_tags(html_tree_quote, 0, inverted)

    # guard against corner cases where everything vanished
    if _readable_text_empty(html_tree_body):
        original = msg_body.decode("utf8") if isinstance(msg_body, bytes) else msg_body
        return original, ""

    clean_html = html.tostring(html_tree_body, encoding="unicode")
    quote_html = (
        ""
        if _readable_text_empty(html_tree_quote)
        else html.tostring(html_tree_quote, encoding="unicode")
    )

    return clean_html, quote_html


def extract_from_html(msg_body):
    """
    Extract not quoted message  and quote from provided html message body
    using tags and plain text algorithm.

    function returns two values:
        clean_html, quote_html = extract_from_html(body)

    Both values are Unicode strings; quote_html is an empty string when
    no quotation is detected.
    """
    clean_html, quote_html = _extract_from_html(msg_body)

    if isinstance(clean_html, bytes):
        clean_html = clean_html.decode("utf8")
    if isinstance(quote_html, bytes):
        quote_html = quote_html.decode("utf8")

    return clean_html, quote_html
