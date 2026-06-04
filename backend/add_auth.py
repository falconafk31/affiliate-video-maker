import re

file_path = "main.py"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# Endpoints to protect (all except health, login, auth-logs, debug, stream)
# Note: Stream doesn't easily support Authorization headers via standard EventSource, so we skip it for now.
endpoints_to_protect = [
    r"@app\.post\(\"/api/process-video\"\)",
    r"@app\.post\(\"/api/generate-hook\"\)",
    r"@app\.post\(\"/api/generate-audio\"\)",
    r"@app\.get\(\"/api/logs\"\)",
    r"@app\.get\(\"/api/logs/download\"\)",
    r"@app\.delete\(\"/api/logs/clear\"\)",
    r"@app\.post\(\"/api/library/upload\"\)",
    r"@app\.get\(\"/api/library\"\)",
    r"@app\.delete\(\"/api/library/\{video_id\}\"\)",
    r"@app\.post\(\"/api/jobs/submit\"\)"
]

def add_param(match):
    full_def = match.group(0)
    # Check if already added
    if "get_current_user" in full_def:
        return full_def
        
    # If the function has no params `def func():`
    if re.search(r"\(\s*\):", full_def):
        return re.sub(r"\(\s*\):", "(current_user: str = Depends(get_current_user)):", full_def)
    
    # If it has params, inject before the closing parenthesis
    # Handle single line and multi-line param lists
    # Find the last closing parenthesis before the colon
    # Using a simple reverse find
    
    last_paren_idx = full_def.rfind("):")
    if last_paren_idx != -1:
        # Check if the last param has a trailing comma
        before_paren = full_def[:last_paren_idx].rstrip()
        if not before_paren.endswith(","):
            replacement = ",\n    current_user: str = Depends(get_current_user)\n):"
        else:
            replacement = "\n    current_user: str = Depends(get_current_user)\n):"
            
        return full_def[:last_paren_idx] + replacement + full_def[last_paren_idx+2:]
    return full_def

for ep in endpoints_to_protect:
    # Pattern to match the decorator and the following def block until the colon
    pattern = ep + r"\s+async def \w+\([^)]*\):|" + ep + r"\s+def \w+\([^)]*\):"
    
    content = re.sub(pattern, add_param, content)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("Injected auth dependencies successfully.")
