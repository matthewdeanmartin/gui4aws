import os
import re

directories = ["gui4aws", "tests", "tests_robotocore"]
private_identifiers = set()

# Regexes to find definitions
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

# Filter out dunders and known unused variables
to_rename = set()
for ident in private_identifiers:
    if ident.startswith('__'):
        continue
    if ident in ['_e', '_event', '_']:
        continue
    to_rename.add(ident)

print("Identifiers to rename:")
for ident in sorted(to_rename):
    print(ident)
