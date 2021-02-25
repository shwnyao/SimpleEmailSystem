#!/usr/bin/python3
import socket
import threading
import sys
import time


class EmailAccountMananger():
    def __init__(self):
        self.account_info = self._read_account_db()
        self.name = None
        self.authenticated = False

    def check_account_name(self, name):
        return name in self.account_info.keys()

    def check_username(self, name):
        is_valid_username = self.check_account_name(name)
        self.name = name if is_valid_username else None
        self.authenticated = False
        return is_valid_username

    def authenticate(self, password):
        self.authenticated = (self.name is not None
                              and password == self.account_info[self.name])
        return self.authenticated

    def logout(self):
        self.authenticated = False
        self.name = None

    def send_email(self, email):
        recipient_mailbox_filename = email.recipient + ".txt"
        fd = open(recipient_mailbox_filename, "a")
        fd.write("\n")
        fd.write(email.gen_txt())
        fd.close()

    def get_mailbox_headers(self):
        self.mails = self._read_mail_db()
        if not self.mails:
            return []

        headers = []
        for i in range(len(self.mails)):
            mail = self.mails[i]
            header = "*" if mail[0][0] == "*" else ""
            header += "{} ".format(i+1)
            header += mail[0].lstrip("*").rstrip("\n") + " " + \
                mail[1].rstrip("\n") + " " + mail[2].rstrip("\n")
            headers.append(header)

        headers.reverse()
        headers.append(".")
        return headers

    def get_email_by_id(self, id):
        if id is None or len(self.mails) < id or id < 1:
            return None

        self.mails[id-1][0] = self.mails[id-1][0].lstrip("*")
        self._update_mail_db()

        return self.mails[id-1]

    def delete_email_by_id(self, id):
        if id is None or len(self.mails) < id or id < 1:
            return -1

        del self.mails[id-1]
        self._update_mail_db()
        return 0

    def _update_mail_db(self):
        my_mailbox_filename = self.name + ".txt"
        fd = open(my_mailbox_filename, "w")
        for mail in self.mails:
            fd.writelines(mail)
            fd.write("\n")
        fd.close()

    def _read_mail_db(self):
        my_mailbox_filename = self.name + ".txt"
        fd = open(my_mailbox_filename, "r")
        lines = fd.readlines()
        if lines:
            lines.append("\n")
        fd.close()

        mails = []
        mail_txt = []
        for line in lines:
            if line != "\n":
                mail_txt.append(line)
            else:
                if mail_txt:
                    mails.append(mail_txt)
                mail_txt = []

        return mails

    def _read_account_db(self):
        try:
            fd = open("ClientInfo.txt", "r")
        except IOError as emsg:
            print(emsg)
            return None

        lines = [line.rstrip('\n') for line in fd.readlines()]
        fd.close()

        account_info = {}
        for i in range(int(len(lines)/2)):
            name = lines[i*2]
            password = lines[i*2+1]
            account_info[name] = password

        return account_info


class EmailDraft():
    def __init__(self, sender, recipient):
        self.sender = sender
        self.recipient = recipient
        self.title = None
        self.content = None

    def set_title(self, title):
        self.title = title

    def set_content(self, content):
        self.content = content

    def gen_txt(self):
        t = time.strftime("%a, %d %b %Y %H:%M:%S %Z", time.gmtime())
        txt = "*FROM {}\n".format(self.sender) + \
            "TITLE {}\n".format(self.title) + \
            "Time {}\n".format(t) + \
            self.content

        return txt


