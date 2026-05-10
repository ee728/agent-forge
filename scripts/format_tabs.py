import os
import glob


def convert_to_tabs(text):
	lines = text.splitlines(keepends=True)
	result = []
	for line in lines:
		stripped = line.lstrip()
		leading = line[:len(line) - len(stripped)]
		if leading and all(c == ' ' for c in leading):
			spaces = len(leading)
			tabs = spaces // 4
			remaining = spaces % 4
			line = '\t' * tabs + ' ' * remaining + stripped
		result.append(line)
	return ''.join(result)


def main():
	root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
	for dirpath, dirnames, filenames in os.walk(root):
		parts = dirpath.split(os.sep)
		if '.git' in parts or '__pycache__' in parts:
			continue
		for f in filenames:
			if not f.endswith('.py'):
				continue
			path = os.path.join(dirpath, f)
			with open(path, 'r') as fh:
				original = fh.read()
			converted = convert_to_tabs(original)
			if converted != original:
				with open(path, 'w') as fh:
					fh.write(converted)
				print(f"  formatted: {os.path.relpath(path, root)}")


if __name__ == '__main__':
	main()
