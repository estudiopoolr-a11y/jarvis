import json

# Read the file and parse it properly handling the escaped newlines
with open('serviceAccountKey.json', 'r') as f:
    content = f.read()

# The content has literal \n sequences that need to be converted to actual newlines
# but the private_key has embedded newlines that should be preserved
# First, let's parse it as a single-line JSON with escaped newlines
# We need to handle the private_key specially

# Step 1: Replace \n with a placeholder that won't conflict
content_fixed = content.replace('\\n', '\x00NEWLINE\x00')

# Step 2: Parse the JSON
creds = json.loads(content_fixed)

# Step 3: Restore actual newlines in string values
for key in creds:
    if isinstance(creds[key], str):
        creds[key] = creds[key].replace('\x00NEWLINE\x00', '\n')

# Step 4: Write the corrected file
with open('serviceAccountKey.json', 'w') as f:
    json.dump(creds, f, indent=2)

print("Fixed serviceAccountKey.json")
print(f"Project ID: {creds['project_id']}")
print(f"Client email: {creds['client_email']}")