class ServerThread(threading.Thread):

    def __init__(self, client):
        threading.Thread.__init__(self)
        self.client = client
        self.auth = EmailAccountMananger()
        self.draft = None

    def run(self):
        conn_sock, addr = self.client

        while True:
            try:
                request = conn_sock.recv(1024).decode()
                if not request:
                    continue
            except socket.error as emsg:
                print("Socket recv error: ", emsg)
                break

            response = self.process_cmd(request)
            if response:
                conn_sock.send(response.encode())

        conn_sock.close()

    def process_cmd(self, request: str):
        cmd = request.split(' ')
        # print(cmd)
        response = ""
        if cmd[0] == "#USERNAME":
            name = None if len(cmd) < 2 else cmd[1]
            response = self.username_handler(name)

        elif cmd[0] == "#PASSWORD":
            password = None if len(cmd) < 2 else cmd[1]
            response = self.password_handler(password)

        elif not self.auth.authenticated:
            response = self.perm_deny_handler()

        elif cmd[0] == "#SENDTO":
            recipient = None if len(cmd) < 2 else cmd[1]
            response = self.draft_recipient_handler(recipient)

        elif cmd[0] == "#TITLE":
            title = None if len(cmd) < 2 else " ".join(cmd[1:])
            response = self.draft_title_handler(title)

        elif cmd[0] == "#CONTENT":
            content = None if len(cmd) < 2 else " ".join(cmd[1:])
            response = self.draft_content_handler(content)
            if response == None:
                response = self.draft_send_handler()

        elif cmd[0] == "#LIST":
            response = self.mailbox_list_handler()

        elif cmd[0] == "#RETRIEVE":
            id = None if len(cmd) < 2 else int(cmd[1])
            response = self.retrieve_handler(id)

        elif cmd[0] == "#DELETE":
            id = None if len(cmd) < 2 else int(cmd[1])
            response = self.delete_handler(id)

        elif cmd[0] == "#EXIT":
            response = self.exit_handler()

        else:
            response = self.invalid_req_handler()
        return response

    def invalid_req_handler(self):
        return "200 Command not found"

    def perm_deny_handler(self):
        return "200 User not logged in yet"

    def username_handler(self, name):
        if not self.auth.check_username(name):
            return "200 Username does not exist"

        return "250 Username ok"

    def password_handler(self, password):
        authenticated = self.auth.authenticate(password)
        response = "250 User authenticated" if authenticated else "200 Authentication failure"
        return response

    def draft_recipient_handler(self, recipient):
        if self.auth.check_account_name(recipient):
            self.draft = EmailDraft(self.auth.name, recipient)
            response = "250 Recipient ok"
        else:
            response = "200 Recipient does not exist on the server"
        return response

    def draft_title_handler(self, title):
        if self.draft is None or self.draft.recipient is None:
            response = "200 Recipient is missing"
        else:
            self.draft.set_title(title)
            response = "250 Title ok"
        return response

    def draft_content_handler(self, content):
        if self.draft is None or self.draft.recipient is None:
            response = "200 Recipient is missing"
        elif self.draft.title is None:
            response = "200 Title is missing"
        else:
            self.draft.set_content(content)
            response = None

        return response

    def draft_send_handler(self):
        self.auth.send_email(self.draft)
        self.draft = None
        response = "250 Content ok"
        return response

    def mailbox_list_handler(self):
        headers = self.auth.get_mailbox_headers()
        if not headers:
            response = "200 Mailbox empty"
        else:
            response = "\n".join(headers)
        return response

    def retrieve_handler(self, id):
        mail = self.auth.get_email_by_id(id)
        if not mail:
            response = "200 Email does not exist"
        else:
            response = "".join(mail) + "."
        return response

    def delete_handler(self, id):
        err = self.auth.delete_email_by_id(id)
        if err:
            response = "200 Delete failed"
        else:
            response = "250 Delete ok"
        return response

    def exit_handler(self):
        self.auth.logout()
        return "250 Exit ok"


def main(argv):
    SERVER_PORT = 8000

    sockfd = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sockfd.bind(("", SERVER_PORT))

    sockfd.listen(5)
    while True:
        client = sockfd.accept()
        t = ServerThread(client)
        t.start()


if __name__ == '__main__':
    if len(sys.argv) != 1:
        print("Usage: python3 MailServer.py")
        sys.exit(1)
    main(sys.argv)
