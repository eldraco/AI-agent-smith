#!/usr/bin/python
#  Copyright (C) 2024  Sebastian Garcia
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
#
# Author:
# Sebastian Garcia, eldraco@gmail.com
#
# Changelog

# Description
#


# standard imports
import argparse
import threading
import sys
import socket

def receive_messages(sock):
    """Receive and print messages from the server"""
    while True:
        try:
            data = sock.recv(1024).decode('utf-8')
            if not data:
                print("\nDisconnected from server")
                sys.exit(0)
            print(f"\nReceived: {data}")
            print("Your message: ", end='', flush=True)
        except Exception as e:
            print(f"\nError receiving message: {e}")
            sys.exit(1)

def main():
    print('AIAgent Smith: An AI Agent to follow your orders.')
    print('Author: Sebastian Garcia (eldraco@gmail.com)')

    # Parse the parameters
    parser = argparse.ArgumentParser()
    parser.add_argument('-v', '--verbose',
                        help='Amount of verbosity.',
                        action='store',
                        required=False,
                        type=int)
    parser.add_argument('-e', '--debug',
                        help='Amount of debugging.',
                        action='store',
                        required=False,
                        type=int)
    parser.add_argument('-s', '--chatserverip',
                        help='Chatting server',
                        required=False,
                        default='127.0.0.1',
                        type=str)
    parser.add_argument('-p', '--chatserverport',
                        help='Chat server port.',
                        required=False,
                        default=9000,
                        type=int)
    parser.add_argument('-o', '--ollamaserver',
                        help='IP address of the ollama server',
                        required=False,
                        default='127.0.0.1',
                        type=str)
    parser.add_argument('-P', '--ollamaserverport',
                        help='Port of the ollama server',
                        required=False,
                        default=11434,
                        type=int)
    args = parser.parse_args()

    # Create socket and connect to the ncat server
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((args.chatserverip, args.chatserverport))
        print(f"Connected to {args.chatserverip}:{args.chatserverport}")
    except Exception as e:
        print(f"Failed to connect: {e}")
        sys.exit(1)
    
    # Start receive thread
    receive_thread = threading.Thread(target=receive_messages, args=(sock,))
    receive_thread.daemon = True
    receive_thread.start()
    
    # Main send loop
    try:
        while True:
            message = input("Your message: ")
            if message.lower() == 'quit':
                break
            message += '\n'
            sock.send(message.encode('utf-8'))
    except KeyboardInterrupt:
        print("\nClosing connection...")
    except Exception as e:
        print(f"Error sending message: {e}")
    finally:
        sock.close()

if __name__ == '__main__':
    main()
