import re
from typing import Tuple

# from copy import deepcopy
from bs4 import BeautifulSoup, Comment, NavigableString, Tag

# from lxml import html
# from lxml.cssselect import CSSSelector
# from lxml.html import html5parser

# from . import constants as const

# from . import html_quotations, utils
# from . import utils


# def process_marked_lines(lines, markers, return_flags=[False, -1, -1]):
#     """Run regexes against message's marked lines to strip quotations.

#     Return only last message lines.
#     >>> mark_message_lines(['Hello', 'From: foo@bar.com', '', '> Hi', 'tsem'])
#     ['Hello']

#     Also returns return_flags.
#     return_flags = [were_lines_deleted, first_deleted_line,
#                     last_deleted_line]
#     """
#     markers = "".join(markers)
#     # if there are no splitter there should be no markers
#     if "s" not in markers and not re.search("(me*){3}", markers):
#         markers = markers.replace("m", "t")
#     if re.match("[te]*f", markers):
#         return_flags[:] = [False, -1, -1]
#         return lines
#     # inlined reply
#     # use lookbehind assertions to find overlapping entries e.g. for 'mtmtm'
#     # both 't' entries should be found
#     for inline_reply in re.finditer("(?<=m)e*((?:t+e*)+)m", markers):
#         # long links could break sequence of quotation lines but they shouldn't
#         # be considered an inline reply
#         links = const.RE_PARENTHESIS_LINK.search(
#             lines[inline_reply.start() - 1]
#         ) or const.RE_PARENTHESIS_LINK.match(lines[inline_reply.start()].strip())
#         if not links:
#             return_flags[:] = [False, -1, -1]
#             return lines

#     # cut out text lines coming after splitter if there are no markers there
#     quotation = re.search("(se*)+((t|f)+e*)+", markers)
#     if quotation:
#         return_flags[:] = [True, quotation.start(), len(lines)]
#         return lines[: quotation.start()]

#     # handle the case with markers
#     quotation = const.RE_QUOTATION.search(markers) or const.RE_EMPTY_QUOTATION.search(
#         markers
#     )
#     if quotation:
#         return_flags[:] = True, quotation.start(1), quotation.end(1)
#         return lines[: quotation.start(1)] + lines[quotation.end(1) :]

#     return_flags[:] = [False, -1, -1]
#     return lines


# def mark_message_lines(lines):
#     """Mark message lines with markers to distinguish quotation lines.

#     Markers:

#     * e - empty line
#     * m - line that starts with quotation marker '>'
#     * s - splitter line
#     * t - presumably lines from the last message in the conversation

#     >>> mark_message_lines(['answer', 'From: foo@bar.com', '', '> question'])
#     'tsem'
#     """
#     markers = ["e" for _ in lines]
#     i = 0
#     while i < len(lines):
#         if not lines[i].strip():
#             markers[i] = "e"  # empty line
#         elif const.QUOT_PATTERN.match(lines[i]):
#             markers[i] = "m"  # line with quotation marker
#         elif const.RE_FWD.match(lines[i]):
#             markers[i] = "f"  # ---- Forwarded message ----
#         else:
#             # in case splitter is spread across several lines
#             splitter = utils.is_splitter(
#                 "\n".join(lines[i : i + const.SPLITTER_MAX_LINES])
#             )

#             if splitter:
#                 # append as many splitter markers as lines in splitter
#                 splitter_lines = splitter.group().splitlines()
#                 for j in range(len(splitter_lines)):
#                     markers[i + j] = "s"

#                 # skip splitter lines
#                 i += len(splitter_lines) - 1
#             else:
#                 # probably the line from the last message in the conversation
#                 markers[i] = "t"
#         i += 1
#     return "".join(markers)


# def html_too_big(s):
#     if isinstance(s, str):
#         s = s.encode("utf8")
#     return s.count(b"<") > const._MAX_TAGS_COUNT


# def html_document_fromstring(s):
#     """Parse html tree from string. Return None if the string can't be parsed."""
#     if isinstance(s, str):
#         s = s.encode("utf8")
#     try:
#         if html_too_big(s):
#             return None
#         return html5parser.document_fromstring(s, parser=utils._html5lib_parser())
#     except Exception:
#         pass


