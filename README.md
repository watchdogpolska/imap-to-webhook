# imap-to-webhook

The service is designed to build an IMAP gateway, and any web application in a simple and convenient way.

It cyclically retrieves IMAP messages, parsers them into a convenient object for use in web applications. Next to 
send to specifieed HTTP(S) endpoint. The message can be moved to another IMAP folder or deleted completely.
In case of connection errors, the message is moved to another folder.

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

