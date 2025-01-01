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
import yaml
import subprocess
import json

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

def build_prompt(prompt, args, memory_lines):
    """Build the full prompt for Ollama"""
    context = chat_history.get_context_window(memory_lines)
    context_str = "\n".join([f"user: {msg['content']}" for msg in context[-memory_lines:]])

    # Load personality data 
    with open(args.personality, 'r', encoding='utf-8') as f:
        personality_data = yaml.safe_load(f)
        agent_name = personality_data.get('agent-name', 'Unknown Agent')
        description = personality_data.get('description', 'No description available')
        function_name = personality_data.get('function_name', 'function_name')  
        function_description = personality_data.get('function_description', 'function_description')
        function_parameters = personality_data.get('function_parameters', 'function_parameters')

    # Agent personality
    personality = f"Agent Name: {agent_name}\nDescription: {description}"

    # Tool prompt
    tool_prompt = f"""
    You have access to the function '{function_name}' to '{function_description}'. Using parameters: {str(function_parameters)}

    If you choose to call a function ONLY reply in the following format with no prefix or suffix:

    {{
      "function": "{function_name}",
      "parameters": {{
        "parameter_name": "parameter_value"
      }}
    }}

    Reminder:
    - Function calls MUST follow the specified format
    - Pay attention to the correct format
    - Required parameters MUST be specified
    - Put the entire function call reply on one line
    """

    # Create the full prompt 
    full_prompt = [
        {"role": "personality", "content": personality},
        {"role": "tool", "content": tool_prompt},
        {"role": "user", "content": f"Previous conversation:\n{context_str}\n\nCurrent message: {prompt}"}
    ]

    return full_prompt

def query_ollama(prompt, args, memory_lines):
    """Send a prompt to Ollama and return the response"""
    try:
        logging.info(f"Sending prompt to Ollama (length: {len(prompt)} chars)")
        logging.info(f"Prompt: {prompt}")

        full_prompt = build_prompt(prompt, args, memory_lines)

        data = {
            "model": MODEL,
            "prompt": str(full_prompt),
            "stream": False
        }
        response = requests.post(OLLAMA_URL, json=data)
        response.raise_for_status()
        response_text = response.json()['response']
        logging.info(f"Received response from Ollama (length: {len(response_text)} chars)")
        logging.info(f"Ollama Response: {response_text}")
        return response_text
    except Exception as e:
        logging.error(f"Error querying Ollama: {e}")
        return f"Error querying Ollama: {e}"

def send_response(sock, message):
    """Send a response message through the socket"""
    try:
        sock.send(message.encode('utf-8'))
        logging.info("Response sent back to chat")
    except Exception as e:
        logging.error(f"Failed to send message: {e}")

def check_and_call_function(response, sock, personality):
    """Check if a function should be called and call it if necessary"""
    parsed_response = parse_tool_response(response)
    if parsed_response:
        function_name = parsed_response["function"]
        arguments = parsed_response["arguments"]

        if function_name == "query_dns":
            query = arguments.get("query")
            query_type = arguments.get("query_type")
            if query and query_type:
                dns_response = query_dns(query, query_type)
                if not dns_response:
                    dns_response = "No data returned by the tool"
                response_message = f"{personality['agent-name']}: {dns_response}\n"
                logging.info(f"Tool Response: {response_message}")
                return response_message

def handle_incoming_message(message, sock, args, personality, memory_lines):
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
        ollama_response = query_ollama(message, args, memory_lines)

        # Check and call function if necessary
        tool_response = check_and_call_function(ollama_response, sock, personality)

        if tool_response and tool_response.strip() != f"{personality['agent-name']}:":
            # Add tool response to history
            chat_history.add_message('Assistant', tool_response)
            send_response(sock, tool_response)
        else:
            # Add assistant response to history
            chat_history.add_message('Assistant', ollama_response)
            response_message = f"{personality['agent-name']}: {ollama_response}\n"
            send_response(sock, response_message)

    except Exception as e:
        error_message = f"Error processing message: {e}"
        logging.error(error_message)
        send_response(sock, error_message)

def receive_messages(sock, args, personality, memory_lines):
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
                    args=(data, sock, args, personality, memory_lines)
                )
                processing_thread.start()
                logging.info("Started processing thread for message")

        except Exception as e:
            logging.error(f"Error receiving message: {e}")
            sys.exit(1)

def parse_tool_response(response: str):
    function_regex = r'{\s*"function":\s*"(\w+)",\s*"parameters":\s*({.*?\s*.*?})\s*}'
    match = re.search(function_regex, response, re.DOTALL)

    if match:
        function_name, args_string = match.groups()
        try:
            args = json.loads(args_string)
            return {"function": function_name, "arguments": args}
        except json.JSONDecodeError as error:
            logging.error(f"Error parsing function arguments: {error}")
            return None
    return None

def query_dns(query: str, query_type: str) -> str:
    """Query a DNS server for a specific record type"""
    try:
        result = subprocess.run(
            ["dig", query, query_type, "+short"],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        logging.error(f"Error querying DNS: {e}")
        return f"Error querying DNS: {e}"

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
    parser.add_argument('-n', '--personality',
                        help='Personality of the agent',
                        required=False,
                        default='personality.yaml',
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

    # Load personality data 
    with open(args.personality, 'r', encoding='utf-8') as f:
        personality_data = yaml.safe_load(f)
        agent_name = personality_data.get('agent-name', 'Unknown Agent')
        description = personality_data.get('description', 'No description available')
        function_name = personality_data.get('function_name', 'function_name')  
        function_description = personality_data.get('function_description', 'function_description')
        function_parameters = personality_data.get('function_parameters', 'function_parameters')
        memory_lines = personality_data.get('memory_lines', 10)
        personality = {
            "agent-name": agent_name,
            "description": description,
            "function_name": function_name,
            "function_description": function_description,
            "function_parameters": function_parameters
        }

    # Start receive thread from the chat server
    receive_thread = threading.Thread(target=receive_messages, args=(sock, args, personality, memory_lines))
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
