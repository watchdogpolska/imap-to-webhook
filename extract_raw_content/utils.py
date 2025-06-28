import re

# from lxml import etree, html
from lxml import html

from . import constants as const

# from lxml.cssselect import CSSSelector

# from lxml.html import html5parser


# _UTF8_DECLARATION = (
#     '<meta http-equiv="Content-Type" content="text/html;' 'charset=utf-8">'
# )
# _BLOCKTAGS = ["div", "p", "ul", "li", "h1", "h2", "h3"]
# _HARDBREAKS = ["br", "hr", "tr"]


# def text_content(context):
#     """XPath Extension function to return a node text content."""
#     return context.context_node.xpath("string()").strip()


# def tail(context):
#     """XPath Extension function to return a node tail text."""
#     return context.context_node.tail or ""


# def register_xpath_extensions():
#     ns = etree.FunctionNamespace("http://mailgun.net")
#     ns.prefix = "mg"
#     ns["text_content"] = text_content
#     ns["tail"] = tail


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


# def _html5lib_parser():
#     """
#     html5lib is a pure-python library that conforms to the WHATWG HTML spec
#     and is not vulnarable to certain attacks common for XML libraries
#     """
#     return html5lib.HTMLParser(
#         # build lxml tree
#         html5lib.treebuilders.getTreeBuilder("lxml"),
#         # remove namespace value from inside lxml.html.html5paser element tag
#         # otherwise it yields something like "{http://www.w3.org/1999/xhtml}div"
#         # instead of "div", throwing the algo off
#         namespaceHTMLElements=False,
#     )


# def _contains_charset_spec(s: str) -> str:
#     """Return True if the first 4KB contain charset spec"""
#     return s.lower().find("html; charset=", 0, 4096) != -1


# def _rm_excessive_newlines(s: str) -> str:
#     """Remove excessive newlines that often happen due to tons of divs"""
#     return const._RE_EXCESSIVE_NEWLINES.sub("\n\n", s).strip()


# def _prepend_utf8_declaration(s: str) -> str:
#     """Prepend 'utf-8' encoding declaration if the first 4KB don't have any"""
#     return s if _contains_charset_spec(s) else _UTF8_DECLARATION + s


def html_fromstring(s: str) -> html.HtmlElement | None:
    """Parse html tree from string. Return None if the string can't be parsed."""
    try:
        return html.fromstring(s)
    except Exception:
        return None


# def html_tree_to_text(tree: etree._Element) -> str:
#     for style in CSSSelector("style")(tree):
#         style.getparent().remove(style)

#     for c in tree.xpath("//comment()"):
#         parent = c.getparent()

#         # comment with no parent does not impact produced text
#         if parent is None:
#             continue

#         parent.remove(c)

#     text = ""
#     for el in tree.iter():
#         el_text = (el.text or "") + (el.tail or "")
#         if len(el_text) > 1:
#             if el.tag in _BLOCKTAGS + _HARDBREAKS:
#                 text += "\n"
#             if el.tag == "li":
#                 text += "  * "
#             text += el_text.strip() + " "

#             # add href to the output
#             href = el.attrib.get("href")
#             if href:
#                 text += "(%s) " % href

#         if el.tag in _HARDBREAKS and text and not text.endswith("\n") and not el_text:
#             text += "\n"

#     text = _rm_excessive_newlines(text)
#     return text


# def html_to_text(s: str) -> str | None:
#     """
#     Dead-simple HTML-to-text converter:
#         >>> html_to_text("one<br>two<br>three")
#         <<< "one\ntwo\nthree"

#     NOTES:
#         1. the string is expected to contain UTF-8 encoded HTML!
#         3. if html can't be parsed returns None
#     """
#     s = _prepend_utf8_declaration(s)
#     s = s.replace("\n", "")
#     tree = html_fromstring(s)

#     if tree is None:
#         return None

#     return html_tree_to_text(tree)
