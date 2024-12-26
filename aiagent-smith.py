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
import json
import requests
import logging
from datetime import datetime
import os


OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "llama3.1"  # Change this to your preferred model

def setup_logging():
    """Setup logging configuration"""
    # Create logs directory if it doesn't exist
    if not os.path.exists('logs'):
        os.makedirs('logs')
    
    # Create a timestamp for the log file
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file = f'logs/chat_session_{timestamp}.log'
    
    # Configure logging format and settings
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return log_file

def query_ollama(prompt):
    """Send a prompt to Ollama and return the response"""
    try:
        logging.info(f"Sending prompt to Ollama (length: {len(prompt)} chars)")
        data = {
            "model": MODEL,
            "prompt": prompt,
            "stream": False
        }
        response = requests.post(OLLAMA_URL, json=data)
        response.raise_for_status()
        response_text = response.json()['response']
        logging.info(f"Received response from Ollama (length: {len(response_text)} chars)")
        return response_text
    except Exception as e:
        logging.error(f"Error querying Ollama: {e}")
        return f"Error querying Ollama: {e}"

def handle_incoming_message(message, sock):
    """Process incoming message through Ollama and send response back"""
    try:
        # Get response from Ollama
        ollama_response = query_ollama(message)
        logging.info(f"Processing message: {message[:10000]}..." if len(message) > 10000 else f"Processing message: {message}")

        # Send response back through the socket
        response_message = f"Agent Smith: {ollama_response}"
        response_message += '\n'
        sock.send(response_message.encode('utf-8'))
        logging.info("Response sent back to chat")
    except Exception as e:
        error_message = f"Error processing message: {e}"
        logging.error(error_message)
        sock.send(error_message.encode('utf-8'))

def receive_messages(sock):
    """Receive messages from the server and process them through Ollama"""
    while True:
        try:
            data = sock.recv(1024).decode('utf-8')
            if not data:
                logging.warning("Disconnected from server")
                print("\nDisconnected from server")
                sys.exit(0)

            logging.info(f"Received new message from chat (length: {len(data)} chars)")
            
            print(f"\nReceived message: {data}")
            # Process message through Ollama in a separate thread
            processing_thread = threading.Thread(
                target=handle_incoming_message,
                args=(data, sock)
            )
            processing_thread.start()
            logging.info("Started processing thread for message")
            
        except Exception as e:
            logging.error(f"Error receiving message: {e}")
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

    # Setup logging
    log_file = setup_logging()
    logging.info(f"Starting new chat session. Log file: {log_file}")

    # Create socket and connect to the ncat server
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((args.chatserverip, args.chatserverport))
        logging.info(f"Successfully connected to chat server at {args.chatserverip}:{args.chatserverport}")
        logging.info(f"Using Ollama model: {MODEL}")
    except Exception as e:
        logging.error(f"Failed to connect to chat server: {e}")
        sys.exit(1)

    # Start receive thread from the chat server
    receive_thread = threading.Thread(target=receive_messages, args=(sock,))
    receive_thread.daemon = True
    receive_thread.start()
    logging.info("Message receiving thread started")
    
    # Keep the main thread running
    try:
        while True:
            # Just keep the program running
            threading.Event().wait()
    except KeyboardInterrupt:
        print("\nClosing connection...")
        logging.info("Received shutdown signal")
    except Exception as e:
        print(f"Error: {e}")
        logging.error(f"Unexpected error: {e}")
    finally:
        logging.info("Closing connection and ending session")
        sock.close()

if __name__ == '__main__':
    main()
