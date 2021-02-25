#!/usr/bin/python3
import socket
import sys


def main(argv):
    SERVER_IP = "127.0.0.1"
    SERVER_PORT = 8000

    try:
        sockfd = socket.socket()
        sockfd.settimeout(10)
        sockfd.connect((SERVER_IP, SERVER_PORT))
    except socket.error as emsg:
        print("Socket error: ", emsg)
        sys.exit(1)

    while True:
        read_buf = input()
        request = read_buf

        if read_buf == "exit":
            break
        elif read_buf == "#CONTENT":
            request += " "
            while True:
                read_buf = input()
                if read_buf == ".":
                    break
                elif not read_buf:
                    continue
                request += "{}\n".format(read_buf)

        try:
            sockfd.send(request.encode())
        except socket.error as emsg:
            print(emsg)
            break

        try:
            rmsg = sockfd.recv(1024).decode()
            print(rmsg)
        except socket.error as emsg:
            print(emsg)
            continue

    sockfd.close()


if __name__ == '__main__':
    if len(sys.argv) != 1:
        print("Usage: python3 MailClient.py")
        sys.exit(1)
    main(sys.argv)
