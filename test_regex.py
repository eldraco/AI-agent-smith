import re
import json

def test_regex(response: str):
    function_regex_escaped = r'{\\n\s*"function":\s*"(\w+)",\\n\s*"parameters":\s*({.*?})\\n\s*}'
    function_regex_actual = r'{\s*"function":\s*"(\w+)",\s*"parameters":\s*({.*?})\s*}'

    match = re.search(function_regex_escaped, response, re.DOTALL) or re.search(function_regex_actual, response, re.DOTALL)

    if match:
        function_name, args_string = match.groups()
        try:
            args = json.loads(args_string)
            parsed_response = {"function": function_name, "arguments": args}
            print("Match found:", parsed_response)
        except json.JSONDecodeError as error:
            print(f"Error parsing function arguments: {error}")
    else:
        print("No match found")

if __name__ == "__main__":
    test_strings = [
        '{\\n  "function": "query_dns",\\n  "parameters": {\\n    "query": "example.com",\\n    "query_type": "TXT"\\n  }\\n}',
        '{\n  "function": "query_dns",\n  "parameters": {\n    "query": "example.com",\n    "query_type": "TXT"\n  }\n}',
        '{\\n  "function": "query_dns",\\n  "parameters": {\\n    "query": "example.com"\\n  }\\n}',
        '{\n  "function": "query_dns",\n  "parameters": {\n    "query": "example.com"\n  }\n}',
        '{\\n  "function": "query_dns",\\n  "parameters": {\\n    "query": "example.com",\\n    "query_type": "A"\\n  }\\n}',
        '{\n  "function": "query_dns",\n  "parameters": {\n    "query": "example.com",\n    "query_type": "A"\n  }\n}'
    ]

    for response in test_strings:
        print(f"Testing string: {response}")
        test_regex(response)
        print("-" * 50)
