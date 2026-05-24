import os
import re

directories = ["gui4aws", "tests", "tests_robotocore"]
private_identifiers = set()

class_re = re.compile(r'\bclass\s+(_[a-zA-Z0-9_]+)\b')
def_re = re.compile(r'\bdef\s+(_[a-zA-Z0-9_]+)\b')
self_attr_re = re.compile(r'\bself\.(_[a-zA-Z0-9_]+)\b')

for d in directories:
    for root, _, files in os.walk(d):
        for f in files:
            if f.endswith('.py'):
                path = os.path.join(root, f)
                with open(path, 'r', encoding='utf-8') as file:
                    content = file.read()
                    private_identifiers.update(class_re.findall(content))
                    private_identifiers.update(def_re.findall(content))
                    private_identifiers.update(self_attr_re.findall(content))

to_rename = set()
for ident in private_identifiers:
    if ident.startswith('__'):
        continue
    if ident in ['_e', '_event', '_']:
        continue
    to_rename.add(ident)

# Sort descending by length to avoid any partial matches (even though \b protects us)
to_rename = sorted(list(to_rename), key=len, reverse=True)

for d in directories:
    for root, _, files in os.walk(d):
        for f in files:
            if f.endswith('.py'):
                path = os.path.join(root, f)
                with open(path, 'r', encoding='utf-8') as file:
                    content = file.read()
                
                new_content = content
                for ident in to_rename:
                    new_ident = ident[1:] # remove leading underscore
                    # Use a regex that replaces \b_ident\b with new_ident
                    pattern = r'\b' + re.escape(ident) + r'\b'
                    new_content = re.sub(pattern, new_ident, new_content)
                
                if new_content != content:
                    with open(path, 'w', encoding='utf-8', newline='') as file:
                        file.write(new_content)
                    print(f"Updated {path}")
