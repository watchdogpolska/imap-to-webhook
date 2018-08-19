# imap-to-webhook

A stateless service is designed to build a relay between an IMAP server and any web application in a simple,
convenient way, well-known by web-developers, without delving into the format of the mail format.

Using the service requires only writing one HTTP endpoint!

It cyclically retrieves IMAP messages from selected IMAP folder, parsers them into a convenient JSON object for
use in web applications. Next to send to specified HTTP(S) endpoint. The message can be moved to
another IMAP folder or deleted completely. In case of connection errors, the message is moved to another folder.

Send JSON object, among others includes:

 * extracted HTML (if available) or text content
 * message divided into content and quote
 * all attachments and filenames of them,
 * indication if the message is automatic (vacation reply, confirmation of receipt)

## Configuration

Configuration takes place via environment variables. The following environment variables are supported:

Name                      | Description 
--------------------------| -----------
```IMAP_URL```            | URL connection to access mailbox. Example ````imap+ssl://user:pass@localhost/?inbox=INBOX````
```IMAP_URL?folder```     | Folder to download messages
```IMAP_URL?error```      | Folder to move messages on error (````error````)
```IMAP_URL?success```    | Folder to store messages on success (```success```)
```ON_SUCCESS```          | Action to perform on process messages. Available ```move```, ```delete```
```WEBHOOK_URL```         | URL endpoint to send parsed messages. Example: ```https://httpbin.org/post```
```COMPRESSION_EML```     | Specifies whether the sent ```.eml``` file should be compressed or not. Example: ```true```
```DELAY```               | The length of the interval between the next downloading of the message in seconds. Default: ```300```


## Request

Here ie example request which you can expect to receive:

```
{
    "headers": {
        "auto_reply_type": "vacation-reply",
        "cc": [],
        "date": "2018-07-30T11:33:22",
        "from": [
            "user-a@siecobywatelska.pl"
        ],
        "message_id": "<E1fk6QU-00CPTw-Ey@s50.hekko.net.pl>",
        "subject": "Odpowied\u017a automatyczna: \"Re: Problem z dostarczeniem odp. na fedrowanie\"",
        "to": [
            "user-b@siecobywatelska.pl"
        ],
        "to+": [
            "user-b@siecobywatelska.pl",
            "user-c@siecobywatelska.pl"
        ]
    },
    "text": {
        "content": "W dniach 30.07-17.08.2018 r. przebywam na urlopie.",
        "quote": ""
    },
    "files_count": 1,
    "files": {
        "content": "...base64-encoded-bytes...",
        "filename": "my-doc.txt"
    },
    "eml": {
        "compressed": true,
        "content": "...base64-encoded-gzipped-bytes..."
    }
}
```

It contains fields:

JSON Path                             | Description
------------------------------------- | -----------
```headers.auto_reply_type```         | Indicates whether the message is automatic or send by human. Empty, if no indicators of automatic character were found.
```headers.cc```                      | List of e-mail address in ```CC```
```headers.date```                    | Date available of message. The values can be hijacked by the recipient to include any date
```headers.from```                    | List of address available in ```From``` header
```headers.message_id```              | Message identifier from the ```Message-ID``` header
```headers.subject```                 | An additional comment is not required
```headers.to```                      | List of e-mail address in ```To``` header
```headers.to+```                     | List of various potential message recipients address, even redirected.
```text.content```                    | Text content of the message, converted from HTML (if available) or text form and truncated to the new content itself
```text.quote```                      | Content truncated from a content that is potentially a quote
```files_count```                     | Number of attachments
```files.*.content```                 | Base-64 encoded binary content of the attachment
```files.*.filename```                | Filename of attachment
```eml.*.compressed```                | Determines whether the next field contains gzip compressed content or uncompressed.
```eml.*.content```                   | Original ```.eml``` message without any modifications, except lossless compresion

## Run

```shell
$ docker build -t imap-to-webook:latest .
$ docker run -e IMAP_URL=imap://imap.example.com/ -e WEBHOOK_URL="https://example.com" imap-to-webhook:latest
```


## Development

In order to facilitate the development, the docker-compose.yml file is provided.

```
$ git clone git@github.com:watchdogpolska/imap-to-webhook.git 
$ cd imap-to-webhook
$ cp .env.sample .env
$ docker-compose up
```

The following services are provided:

* ```daemon``` - proper service
* ```mock``` - a simple web server that accepts requests and writes them to the ```stdout```.

## Testing

Following commands are required to run tests:

```
pip install -r requirements.txt
python test.py
```
