import regex as re

MAX_LINES_COUNT = 1000
SPLITTER_MAX_LINES = 6
_MAX_TAGS_COUNT = 419
_BLOCKTAGS = ['div', 'p', 'ul', 'li', 'h1', 'h2', 'h3']
_HARDBREAKS = ['br', 'hr', 'tr']
_RE_EXCESSIVE_NEWLINES = re.compile("\n{2,10}")

QUOT_PATTERN = re.compile('^>+ ?')
RE_PARENTHESIS_LINK = re.compile("\(https?://")
RE_NORMALIZED_LINK = re.compile('@@(http://[^>@]*)@@')
RE_FWD = re.compile("^[-]+[ ]*Forwarded message[ ]*[-]+$", re.I | re.M)
RE_DELIMITER = re.compile('\r?\n')
RE_LINK = re.compile('<(http://[^>]*)>')
RE_ON_DATE_SMB_WROTE = re.compile(
    u'(-*[>]?[ ]?({0})[ ].*({1})(.*\n){{0,2}}.*({2}):?-*)'.format(
        # Beginning of the line
        u'|'.join((
            # English
            'On',
            # French
            'Le',
            # Polish
            'W dniu',
            # Dutch
            'Op',
            # German
            'Am',
            # Norwegian
            u'På',
            # Swedish, Danish
            'Den',
            # Vietnamese
            u'Vào',
        )),
        # Date and sender separator
        u'|'.join((
            # most languages separate date and sender address by comma
            ',',
            # polish date and sender address separator
            u'użytkownik'
        )),
        # Ending of the line
        u'|'.join((
            # English
            'wrote', 'sent',
            # French
            u'a écrit',
            # Polish
            u'napisał',
            # Dutch
            'schreef','verzond','geschreven',
            # German
            'schrieb',
            # Norwegian, Swedish
            'skrev',
            # Vietnamese
            u'đã viết',
        ))
    ))
RE_ORIGINAL_MESSAGE = re.compile(u'[\s]*[-]+[ ]*({})[ ]*[-]+'.format(
    u'|'.join((
        # English
        'Original Message', 'Reply Message',
        # German
        u'Ursprüngliche Nachricht', 'Antwort Nachricht',
        # Danish
        'Oprindelig meddelelse',
    ))), re.I)
RE_ON_DATE_WROTE_SMB = re.compile(
    u'(-*[>]?[ ]?({0})[ ].*(.*\n){{0,2}}.*({1})[ ]*.*:)'.format(
        # Beginning of the line
        u'|'.join((
        	'Op',
        	#German
        	'Am'
        )),
        # Ending of the line
        u'|'.join((
            # Dutch
            'schreef','verzond','geschreven',
            # German
            'schrieb'
        ))
    )
    )

RE_FROM_COLON_OR_DATE_COLON = re.compile(u'(_+\r?\n)?[\s]*(:?[*]?{})[\s]?:[*]?.*'.format(
    u'|'.join((
        # "From" in different languages.
        'From', 'Van', 'De', 'Von', 'Fra', u'Från',
        # "Date" in different languages.
        'Date', 'Datum', u'Envoyé', 'Skickat', 'Sendt',
    ))), re.I)
RE_ANDROID_WROTE = re.compile(u'[\s]*[-]+.*({})[ ]*[-]+'.format(
    u'|'.join((
        # English
        'wrote',
    ))), re.I)
RE_POLYMAIL = re.compile('On.*\s{2}<\smailto:.*\s> wrote:', re.I)
RE_QUOTATION = re.compile(
    r'''
    (
        # quotation border: splitter line or a number of quotation marker lines
        (?:
            s
            |
            (?:me*){2,}
        )

        # quotation lines could be marked as splitter or text, etc.
        .*

        # but we expect it to end with a quotation marker line
        me*
    )

    # after quotations should be text only or nothing at all
    [te]*$
    ''', re.VERBOSE)
RE_EMPTY_QUOTATION = re.compile(
    r'''
    (
        # quotation border: splitter line or a number of quotation marker lines
        (?:
            (?:se*)+
            |
            (?:me*){2,}
        )
    )
    e*
    ''', re.VERBOSE)

SPLITTER_PATTERNS = [
    RE_ORIGINAL_MESSAGE,
    RE_ON_DATE_SMB_WROTE,
    RE_ON_DATE_WROTE_SMB,
    RE_FROM_COLON_OR_DATE_COLON,
    # 02.04.2012 14:20 пользователь "bob@example.com" <
    # bob@xxx.mailgun.org> написал:
    re.compile("(\d+/\d+/\d+|\d+\.\d+\.\d+).*@", re.S),
    # 2014-10-17 11:28 GMT+03:00 Bob <
    # bob@example.com>:
    re.compile("\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}\s+GMT.*@", re.S),
    # Thu, 26 Jun 2014 14:00:51 +0400 Bob <bob@example.com>:
    re.compile('\S{3,10}, \d\d? \S{3,10} 20\d\d,? \d\d?:\d\d(:\d\d)?'
               '( \S+){3,6}@\S+:'),
    # Sent from Samsung MobileName <address@example.com> wrote:
    re.compile('Sent from Samsung .*@.*> wrote'),
    RE_ANDROID_WROTE,
    RE_POLYMAIL
    ]

