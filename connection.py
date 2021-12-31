class IMAPClient:
    def __init__(self, config):
        transport = config["imap"]["transport"]
        hostname = config["imap"]["hostname"]
        port = config["imap"]["port"]
        self.client = transport(host=hostname, port=port)
        print("Connected to mail server")
        username = config["imap"]["username"]
        password = config["imap"]["password"]
        if username and password:
            login = self.client.login(username, password)
            if login[0] != "OK":
                raise Exception("Unable to login", login)
        print("Logged in")
        select_folder = self.client.select(config["imap"]["inbox"])
        if select_folder[0] != "OK":
            raise Exception("Unable to select folder", select_folder)

    def get_mail_ids(self):
        result_search, data = self.client.uid("SEARCH", "ALL")
        if result_search != "OK":
            raise Exception("Search failed!")
        return data[0].decode("utf-8").split()

    def fetch(self, msg_id):
        result_fetch, data = self.client.uid("FETCH", "{0}:{0} RFC822".format(msg_id))
        if result_fetch != "OK":
            raise Exception("Fetch failed!")
        return data[0][1]

    def connection_close(self):
        self.client.close()
        print("Connection closed")
        self.client.logout()
        print("Logged out")

    def move(self, msg_id, folder):
        print("Going to move {} to {}".format(msg_id, folder))
        self.copy(folder, msg_id)
        self.mark_delete(msg_id)

    def mark_delete(self, msg_id):
        print("Going to mark as deleted {}".format(msg_id))
        delete_result, _ = self.client.uid("STORE", msg_id, "+FLAGS", r"(\Deleted)")
        if delete_result != "OK":
            raise Exception("Failed to mark as deleted msg {}".format(msg_id))

    def copy(self, folder, msg_id):
        print("Going to copy {} to {}".format(msg_id, folder))
        copy_result, data = self.client.uid("COPY", msg_id, folder)
        if copy_result != "OK":
            print(copy_result, data)
            raise Exception("Failed to copy msg {} to {}".format(msg_id, folder))

    def expunge(self):
        self.client.expunge()
