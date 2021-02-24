#!/usr/bin/python3
import socket
import sys

# open TCP client socket

# read input cmd from keyboard

# compose msg

# send msg to server


def is_valid_cmd(buf):
    if not buf:
        return False
    cmd_list = ["#USERNAME", "#PASSWORD", "#SENDTO", "#TITLE",
                "#CONTENT", ".", "#LIST", "#RETRIEVE", "#DELETE", "#EXIT"]
    buf = buf.split()
    return buf[0] in cmd_list


def main(argv):
    SERVER_IP = "127.0.0.1"
    SERVER_PORT = 8000

    # create socket and connect to server
    try:
        sockfd = socket.socket()
        sockfd.settimeout(10)
        sockfd.connect((SERVER_IP, SERVER_PORT))
    except socket.error as emsg:
        print("Socket error: ", emsg)
        sys.exit(1)

    read_buf = ""
    while read_buf != "exit":
        read_buf = input()
        if not is_valid_cmd(read_buf):
            print("invalid command")
            continue

        try:
            sockfd.send(read_buf.encode())
        except:
            break

        try:
            rmsg = sockfd.recv(1024).decode()
            print(rmsg)
        except socket.error as emsg:
            continue

    sockfd.close()


if __name__ == '__main__':
    if len(sys.argv) != 1:
        print("Usage: python3 MailClient.py")
        sys.exit(1)
    main(sys.argv)