# def html_tree_to_text(tree):
#     return tree.text_content().strip()


# def _readable_text_empty(html_tree):
#     return not bool(html_tree_to_text(html_tree).strip())


# def _extract_from_html(msg_body):
#     """
#     Extract not quoted message from provided html message body
#     using tags and plain text algorithm.

#     Cut out the 'blockquote', 'gmail_quote' tags.
#     Cut Microsoft quotations.

#     Then use plain text algorithm to cut out splitter or
#     leftover quotation.
#     This works by adding checkpoint text to all html tags,
#     then converting html to text,
#     then extracting quotations from text,
#     then checking deleted checkpoints,
#     then deleting necessary tags.

#     function returns two values:
#         clean_html, quote_html = _extract_from_html(body)

#     Both values are Unicode strings; quote_html is an empty string when
#     no quotation is detected.
#     """

#     if isinstance(msg_body, bytes):
#         msg_body = msg_body.decode("utf-8", "replace")
#     else:  # already a str
#         try:
#             # Mojibake test: can we round-trip through Latin-1?
#             fixed = msg_body.encode("latin-1").decode("utf-8")
#         except (UnicodeEncodeError, UnicodeDecodeError):
#             # Either genuine UTF-8 (cannot encode to latin-1) or
#             # undecodable rubbish – keep the original
#             pass
#         else:
#             # latin-1 round-trip succeeded ⇒ original was mojibake
#             msg_body = fixed

#     # ------------------------------------------------------------------
#     # 2. Early exits for empty bodies
#     # ------------------------------------------------------------------
#     if msg_body.strip() == "":
#         return msg_body, ""  # both values are str

#     # ------------------------------------------------------------------
#     # 3. Prepare for DOM parsing
#     # ------------------------------------------------------------------
#     msg_body = msg_body.replace("\r\n", "\n")  # str → str
#     # html_tree = html_document_fromstring(msg_body)
#     html_tree = html.fromstring(msg_body)

#     if html_tree is None:  # malformed HTML
#         return msg_body, ""  # both str

#     cut_quotations = (
#         html_quotations.cut_gmail_quote(html_tree)
#         or html_quotations.cut_zimbra_quote(html_tree)
#         or html_quotations.cut_blockquote(html_tree)
#         or html_quotations.cut_microsoft_quote(html_tree)
#         or html_quotations.cut_by_id(html_tree)
#         or html_quotations.cut_from_block(html_tree)
#     )

#     # TWO working copies: one for the body, one for the quote
#     html_tree_body = deepcopy(html_tree)  # -> cleaned message
#     html_tree_quote = deepcopy(html_tree)  # -> quoted part only

#     number_of_checkpoints = html_quotations.add_checkpoint(html_tree, 0)
#     quotation_checkpoints = [False] * number_of_checkpoints
#     plain_text = html_tree_to_text(html_tree)
#     plain_text = utils.preprocess(plain_text, "\n", content_type="text/html")
#     lines = plain_text.splitlines()
#     # Don't process too long messages
#     if len(lines) > const.MAX_LINES_COUNT:
#        original = msg_body.decode("utf8") if isinstance(msg_body, bytes) else msg_body
#          return original, ""
#     # Collect checkpoints on each line
#     line_checkpoints = [
#         [
#             int(i[4:-4])  # Only checkpoint number
#             for i in re.findall(html_quotations.CHECKPOINT_PATTERN, line)
#         ]
#         for line in lines
#     ]
#     # Remove checkpoints
#     lines = [re.sub(html_quotations.CHECKPOINT_PATTERN, "", line) for line in lines]

#     # Use plain text quotation extracting algorithm
#     markers = mark_message_lines(lines)
#     return_flags = []
#     process_marked_lines(lines, markers, return_flags)
#     lines_were_deleted, first_deleted, last_deleted = return_flags

#     if not lines_were_deleted and not cut_quotations:  # nothing to cut
#        original = msg_body.decode("utf8") if isinstance(msg_body, bytes) else msg_body
#         return original, ""

