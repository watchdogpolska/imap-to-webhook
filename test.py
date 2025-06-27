import json
import os
import re
import unittest
from unittest.mock import Mock, patch

from extract_raw_content import constants, html, text, utils

# ---------------------------------------------------------------------
# Compatibility layer for the new (clean_html, quote_html) API introduced in
# fix_quotes_and_encoding.  The existing tests expect the *clean* body
# only, so we wrap the function to return element 0 of the tuple.
# ---------------------------------------------------------------------
_orig_extract = html.extract_from_html


def _extract_clean(body):
    """Return only the cleaned HTML body (discard quotation)."""
    return _orig_extract(body)[0]


html.extract_from_html = _extract_clean
# ---------------------------------------------------------------------

from mail_parser import serialize_mail

STANDARD_REPLIES = "mails/standard_replies"
RE_WHITESPACE = re.compile(r"\s")
RE_DOUBLE_WHITESPACE = re.compile(r"\s")


def get_email_as_bytes(name):
    with open(
        os.path.join(
            os.path.dirname(__file__),
            "mails",
            name,
        ),
        "rb",
    ) as f:
        return f.read()


class TestMain(unittest.TestCase):
    def test_disposition_notification(self):
        mail = get_email_as_bytes("disposition-notification.eml")
        body = serialize_mail(mail)
        body_map = {k: v for k, v in body}
        manifest = json.loads(body_map["manifest"][1].read().decode("utf-8"))
        self.assertTrue(
            manifest["headers"]["auto_reply_type"], "disposition-notification"
        )

    def test_vacation_reply(self):
        mail = get_email_as_bytes("vacation-reply.eml")
        body = serialize_mail(mail)
        body_map = {k: v for k, v in body}
        manifest = json.loads(body_map["manifest"][1].read().decode("utf-8"))
        self.assertTrue(manifest["headers"]["auto_reply_type"], "vacation-reply")

    def test_html_only(self):
        mail = get_email_as_bytes("html_only.eml")
        body = serialize_mail(mail)
        body_map = {k: v for k, v in body}
        manifest = json.loads(body_map["manifest"][1].read().decode("utf-8"))
        self.assertTrue(manifest["text"]["content"])
        self.assertTrue(manifest["text"]["html_content"])

    def test_get_delimiter(self):
        self.assertEqual("\r\n", text.get_delimiter("abc\r\n123"))
        self.assertEqual("\n", text.get_delimiter("abc\n123"))
        self.assertEqual("\n", text.get_delimiter("abc"))

    def test_html_to_text(self):
        html = """<body>
<p>Hello world!</p>
<br>
<ul>
<li>One!</li>
<li>Two</li>
</ul>
<p>
Haha
</p>
</body>"""
        text = utils.html_to_text(html)
        self.assertEqual("Hello world! \n\n  * One! \n  * Two \nHaha", text)
        self.assertEqual("привет!", utils.html_to_text("<b>привет!</b>"))

        html = "<body><br/><br/>Hi</body>"
        self.assertEqual("Hi", utils.html_to_text(html))

        html = """Hi
<style type="text/css">

div, p, li {

font: 13px 'Lucida Grande', Arial, sans-serif;

}
</style>

<style type="text/css">

h1 {

font: 13px 'Lucida Grande', Arial, sans-serif;

}
</style>"""
        self.assertEqual("Hi", utils.html_to_text(html))

        html = """<div>
<!-- COMMENT 1 -->
<span>TEXT 1</span>
<p>TEXT 2 <!-- COMMENT 2 --></p>
</div>"""
        self.assertEqual("TEXT 1 \nTEXT 2", utils.html_to_text(html))

    def test_comment_no_parent(self):
        s = "<!-- COMMENT 1 --> no comment"
        d = html.html_document_fromstring(s)
        self.assertEqual("no comment", utils.html_tree_to_text(d))

    @patch.object(utils, "html_fromstring", Mock(return_value=None))
    def test_bad_html_to_text(self):
        bad_html = "one<br>two<br>three"
        self.assertEqual(None, utils.html_to_text(bad_html))

    def test_quotation_splitter_inside_blockquote(self):
        msg_body = """Reply
<blockquote>

<div>
    On 11-Apr-2011, at 6:54 PM, Bob &lt;bob@example.com&gt; wrote:
</div>

<div>
    Test
</div>

</blockquote>"""

        self.assertEqual(
            "<html><head></head><body>Reply</body></html>",
            RE_WHITESPACE.sub("", html.extract_from_html(msg_body)),
        )

    def test_quotation_splitter_outside_blockquote(self):
        msg_body = """Reply

<div>
On 11-Apr-2011, at 6:54 PM, Bob &lt;bob@example.com&gt; wrote:
</div>

<blockquote>
<div>
    Test
</div>
</blockquote>
"""
        self.assertEqual(
            "<html><head></head><body>Reply</body></html>",
            RE_WHITESPACE.sub("", html.extract_from_html(msg_body)),
        )

    def test_regular_blockquote(self):
        msg_body = """Reply
<blockquote>Regular</blockquote>

<div>
On 11-Apr-2011, at 6:54 PM, Bob &lt;bob@example.com&gt; wrote:
</div>

<blockquote>
<div>
    <blockquote>Nested</blockquote>
</div>
</blockquote>
"""
        self.assertEqual(
            "<html><head></head><body>Reply"
            + "<blockquote>Regular</blockquote></body></html>",
            RE_WHITESPACE.sub("", html.extract_from_html(msg_body)),
        )

    def test_no_blockquote(self):
        msg_body = """
<html>
<body>
Reply

<div>
On 11-Apr-2011, at 6:54 PM, Bob &lt;bob@example.com&gt; wrote:
</div>

<div>
Test
</div>
</body>
</html>
"""

        reply = """
<html>
<head></head>
<body>
Reply

</body></html>"""
        self.assertEqual(
            RE_WHITESPACE.sub("", reply),
            RE_WHITESPACE.sub("", html.extract_from_html(msg_body)),
        )

    def test_empty_body(self):
        self.assertEqual("", html.extract_from_html(""))

    def test_validate_output_html(self):
        msg_body = """Reply
<div>
On 11-Apr-2011, at 6:54 PM, Bob &lt;bob@example.com&gt; wrote:

    <blockquote>
    <div>
        Test
    </div>
    </blockquote>
</div>

<div/>
"""
        out = html.extract_from_html(msg_body)
        self.assertTrue(
            "<html>" in out and "</html>" in out,
            "Invalid HTML - <html>/</html> tag not present",
        )
        self.assertTrue(
            "<div/>" not in out, "Invalid HTML output - <div/> element is not valid"
        )

    def test_gmail_quote(self):
        msg_body = """Reply
<div class="gmail_quote">
<div class="gmail_quote">
    On 11-Apr-2011, at 6:54 PM, Bob &lt;bob@example.com&gt; wrote:
    <div>
    Test
    </div>
</div>
</div>"""
        self.assertEqual(
            "<html><head></head><body>Reply</body></html>",
            RE_WHITESPACE.sub("", html.extract_from_html(msg_body)),
        )

    def test_gmail_quote_compact(self):
        msg_body = (
            "Reply"
            '<div class="gmail_quote">'
            '<div class="gmail_quote">'
            + "On 11-Apr-2011, at 6:54 PM, Bob &lt;bob@example.com&gt; wrote:"
            "<div>Test</div>"
            "</div>"
            "</div>"
        )
        self.assertEqual(
            "<html><head></head><body>Reply</body></html>",
            RE_WHITESPACE.sub("", html.extract_from_html(msg_body)),
        )

    def test_gmail_quote_blockquote(self):
        msg_body = """Message
<blockquote class="gmail_quote">
<div class="gmail_default">
    My name is William Shakespeare.
    <br/>
</div>
</blockquote>"""
        self.assertEqual(
            RE_WHITESPACE.sub("", msg_body),
            RE_WHITESPACE.sub("", html.extract_from_html(msg_body)),
        )

    def test_blockquote_disclaimer(self):
        msg_body = """
<html>
<body>
<div>
    <div>
    message
    </div>
    <blockquote>
    Quote
    </blockquote>
</div>
<div>
    disclaimer
</div>
</body>
</html>
"""

        stripped_html = """
<html>
<head></head>
<body>
<div>
    <div>
    message
    </div>
</div>
<div>
    disclaimer
</div>
</body>
</html>
"""
        self.assertEqual(
            RE_WHITESPACE.sub("", stripped_html),
            RE_WHITESPACE.sub("", html.extract_from_html(msg_body)),
        )

    def test_date_block(self):
        msg_body = """
<div>
message<br>
<div>
    <hr>
    Date: Fri, 23 Mar 2012 12:35:31 -0600<br>
    To: <a href="mailto:bob@example.com">bob@example.com</a><br>
    From: <a href="mailto:rob@example.com">rob@example.com</a><br>
    Subject: You Have New Mail From Mary!<br><br>

    text
</div>
</div>
"""
        self.assertEqual(
            "<html><head></head><body><div>message<br></div></body></html>",
            RE_WHITESPACE.sub("", html.extract_from_html(msg_body)),
        )

    def test_from_block(self):
        msg_body = """<div>
message<br>
<div>
<hr>
From: <a href="mailto:bob@example.com">bob@example.com</a><br>
Date: Fri, 23 Mar 2012 12:35:31 -0600<br>
To: <a href="mailto:rob@example.com">rob@example.com</a><br>
Subject: You Have New Mail From Mary!<br><br>

text
</div></div>
"""
        self.assertEqual(
            "<html><head></head><body><div>message<br></div></body></html>",
            RE_WHITESPACE.sub("", html.extract_from_html(msg_body)),
        )

    def test_reply_shares_div_with_from_block(self):
        msg_body = """
<body>
<div>

    Blah<br><br>

    <hr>Date: Tue, 22 May 2012 18:29:16 -0600<br>
    To: xx@hotmail.ca<br>
    From: quickemail@ashleymadison.com<br>
    Subject: You Have New Mail From x!<br><br>

</div>
</body>"""
        self.assertEqual(
            "<html><head></head><body><div>Blah<br><br></div></body></html>",
            RE_WHITESPACE.sub("", html.extract_from_html(msg_body)),
        )

    def test_reply_quotations_share_block(self):
        stripped_html = text.extract_from_plain(
            get_email_as_bytes("reply-quotations-share-block.eml").decode("utf-8")
        )
        self.assertTrue(stripped_html)
        self.assertTrue("From" not in stripped_html)

    def test_OLK_SRC_BODY_SECTION_stripped(self):
        self.assertEqual(
            "<html><head></head><body><div>Reply</div></body></html>",
            RE_WHITESPACE.sub(
                "",
                html.extract_from_html(get_email_as_bytes("OLK_SRC_BODY_SECTION.html")),
            ),
        )

    def test_reply_separated_by_hr(self):
        self.assertEqual(
            "<html><head></head><body><div>Hi<div>there</div></div></body></html>",
            RE_WHITESPACE.sub(
                "",
                html.extract_from_html(
                    get_email_as_bytes("reply-separated-by-hr.html")
                ),
            ),
        )

    def test_from_block_and_quotations_in_separate_divs(self):
        msg_body = """
Reply
<div>
<hr/>
<div>
    <font>
    <b>From: bob@example.com</b>
    <b>Date: Thu, 24 Mar 2016 08:07:12 -0700</b>
    </font>
</div>
<div>
    Quoted message
</div>
</div>
"""
        self.assertEqual(
            "<html><head></head><body>Reply<div><hr></div></body></html>",
            RE_WHITESPACE.sub("", html.extract_from_html(msg_body)),
        )

    def extract_reply_and_check(self, filename):
        kwargs = {}
        kwargs["encoding"] = "utf8"

        with open(filename, **kwargs) as f:
            msg_body = f.read()
            reply = html.extract_from_html(msg_body)
            plain_reply = utils.html_to_text(reply)

            self.assertEqual(
                RE_WHITESPACE.sub("", "Hi. I am fine.\n\nThanks,\nAlex"),
                RE_WHITESPACE.sub("", plain_reply),
            )

    def test_CRLF(self):
        """CR is not converted to '&#13;'"""
        symbol = "&#13;"
        extracted = html.extract_from_html("<html>\r\n</html>")
        self.assertFalse(symbol in extracted)
        self.assertEqual("<html></html>", RE_WHITESPACE.sub("", extracted))

        msg_body = """My
reply
<blockquote>

<div>
    On 11-Apr-2011, at 6:54 PM, Bob &lt;bob@example.com&gt; wrote:
</div>

<div>
    Test
</div>

</blockquote>"""
        msg_body = msg_body.replace("\n", "\r\n")
        extracted = html.extract_from_html(msg_body)
        self.assertFalse(symbol in extracted)
        # Keep new lines otherwise "My reply" becomes one word - "Myreply"
        self.assertEqual(
            "<html><head></head><body>My\nreply\n</body></html>", extracted
        )

    def test_gmail_forwarded_msg(self):
        msg_body = (
            '<div dir="ltr"><br>'
            + '<div class="gmail_quote">---------- Forwarded message ----------<br>'
            + 'From: <b class="gmail_sendername">Bob</b> <span dir="ltr">'
            + '&lt;<a href="mailto:bob@example.com">bob@example.com</a>&gt;'
            + "</span><br>Date: Fri, Feb 11, 2010 at 5:59 PM<br>"
            + "Subject: Bob WFH today<br>To: Mary &lt;"
            + '<a href="mailto:mary@example.com">'
            + 'mary@example.com</a>&gt;<br><br><br><div dir="ltr">eom</div>'
            + "</div><br></div>"
        )
        extracted = html.extract_from_html(msg_body)
        self.assertEqual(
            RE_WHITESPACE.sub("", msg_body), RE_WHITESPACE.sub("", extracted)
        )

    def test_readable_html_empty(self):
        msg_body = """
<blockquote>
Reply
<div>
    On 11-Apr-2011, at 6:54 PM, Bob &lt;bob@example.com&gt; wrote:
</div>

<div>
    Test
</div>

</blockquote>"""

        self.assertEqual(
            RE_WHITESPACE.sub("", msg_body),
            RE_WHITESPACE.sub("", html.extract_from_html(msg_body)),
        )

    @patch.object(html, "html_document_fromstring", Mock(return_value=None))
    def test_bad_html(self):
        bad_html = "<html></html>"
        self.assertEqual(bad_html, html.extract_from_html(bad_html))

    def test_gmail_reply(self):
        self.extract_reply_and_check("mails/html_replies/gmail.html")

    def test_mail_ru_reply(self):
        self.extract_reply_and_check("mails/html_replies/mail_ru.html")

    def test_hotmail_reply(self):
        self.extract_reply_and_check("mails/html_replies/hotmail.html")

    def test_ms_outlook_2003_reply(self):
        self.extract_reply_and_check("mails/html_replies/ms_outlook_2003.html")

    def test_ms_outlook_2007_reply(self):
        self.extract_reply_and_check("mails/html_replies/ms_outlook_2007.html")

    def test_ms_outlook_2010_reply(self):
        self.extract_reply_and_check("mails/html_replies/ms_outlook_2010.html")

    def test_thunderbird_reply(self):
        self.extract_reply_and_check("mails/html_replies/thunderbird.html")

    def test_windows_mail_reply(self):
        self.extract_reply_and_check("mails/html_replies/windows_mail.html")

    def test_yandex_ru_reply(self):
        self.extract_reply_and_check("mails/html_replies/yandex_ru.html")

    @patch.object(constants, "MAX_LINES_COUNT", 1)
    def test_too_many_lines(self):
        msg_body = """Test reply
Hi
-----Original Message-----

Test"""
        self.assertEqual("Test reply", text.extract_from_plain(msg_body))

    def test_pattern_on_date_somebody_wrote(self):
        msg_body = """Test reply

On 11-Apr-2011, at 6:54 PM, Roman Tkachenko <romant@example.com> wrote:

>
> Test
>
> Roman"""

        self.assertEqual("Test reply", text.extract_from_plain(msg_body))

    def test_pattern_on_date_polymail(self):
        msg_body = """Test reply

On Tue, Apr 11, 2017 at 10:07 PM John Smith

<
mailto:John Smith <johnsmith@gmail.com>
> wrote:
Test quoted data
"""

        self.assertEqual("Test reply", text.extract_from_plain(msg_body))

    def test_pattern_sent_from_samsung_smb_wrote(self):
        msg_body = """Test reply

Sent from Samsung MobileName <address@example.com> wrote:

>
> Test
>
> Roman"""

        self.assertEqual("Test reply", text.extract_from_plain(msg_body))

    def test_pattern_on_date_wrote_somebody(self):
        self.assertEqual(
            "Lorem",
            text.extract_from_plain(
                """Lorem

Op 13-02-2014 3:18 schreef Julius Caesar <pantheon@rome.com>:

Veniam laborum mlkshk kale chips authentic.
Normcore mumblecore laboris, fanny pack readymade eu blog chia pop-up
freegan enim master cleanse.
"""
            ),
        )

    def test_pattern_on_date_somebody_wrote_date_with_slashes(self):
        msg_body = """Test reply

On 04/19/2011 07:10 AM, Roman Tkachenko wrote:

>
> Test.
>
> Roman"""
        self.assertEqual("Test reply", text.extract_from_plain(msg_body))

    def test_date_time_email_splitter(self):
        msg_body = """Test reply

2014-10-17 11:28 GMT+03:00 Postmaster <
postmaster@sandboxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx.mailgun.org>:

> First from site
>
    """
        self.assertEqual("Test reply", text.extract_from_plain(msg_body))

    def test_pattern_on_date_somebody_wrote_allows_space_in_front(self):
        msg_body = """Thanks Thanmai
On Mar 8, 2012 9:59 AM, "Example.com" <
r+7f1b094ceb90e18cca93d53d3703feae@example.com> wrote:


>**
>  Blah-blah-blah"""
        self.assertEqual("Thanks Thanmai", text.extract_from_plain(msg_body))

    def test_pattern_on_date_somebody_sent(self):
        msg_body = """Test reply

On 11-Apr-2011, at 6:54 PM, Roman Tkachenko <romant@example.com> sent:

>
> Test
>
> Roman"""
        self.assertEqual("Test reply", text.extract_from_plain(msg_body))

    def test_appointment(self):
        msg_body = """Response

    10/19/2017 @ 9:30 am for physical therapy
    Bla
    1517 4th Avenue Ste 300
    London CA 19129, 555-421-6780

    John Doe, FCLS
    Mailgun Inc
    555-941-0697

    From: from@example.com [mailto:from@example.com]
    Sent: Wednesday, October 18, 2017 2:05 PM
    To: John Doer - SIU <jd@example.com>
    Subject: RE: Claim # 5551188-1

    Text"""

        expected = """Response

    10/19/2017 @ 9:30 am for physical therapy
    Bla
    1517 4th Avenue Ste 300
    London CA 19129, 555-421-6780

    John Doe, FCLS
    Mailgun Inc
    555-941-0697"""
        self.assertEqual(expected, text.extract_from_plain(msg_body))

    def test_line_starts_with_on(self):
        msg_body = """Blah-blah-blah
On blah-blah-blah"""
        self.assertEqual(msg_body, text.extract_from_plain(msg_body))

    def test_reply_and_quotation_splitter_share_line(self):
        # reply lines and 'On <date> <person> wrote:' splitter pattern
        # are on the same line
        msg_body = """reply On Wed, Apr 4, 2012 at 3:59 PM, bob@example.com wrote:
> Hi"""
        self.assertEqual("reply", text.extract_from_plain(msg_body))

        # test pattern '--- On <date> <person> wrote:' with reply text on
        # the same line
        msg_body = """reply--- On Wed, Apr 4, 2012 at 3:59 PM, me@domain.com wrote:
> Hi"""
        self.assertEqual("reply", text.extract_from_plain(msg_body))

        # test pattern '--- On <date> <person> wrote:' with reply text containing
        # '-' symbol
        msg_body = """reply
bla-bla - bla--- On Wed, Apr 4, 2012 at 3:59 PM, me@domain.com wrote:
> Hi"""
        reply = """reply
bla-bla - bla"""

        self.assertEqual(reply, text.extract_from_plain(msg_body))

    def test_android_wrote(self):
        msg_body = """Test reply

---- John Smith wrote ----

> quoted
> text
"""
        self.assertEqual("Test reply", text.extract_from_plain(msg_body))

    def test_reply_wraps_quotations(self):
        msg_body = """Test reply

On 04/19/2011 07:10 AM, Roman Tkachenko wrote:

>
> Test

Regards, Roman"""

        reply = """Test reply

Regards, Roman"""

        self.assertEqual(reply, text.extract_from_plain(msg_body))

    def test_reply_wraps_nested_quotations(self):
        msg_body = """Test reply
On 04/19/2011 07:10 AM, Roman Tkachenko wrote:

>Test test
>On 04/19/2011 07:10 AM, Roman Tkachenko wrote:
>
>>
>> Test.
>>
>> Roman

Regards, Roman"""

        reply = """Test reply
Regards, Roman"""
        self.assertEqual(reply, text.extract_from_plain(msg_body))

    def test_quotation_separator_takes_2_lines(self):
        msg_body = """Test reply

On Fri, May 6, 2011 at 6:03 PM, Roman Tkachenko from Hacker News
<roman@definebox.com> wrote:

> Test.
>
> Roman

Regards, Roman"""

        reply = """Test reply

Regards, Roman"""
        self.assertEqual(reply, text.extract_from_plain(msg_body))

    def test_quotation_separator_takes_3_lines(self):
        msg_body = """Test reply

On Nov 30, 2011, at 12:47 PM, Somebody <
416ffd3258d4d2fa4c85cfa4c44e1721d66e3e8f4@somebody.domain.com>
wrote:

Test message
"""
        self.assertEqual("Test reply", text.extract_from_plain(msg_body))

    def test_short_quotation(self):
        msg_body = """Hi

On 04/19/2011 07:10 AM, Roman Tkachenko wrote:

> Hello"""
        self.assertEqual("Hi", text.extract_from_plain(msg_body))

    def test_with_indent(self):
        msg_body = """
YOLO salvia cillum kogi typewriter mumblecore cardigan skateboard Austin.

------On 12/29/1987 17:32 PM, Julius Caesar wrote-----

Brunch mumblecore pug Marfa tofu, irure taxidermy hoodie readymade pariatur.
    """
        self.assertEqual(
            "YOLO salvia cillum kogi typewriter mumblecore cardigan skateboard Austin.",
            text.extract_from_plain(msg_body),
        )

    def test_short_quotation_with_newline(self):
        msg_body = """Btw blah blah...

On Tue, Jan 27, 2015 at 12:42 PM -0800, "Company" <christine.XXX@XXX.com> wrote:

Hi Mark,
Blah blah? 
Thanks,Christine 

On Jan 27, 2015, at 11:55 AM, Mark XXX <mark@XXX.com> wrote:

Lorem ipsum?
Mark

Sent from Acompli"""
        self.assertEqual("Btw blah blah...", text.extract_from_plain(msg_body))

    def test_pattern_date_email_with_unicode(self):
        msg_body = """Replying ok
2011/4/7 Nathan \xd0\xb8ova <support@example.com>

>  Cool beans, scro"""
        self.assertEqual("Replying ok", text.extract_from_plain(msg_body))

    def test_english_from_block(self):
        self.assertEqual(
            "Allo! Follow up MIME!",
            text.extract_from_plain(
                """Allo! Follow up MIME!

From: somebody@example.com
Sent: March-19-11 5:42 PM
To: Somebody
Subject: The manager has commented on your Loop

Blah-blah-blah
"""
            ),
        )

    def test_german_from_block(self):
        self.assertEqual(
            "Allo! Follow up MIME!",
            text.extract_from_plain(
                """Allo! Follow up MIME!

Von: somebody@example.com
Gesendet: Dienstag, 25. November 2014 14:59
An: Somebody
Betreff: The manager has commented on your Loop

Blah-blah-blah
"""
            ),
        )

    def test_french_multiline_from_block(self):
        self.assertEqual(
            "Lorem ipsum",
            text.extract_from_plain(
                """Lorem ipsum

De : Brendan xxx [mailto:brendan.xxx@xxx.com]
Envoyé : vendredi 23 janvier 2015 16:39
À : Camille XXX
Objet : Follow Up

Blah-blah-blah
"""
            ),
        )

    def test_french_from_block(self):
        self.assertEqual(
            "Lorem ipsum",
            text.extract_from_plain(
                """Lorem ipsum

    Le 23 janv. 2015 à 22:03, Brendan xxx
    <brendan.xxx@xxx.com<mailto:brendan.xxx@xxx.com>> a écrit:

    Bonjour!"""
            ),
        )

    def test_polish_from_block(self):
        self.assertEqual(
            "Lorem ipsum",
            text.extract_from_plain(
                """Lorem ipsum

W dniu 28 stycznia 2015 01:53 użytkownik Zoe xxx <zoe.xxx@xxx.com>
napisał:

Blah!
"""
            ),
        )

    def test_danish_from_block(self):
        self.assertEqual(
            "Allo! Follow up MIME!",
            text.extract_from_plain(
                """Allo! Follow up MIME!

Fra: somebody@example.com
Sendt: 19. march 2011 12:10
Til: Somebody
Emne: The manager has commented on your Loop

Blah-blah-blah
"""
            ),
        )

    def test_swedish_from_block(self):
        self.assertEqual(
            "Allo! Follow up MIME!",
            text.extract_from_plain(
                """Allo! Follow up MIME!
Från: Anno Sportel [mailto:anno.spoel@hsbcssad.com]
Skickat: den 26 augusti 2015 14:45
Till: Isacson Leiff
Ämne: RE: Week 36

Blah-blah-blah
"""
            ),
        )

    def test_swedish_from_line(self):
        self.assertEqual(
            "Lorem",
            text.extract_from_plain(
                """Lorem
Den 14 september, 2015 02:23:18, Valentino Rudy (valentino@rudy.be) skrev:

Veniam laborum mlkshk kale chips authentic.
Normcore mumblecore laboris, fanny pack
readymade eu blog chia pop-up freegan enim master cleanse.
"""
            ),
        )

    def test_norwegian_from_line(self):
        self.assertEqual(
            "Lorem",
            text.extract_from_plain(
                """Lorem
På 14 september 2015 på 02:23:18, Valentino Rudy (valentino@rudy.be) skrev:

Veniam laborum mlkshk kale chips authentic.
Normcore mumblecore laboris, fanny pack
readymade eu blog chia pop-up freegan enim master cleanse.
"""
            ),
        )

    def test_dutch_from_block(self):
        self.assertEqual(
            "Gluten-free culpa lo-fi et nesciunt nostrud.",
            text.extract_from_plain(
                """Gluten-free culpa lo-fi et nesciunt nostrud.

Op 17-feb.-2015, om 13:18 heeft Julius Caesar
<pantheon@rome.com> het volgende geschreven:

Small batch beard laboris tempor, non listicle hella Tumblr heirloom.
"""
            ),
        )

    def test_vietnamese_from_block(self):
        self.assertEqual(
            "Hello",
            text.extract_from_plain(
                """Hello

Vào 14:24 8 tháng 6, 2017, Hùng Nguyễn <hungnguyen@xxx.com> đã viết:

> Xin chào
"""
            ),
        )

    def test_quotation_marker_false_positive(self):
        msg_body = """Visit us now for assistance...
>>> >>>  http://www.domain.com <<<
Visit our site by clicking the link above"""
        self.assertEqual(msg_body, text.extract_from_plain(msg_body))

    def test_link_closed_with_quotation_marker_on_new_line(self):
        msg_body = """8.45am-1pm

From: somebody@example.com
Date: Wed, 16 May 2012 00:15:02 -0600

<http://email.example.com/c/dHJhY2tpbmdfY29kZT1mMDdjYzBmNzM1ZjYzMGIxNT
>  <bob@example.com <mailto:bob@example.com> >

Requester: """
        self.assertEqual("8.45am-1pm", text.extract_from_plain(msg_body))

    def test_link_breaks_quotation_markers_sequence(self):
        # link starts and ends on the same line
        msg_body = """Blah

On Thursday, October 25, 2012 at 3:03 PM, life is short. on Bob wrote:

>
> Post a response by replying to this email
>
(http://example.com/c/YzOTYzMmE) >
> life is short. (http://example.com/c/YzMmE)
>
"""
        self.assertEqual("Blah", text.extract_from_plain(msg_body))

        # link starts after some text on one line and ends on another
        msg_body = """Blah

On Monday, 24 September, 2012 at 3:46 PM, bob wrote:

> [Ticket #50] test from bob
>
> View ticket (http://example.com/action
_nonce=3dd518)
>
"""
        self.assertEqual("Blah", text.extract_from_plain(msg_body))

    def test_from_block_starts_with_date(self):
        msg_body = """Blah

Date: Wed, 16 May 2012 00:15:02 -0600
To: klizhentas@example.com

"""
        self.assertEqual("Blah", text.extract_from_plain(msg_body))

    def test_bold_from_block(self):
        msg_body = """Hi

*From:* bob@example.com [mailto:
bob@example.com]
*Sent:* Wednesday, June 27, 2012 3:05 PM
*To:* travis@example.com
*Subject:* Hello

"""
        self.assertEqual("Hi", text.extract_from_plain(msg_body))

    def test_weird_date_format_in_date_block(self):
        msg_body = """Blah
Date: Fri=2C 28 Sep 2012 10:55:48 +0000
From: tickets@example.com
To: bob@example.com
Subject: [Ticket #8] Test

"""
        self.assertEqual("Blah", text.extract_from_plain(msg_body))

    def test_dont_parse_quotations_for_forwarded_messages(self):
        msg_body = """FYI

---------- Forwarded message ----------
From: bob@example.com
Date: Tue, Sep 4, 2012 at 1:35 PM
Subject: Two
line subject
To: rob@example.com

Text"""
        self.assertEqual(msg_body, text.extract_from_plain(msg_body))

    def test_forwarded_message_in_quotations(self):
        msg_body = """Blah

-----Original Message-----

FYI

---------- Forwarded message ----------
From: bob@example.com
Date: Tue, Sep 4, 2012 at 1:35 PM
Subject: Two
line subject
To: rob@example.com

"""
        self.assertEqual("Blah", text.extract_from_plain(msg_body))

    def test_mark_message_lines(self):
        # e - empty line
        # s - splitter line
        # m - line starting with quotation marker '>'
        # t - the rest

        lines = [
            "Hello",
            "",
            # next line should be marked as splitter
            "_____________",
            "From: foo@bar.com",
            "Date: Wed, 16 May 2012 00:15:02 -0600",
            "",
            "> Hi",
            "",
            "Signature",
        ]
        self.assertEqual("tesssemet", text.mark_message_lines(lines))

        lines = [
            "Just testing the email reply",
            "",
            "Robert J Samson",
            "Sent from my iPhone",
            "",
            # all 3 next lines should be marked as splitters
            "On Nov 30, 2011, at 12:47 PM, Skapture <",
            (
                "416ffd3258d4d2fa4c85cfa4c44e1721d66e3e8f4"
                "@skapture-staging.mailgun.org>"
            ),
            "wrote:",
            "",
            "Tarmo Lehtpuu has posted the following message on",
        ]
        self.assertEqual("tettessset", text.mark_message_lines(lines))

    def test_process_marked_lines(self):
        # quotations and last message lines are mixed
        # consider all to be a last message
        markers = "tsemmtetm"
        lines = [str(i) for i in range(len(markers))]
        lines = [str(i) for i in range(len(markers))]

        self.assertEqual(lines, text.process_marked_lines(lines, markers))

        # no splitter => no markers
        markers = "tmm"
        lines = ["1", "2", "3"]
        self.assertEqual(["1", "2", "3"], text.process_marked_lines(lines, markers))

        # text after splitter without markers is quotation
        markers = "tst"
        lines = ["1", "2", "3"]
        self.assertEqual(["1"], text.process_marked_lines(lines, markers))

        # message + quotation + signature
        markers = "tsmt"
        lines = ["1", "2", "3", "4"]
        self.assertEqual(["1", "4"], text.process_marked_lines(lines, markers))

        # message + <quotation without markers> + nested quotation
        markers = "tstsmt"
        lines = ["1", "2", "3", "4", "5", "6"]
        self.assertEqual(["1"], text.process_marked_lines(lines, markers))

        # test links wrapped with paranthesis
        # link starts on the marker line
        markers = "tsmttem"
        lines = [
            "text",
            "splitter",
            ">View (http://example.com",
            "/abc",
            ")",
            "",
            "> quote",
        ]
        self.assertEqual(lines[:1], text.process_marked_lines(lines, markers))

        # link starts on the new line
        markers = "tmmmtm"
        lines = [
            "text",
            ">" ">",
            ">",
            "(http://example.com) >  ",
            "> life is short. (http://example.com)  ",
        ]
        self.assertEqual(lines[:1], text.process_marked_lines(lines, markers))

        # check all "inline" replies
        markers = "tsmtmtm"
        lines = [
            "text",
            "splitter",
            ">",
            "(http://example.com)",
            ">",
            "inline  reply",
            ">",
        ]
        self.assertEqual(lines, text.process_marked_lines(lines, markers))

        # inline reply with link not wrapped in paranthesis
        markers = "tsmtm"
        lines = [
            "text",
            "splitter",
            ">",
            "inline reply with link http://example.com",
            ">",
        ]
        self.assertEqual(lines, text.process_marked_lines(lines, markers))

        # inline reply with link wrapped in paranthesis
        markers = "tsmtm"
        lines = ["text", "splitter", ">", "inline  reply (http://example.com)", ">"]
        self.assertEqual(lines, text.process_marked_lines(lines, markers))

    def test_preprocess(self):
        msg = (
            "Hello\n"
            "See <http://google.com\n"
            "> for more\n"
            "information On Nov 30, 2011, at 12:47 PM, Somebody <\n"
            "416ffd3258d4d2fa4c85cfa4c44e1721d66e3e8f4\n"
            "@example.com>"
            "wrote:\n"
            "\n"
            "> Hi"
        )

        # test the link is rewritten
        # 'On <date> <person> wrote:' pattern starts from a new line
        prepared_msg = (
            "Hello\n"
            "See @@http://google.com\n"
            "@@ for more\n"
            "information\n"
            " On Nov 30, 2011, at 12:47 PM, Somebody <\n"
            "416ffd3258d4d2fa4c85cfa4c44e1721d66e3e8f4\n"
            "@example.com>"
            "wrote:\n"
            "\n"
            "> Hi"
        )
        self.assertEqual(prepared_msg, utils.preprocess(msg, "\n"))

        msg = """
> <http://teemcl.mailgun.org/u/**aD1mZmZiNGU5ODQwMDNkZWZlMTExNm**

> MxNjQ4Y2RmOTNlMCZyPXNlcmdleS5v**YnlraG92JTQwbWFpbGd1bmhxLmNvbS**

> Z0PSUyQSZkPWUwY2U<http://example.org/u/aD1mZmZiNGU5ODQwMDNkZWZlMTExNmMxNjQ4Y>
        """
        self.assertEqual(msg, utils.preprocess(msg, "\n"))

        # 'On <date> <person> wrote' shouldn't be spread across too many lines
        msg = (
            "Hello\n"
            "How are you? On Nov 30, 2011, at 12:47 PM,\n "
            "Example <\n"
            "416ffd3258d4d2fa4c85cfa4c44e1721d66e3e8f4\n"
            "@example.org>"
            "wrote:\n"
            "\n"
            "> Hi"
        )
        self.assertEqual(msg, utils.preprocess(msg, "\n"))

        msg = "Hello On Nov 30, smb wrote:\n" "Hi\n" "On Nov 29, smb wrote:\n" "hi"

        prepared_msg = (
            "Hello\n" " On Nov 30, smb wrote:\n" "Hi\n" "On Nov 29, smb wrote:\n" "hi"
        )

        self.assertEqual(prepared_msg, utils.preprocess(msg, "\n"))

    def test_preprocess_postprocess_2_links(self):
        msg_body = "<http://link1> <http://link2>"
        self.assertEqual(msg_body, text.extract_from_plain(msg_body))

    def test_feedback_below_left_unparsed(self):
        msg_body = """Please enter your feedback below. Thank you.

-------------------------------------
Enter Feedback Below
-------------------------------------

The user experience was unparallelled. Please continue production.
I'm sending payment to ensure
that this line is intact."""

        parsed = text.extract_from_plain(msg_body)
        self.assertEqual(msg_body, parsed)


if __name__ == "__main__":
    unittest.main(verbosity=2)
