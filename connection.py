def get_mail_ids(client):
    result_search, data = client.uid('SEARCH', 'ALL')
    if result_search != 'OK':
        raise Exception("Search failed!")
    msg_ids = data[0].decode('utf-8').split()
    return msg_ids


def connection_initialize(config):
    client = config['imap']['transport'](config['imap']['hostname'], port=config['imap']['port'])
    print(client.PROTOCOL_VERSION)
    print("Connected to mail server")
    if config['imap']['username'] and config['imap']['password']:
        login = client.login(config['imap']['username'], config['imap']['password'])
        if login[0] != 'OK':
            raise Exception("Unable to login", login)
    print("Logged in")
    select_folder = client.select(config['imap']['inbox'])
    if select_folder[0] != 'OK':
        raise Exception("Unable to select folder", select_folder)
    return client


def connection_close(client):
    client.close()
    print("Connection closed")
    client.logout()
    print("Logged out")