#     # collect checkpoints that belong to quotation
#     if lines_were_deleted:
#         for i in range(first_deleted, last_deleted):
#             for checkpoint in line_checkpoints[i]:
#                 quotation_checkpoints[checkpoint] = True

#     # --- build the two trees ---------------------------------------------
#     # 1. message without quotation
#     html_quotations.delete_quotation_tags(html_tree_body, 0, quotation_checkpoints)

#     # 2. quotation only  – delete the *other* checkpoints
#     inverted = [not c for c in quotation_checkpoints]
#     html_quotations.delete_quotation_tags(html_tree_quote, 0, inverted)

#     # guard against corner cases where everything vanished
#     if _readable_text_empty(html_tree_body):
#        original = msg_body.decode("utf8") if isinstance(msg_body, bytes) else msg_body
#         return original, ""

#     clean_html = html.tostring(html_tree_body, encoding="unicode")
#     quote_html = (
#         ""
#         if _readable_text_empty(html_tree_quote)
#         else html.tostring(html_tree_quote, encoding="unicode")
#     )

#     return clean_html, quote_html


# def extract_from_html(msg_body):
#     """
#     Extract not quoted message  and quote from provided html message body
#     using tags and plain text algorithm.

#     function returns two values:
#         clean_html, quote_html = extract_from_html(body)

#     Both values are Unicode strings; quote_html is an empty string when
#     no quotation is detected.
#     """
#     clean_html, quote_html = _extract_from_html(msg_body)

#     if isinstance(clean_html, bytes):
#         clean_html = clean_html.decode("utf8")
#     if isinstance(quote_html, bytes):
#         quote_html = quote_html.decode("utf8")

#     return clean_html, quote_html


def strip_email_quote(msg_body) -> Tuple[str, str]:
    """
    Return ``(clean_html, quote_html)`` where *quote_html* contains every
    fragment that looks like an earlier-message quotation and *clean_html*
    is the remainder.

    The function is defensive against quirky, half-broken markup coming from
    real-world mailers (mixed encodings, stray <>, Word HTML, etc.).  It does
    **not** raise – if a node blows up on serialisation we fall back to its
    plain-text representation so your pipeline keeps moving.
    """

    if isinstance(msg_body, bytes):
        msg_body = msg_body.decode("utf-8", "replace")

    soup = BeautifulSoup(msg_body, "html.parser")  # forgiving parser
    extracted_parts: list[str] = []

    # -- 0 · Cut at first <hr> (if present) ---------------------------------
    _preprocess_outlook(soup)  # Outlook-specific normalisations
    _harvest_from_first_hr(soup, extracted_parts)

    # -- 1 · Strip classic “Original message …” comment blocks ---------------
    for c in soup.find_all(
        string=lambda t: isinstance(t, Comment)
        and re.search(r"(original message|forwarded message|reply below)", t, re.I)
    ):
        _safe_append(extracted_parts, f"<!--{c}-->")
        c.extract()

    # -- 2 · Identify every element that *might* be a quotation --------------
    quote_blocks: list[Tag] = []
    for candidate in soup.find_all(looks_like_quote):
        # keep only *outermost* quote blocks
        if not any(parent in quote_blocks for parent in candidate.parents):
            quote_blocks.append(candidate)

    # -- 3 · Lift the blocks out ---------------------------------------------
    for block in quote_blocks:
        _safe_append(extracted_parts, _outer_html(block))
        block.decompose()

    clean_html = soup.decode(formatter="minimal")  # lightweight serialiser
    quote_html = "".join(extracted_parts)

    return clean_html, quote_html


def looks_like_quote(tag: Tag) -> bool:  # now top-level
    if tag.name in {"blockquote", "hr"}:
        return True
    if (tag.get("id") or "").lower() in {
        "gmail_quote",
        "yahoo_quoted",
        "divrplyfwdmsg",
        "outlookquotedcontent",
        "olk_src_body_section",
    }:
        return True
    tcls = " ".join(tag.get("class", [])).lower()
    if any(
        k in tcls
        for k in (
            "gmail_quote",
            "yahoo_quoted",
            "js-email-quote",
            "outlookmessageheader",
        )
    ):
        return True
    style = (tag.get("style") or "").replace(" ", "").lower()
    return bool(re.search(r"border-left[^:]*:\s*\d+px", style))


