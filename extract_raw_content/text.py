import re

from . import constants as const
from . import utils


def get_delimiter(msg_body):
    delimiter = const.RE_DELIMITER.search(msg_body)
    if delimiter:
        delimiter = delimiter.group()
    else:
        delimiter = "\n"
    return delimiter


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
    for inline_reply in re.finditer("(?<=m)e*(t[te]*)m", markers):
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


def postprocess(msg_body):
    """Make up for changes done at preprocessing message.

    Replace link brackets back to '<' and '>'.
    """
    return re.sub(const.RE_NORMALIZED_LINK, r"<\1>", msg_body).strip()


def extract_from_plain(msg_body):
    """Extracts a non quoted message from provided plain text."""
    delimiter = get_delimiter(msg_body)
    msg_body = utils.preprocess(msg_body, delimiter)
    # don't process too long messages
    lines = msg_body.splitlines()[: const.MAX_LINES_COUNT]
    markers = mark_message_lines(lines)
    lines = process_marked_lines(lines, markers)

    # concatenate lines, change links back, strip and return
    msg_body = delimiter.join(lines)
    msg_body = postprocess(msg_body)
    return msg_body
