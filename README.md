# AIAgent Smith
AIAgent Smith is a an AI agent that connects to an ncat chat program to chat with other users. Every message is sent to an ollama model to ask a response.

The idea is to have many agents connected in a chat room, and users to be able to ask them for different things, like going to the Internet, checking files, performing security scans, etc.

In the future, each agent will provide a service.

# Install
```
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

# Use

1. Start an ncat chat server
Be careful it will be open in the whole network. 
`ncat -l 9000 -k --broker --chat`

If you want only in localhost, then do:
`ncat -l 127.0.0.1 9000 -k --broker --chat`

2. Connect with one or more AI Agent Smith
`python aiagent-smith.p`

3. Connect with one or more human users
`ncat 127.0.0.1 9000`

4. Have fun.

# TODO
- To offer services
- To ask for services