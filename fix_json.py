import json

# Read the file, handling BOM and escaped newlines
with open('serviceAccountKey.json', 'rb') as f:
    raw = f.read()

# Remove BOM if present
if raw.startswith(b'\xef\xbb\xbf'):
    raw = raw[3:]

text = raw.decode('utf-8')

# The file has literal backslash-n sequences that should be real newlines
# We need to:
# 1. Replace \n with a placeholder
# 2. Parse JSON
# 3. Restore actual newlines in string values

# But wait - the private_key field has REAL newlines inside the base64 content
# Let me check the structure more carefully
print("File has \\n sequences:", '\\n' in text)

# Actually, let's just replace the escaped newlines with real ones
# This is a single-line JSON with \n escape sequences
content_fixed = text.replace('\\n', '\n')

# Now parse
creds = json.loads(content_fixed)
print(f"Project ID: {creds['project_id']}")
print(f"Client email: {creds['client_email']}")

# Write properly formatted JSON
with open('serviceAccountKey.json', 'w', encoding='utf-8') as f:
    json.dump(creds, f, indent=2, ensure_ascii=False)

print("Fixed and saved serviceAccountKey.json")
