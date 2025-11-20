#!/usr/bin/env python3
"""
Clean wrapper for agentcore invoke - shows only the agent's response.
Usage: python ask.py "your question here"
"""

import subprocess
import re
import sys

def ask_agent(prompt):
    """Ask the agent and return clean response using regex extraction."""
    try:
        # Call agentcore invoke
        cmd = ['agentcore', 'invoke', f'{{"prompt": "{prompt}"}}']
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode != 0:
            return f"Error: {result.stderr}"
        
        output = result.stdout
        
        # Method 1: Try to extract text using regex (most reliable)
        # Pattern matches: "text": "..." including escaped characters
        pattern = r'"text":\s*"((?:[^"\\]|\\.)*)"\s*}'
        matches = re.findall(pattern, output, re.DOTALL)
        
        if matches:
            # Get the last match (the actual agent response)
            text = matches[-1]
            
            # Unescape common JSON escape sequences
            text = text.replace('\\n', '\n')
            text = text.replace('\\t', '\t')
            text = text.replace('\\"', '"')
            text = text.replace('\\\\', '\\')
            
            return text.strip()
        
        # Method 2: If regex fails, try to find Response: and extract manually
        if "Response:" in output:
            response_part = output.split("Response:")[1]
            # Try to find text field manually
            text_match = re.search(r'"text":\s*"([^"]*)"', response_part)
            if text_match:
                return text_match.group(1).replace('\\n', '\n').strip()
        
        # Method 3: If all else fails, return a helpful error
        return "Error: Could not extract response from agent output.\n\nTry using: python quick_check.py"
        
    except subprocess.TimeoutExpired:
        return "Error: Request timed out (30 seconds)"
    except Exception as e:
        return f"Error: {str(e)}\n\nTry using: python quick_check.py"

def main():
    if len(sys.argv) < 2:
        print("\n📝 Usage: python ask.py 'your question here'\n")
        print("Examples:")
        print("  python ask.py 'list instances'")
        print("  python ask.py 'list instances in table form'")
        print("  python ask.py 'check cpu'")
        print("  python ask.py 'why is cpu high'")
        print("  python ask.py 'should I scale up'")
        print("\nQuick alternative (for clean tables):")
        print("  python quick_check.py")
        print()
        sys.exit(1)
    
    # Get prompt from command line arguments
    prompt = ' '.join(sys.argv[1:])
    
    print(f"\n🤖 Question: {prompt}")
    print("=" * 80)
    print()
    
    # Ask agent
    response = ask_agent(prompt)
    
    # Print response
    print(response)
    
    print()
    print("=" * 80)
    print()

if __name__ == "__main__":
    main()
