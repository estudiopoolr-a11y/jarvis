import json
import re

# Read the file, handling BOM
with open('serviceAccountKey.json', 'rb') as f:
    raw = f.read()

# Remove BOM if present
if raw.startswith(b'\xef\xbb\xbf'):
    raw = raw[3:]

text = raw.decode('utf-8')

# The problem is the file has \n sequences but also the private_key has
# actual newlines in the base64 content. We need to be smarter about this.
# 
# The structure is: all fields are on one line with \n separators
# BUT the private_key value itself contains embedded newlines from base64

# Let's parse more carefully - find the private_key field and preserve its content
# Actually, let's just use json.loads with strict=False to allow control characters
# Then fix the private_key field

try:
    # Try parsing with strict=False first
    creds = json.loads(text, strict=False)
    print("Parsed with strict=False")
except json.JSONDecodeError:
    # The issue is the private_key has actual newlines inside the string
    # Let's try to fix by properly escaping them
    
    # Find the private_key field and fix it
    # Pattern: "private_key": "content with newlines"
    def fix_private_key(match):
        key_value = match.group(1)
        # Escape any newlines in the value
        fixed = key_value.replace('\n', '\\n')
        return f'"private_key": "{fixed}"'
    
    text_fixed = re.sub(r'"private_key": "(.*?)"', fix_private_key, text, flags=re.DOTALL)
    
    # Also fix other fields that might have similar issues
    # But first, let's try the simple fix
    try:
        creds = json.loads(text_fixed)
        print("Parsed after fixing private_key")
    except json.JSONDecodeError as e2:
        print(f"Still failing: {e2}")
        # Let's try another approach - find all strings with newlines and escape them
        def escape_newlines_in_strings(m):
            return m.group(0).replace('\n', '\\n')
        
        # This is tricky because we need to only escape newlines inside JSON strings
        # Let's use a different approach: parse character by character
        
        # Actually, the simplest fix is to just escape ALL newlines in the JSON
        # since they should be \n escape sequences anyway
        text_escaped = text.replace('\n', '\\n')
        try:
            creds = json.loads(text_escaped)
            print("Parsed after escaping all newlines")
        except json.JSONDecodeError as e3:
            print(f"Still failing after full escape: {e3}")
            # Last resort: show what we have
            print(f"Text around error: {repr(text[150:200])}")
            raise

# Write properly formatted JSON
with open('serviceAccountKey.json', 'w', encoding='utf-8') as f:
    json.dump(creds, f, indent=2, ensure_ascii=False)

print(f"Project ID: {creds['project_id']}")
print(f"Client email: {creds['client_email']}")
print("Fixed and saved serviceAccountKey.json")
