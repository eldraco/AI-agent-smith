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
import requests
import logging
from datetime import datetime
import os
from collections import deque
import re

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "llama3.1"  # Change this to your preferred model
#MODEL = "smollm2"

class ChatHistory:
    def __init__(self):
        self.messages = deque()
        self.history_file = 'history_file.txt'
        self.lock = threading.Lock()

    def setup(self, session_timestamp):
        """Setup the history file"""
        if not os.path.exists('logs'):
            os.makedirs('logs')
        self.history_file = f'logs/chat_history_{session_timestamp}.txt'
        
    def add_message(self, role, content):
        """Add a message to history and save to file"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        message = {
            'timestamp': timestamp,
            'role': role,
            'content': content
        }
        
        with self.lock:
            self.messages.append(message)
            # Save to file
            with open(self.history_file, 'a', encoding='utf-8') as f:
                f.write(f"[{timestamp}] {role}: {content}\n")
    
    def get_full_history(self):
        """Return the full conversation history"""
        with self.lock:
            return list(self.messages)

    def get_context_window(self, window_size=10):
        """Get the last n messages for context"""
        with self.lock:
            return list(self.messages)[-window_size:]

# Global chat history instance
chat_history = ChatHistory()

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

        context = chat_history.get_context_window()
        context_str = "\n".join([f"{msg['role']}: {msg['content']}" for msg in context[-100:]])
        full_prompt = f"Previous conversation:\n{context_str}\n\nCurrent message: {prompt}"


        data = {
            "model": MODEL,
            "prompt": full_prompt,
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
        # Skip announcement messages
        if message.startswith('<announce>'):
            logging.info(f"Skipping announcement: {message}")
            return

        logging.info(f"Processing message: {message[:10000]}..." if len(message) > 10000 else f"Processing message: {message}")

        # Add user message to history
        chat_history.add_message('User', message)

        # Get response from Ollama
        ollama_response = query_ollama(message)

        # Add assistant response to history
        chat_history.add_message('Assistant', ollama_response)

        # Send response back through the socket
        response_message = f"Agent Smith: {ollama_response}"
        response_message += '\n'
        sock.send(response_message.encode('utf-8'))
        logging.info("Response sent back to chat")
    except Exception as e:
        error_message = f"Error processing message: {e}"
        logging.error(error_message)
        try:
            sock.send(error_message.encode('utf-8'))
        except:
            logging.error("Failed to send error message back to socket")

def receive_messages(sock):
    """Receive messages from the server and process them"""
    while True:
        try:
            data = sock.recv(1024).decode('utf-8')
            if not data:
                logging.warning("Disconnected from server")
                sys.exit(0)

            logging.info(f"Received new message from chat: {data}")

            # Process all non-empty messages
            clean_data = re.sub(r'^<\w+>', '', data)
            if clean_data.strip():
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
    parser.add_argument('-p', '--personality',
                        help='Personality of the agent',
                        required=True,
                        default='personality.yml',
                        type=str)
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

    # Add the personality to the chat history so it is at the beginning
    with open(args.personality, 'r', encoding='utf-8') as f:
        personality = f.read()
        chat_history.add_message('Personality', personality) # Add personality to history
    
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
