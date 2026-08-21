import subprocess
import os
import re

# Workspace path inside the container
WORKSPACE = os.getenv("AGENT_WORKSPACE", "/app/workspace")
MAX_OUTPUT_SIZE = 10240  # 10 KB

# Whitelist of allowed commands (Linux)
ALLOWED = {
    "ls", "cat", "cp", "mv", "mkdir", "echo", "find", "grep", "wc", "head", 
    "tail", "pwd", "whoami", "date", "uptime", "chmod", "chown", "touch", "ln",
    "du", "stat", "file", "readlink", "basename", "dirname",
}


def run_console_command(cmd: str) -> str:
    """Execute a safe command in the workspace directory."""
    cmd = cmd.strip()
    if not cmd:
        return "Error: Empty command."
    
    cmd_parts = cmd.split()
    command = cmd_parts[0]
    
    # 1. Check whitelist
    if command not in ALLOWED:
        return f"Error: Command '{command}' is not allowed. Allowed: {', '.join(sorted(ALLOWED))}"
    
    # 2. Block dangerous operations
    if command == "rm":
        return "Error: 'rm' is not allowed for safety."
    
    # 3. Path validation: block ".." in any argument
    for part in cmd_parts[1:]:
        if ".." in part:
            return "Error: '..' in path is not allowed."
    
    # Block absolute paths outside workspace
    if cmd.startswith("/") and not cmd.startswith(WORKSPACE):
        return "Error: Absolute paths outside workspace are not allowed."
    
    # 4. Execute in workspace directory
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            cwd=WORKSPACE,
            timeout=5,
            capture_output=True,
            text=True
        )
        
        output = result.stdout + result.stderr
        if result.returncode != 0:
            output = f"Command failed with exit code {result.returncode}.\n{output}"
            
        # Limit output size
        if len(output) > MAX_OUTPUT_SIZE:
            output = output[:MAX_OUTPUT_SIZE] + "\n[Output truncated due to size limit (10KB)]"
            
        return output or "Command completed successfully (no output)."
        
    except subprocess.TimeoutExpired:
        return "Error: Command execution timed out (5 seconds limit)."
    except Exception as e:
        return f"System error: {str(e)}"
