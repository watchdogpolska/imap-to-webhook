def get_mail_ids(client):
    result_search, data = client.uid('SEARCH', 'ALL')
    if result_search != 'OK':
        raise Exception("Search failed!")
    msg_ids = data[0].decode('utf-8').split()
    return msg_ids


def connection_initialize(config):
    transport = config['imap']['transport']
    hostname = config['imap']['hostname']
    port = config['imap']['port']
    client = transport(hostname=hostname, port=port)
    print("Connected to mail server")
    username = config['imap']['username']
    password = config['imap']['password']
    if username and password:
        login = client.login(username, password)
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
