from services.personalities import get_system_prompt, BASE_SYSTEM_PROMPT

try:
    print("Attempting to format prompt...")
    prompt = get_system_prompt()
    print("Success!")
    print(prompt[:100])
except Exception as e:
    print("FAILED!")
    print(e)

print("-" * 20)
print("BASE PROMPT START:")
# print first 500 chars raw
print(repr(BASE_SYSTEM_PROMPT[:500]))
print("-" * 20)
print("Looking for open braces:")
lines = BASE_SYSTEM_PROMPT.split('\n')
for i, line in enumerate(lines):
    if '{' in line:
        print(f"Line {i+1}: {repr(line)}")