def _preprocess_outlook(soup: BeautifulSoup) -> None:
    """
    Make old and new Outlook HTML easy for `_harvest_from_first_hr`:
      • lower-case every class/id,
      • if we see the grey divider (`border-top:`) *and* it contains
        header keywords → drop a real `<hr>` before it,
      • else: find the first paragraph that *looks* like the Outlook
        header (From/Sent/To/Subject in EN/PL/RU) and drop `<hr>` before
        that.
    """

    hr = soup.find("hr")
    if hr:
        return

    # 1 – lower-case class/id
    for tag in soup.find_all(True):
        if tag.has_attr("class"):
            tag["class"] = [cls.lower() for cls in tag["class"]]
        if tag.has_attr("id"):
            tag["id"] = tag["id"].lower()

    # ------------------------------------------------------------------
    #  localisation: header keywords we accept as “the quoted part starts
    #  here”.  Lower-case because we lowercase the text before matching.
    # ------------------------------------------------------------------
    HDR_WORDS = {
        # English
        "from:",
        "sent:",
        "to:",
        "cc:",
        "subject:",
        # Polish
        "od:",
        "wysłano:",
        "do:",
        "dw:",
        "temat:",
        # Russian
        "от:",
        "отправлено:",
        "кому:",
        "копия:",
        "тема:",
    }

    # ..................................................................
    #  2a · Try modern Outlook: <div style="border-top:…">
    # ..................................................................
    def is_divider(tag: Tag) -> bool:
        if tag.name not in {"div", "p"} or not tag.has_attr("style"):
            return False
        st = tag["style"].lower()
        if "border-top:" not in st:
            return False
        if not re.search(r"border-top:[^;]*\d+(?:px|pt|em)", st):
            return False
        return any(w in tag.get_text(" ", strip=True).lower() for w in HDR_WORDS)

    for divider in soup.find_all(is_divider):
        divider.insert_before(soup.new_tag("hr"))
        return

    # ..................................................................
    #  2b · Fallback for *old* Outlook – no grey line, but a header para
    # ..................................................................
    def is_header_para(tag: Tag) -> bool:
        if tag.name not in {"p", "div"}:
            return False
        text = tag.get_text(" ", strip=True).lower()
        # must start with a header keyword to avoid false positives
        return any(text.startswith(w) for w in HDR_WORDS)

    header = soup.find(is_header_para)
    if header is not None:
        header.insert_before(soup.new_tag("hr"))


def _harvest_from_first_hr(soup: BeautifulSoup, bucket: list[str]) -> None:
    """
    Move the first <hr> *and everything that follows it* into *bucket*,
    then delete those nodes from *soup*.
    """
    hr = soup.find("hr")
    if hr is None:
        return

    # include the <hr> itself and every successor in document order
    for node in [hr] + list(hr.next_elements):
        if isinstance(node, (Tag, NavigableString)):
            _safe_append(
                bucket, _outer_html(node) if isinstance(node, Tag) else str(node)
            )
            node.extract()


def _outer_html(tag: Tag) -> str:
    """
    Serialise a Tag to HTML as safely as possible.

    BeautifulSoup occasionally hits a corner-case where ``tag.name`` becomes
    *None* (malformed input or after certain tree mutations).  When that
    happens we fall back to its text representation so callers never see the
    ugly ``TypeError: can only concatenate str (not "NoneType") to str``.
    """
    try:
        return tag.decode(formatter="minimal")
    except Exception:  # pragma: no cover  – last-chance net
        return tag.get_text(strip=False)


def _safe_append(lst: list[str], fragment: str) -> None:
    """
    Append ``fragment`` to ``lst``, guaranteeing that every entry is text –
    prevents later ``TypeError`` when ``"".join(...)`` is called.
    """
    lst.append(fragment or "")
