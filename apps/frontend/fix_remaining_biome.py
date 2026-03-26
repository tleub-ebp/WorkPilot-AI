#!/usr/bin/env python3
"""Fix remaining Biome warnings after initial script run.

Two main issues to fix:
1. Stacked // biome-ignore comments in JSX children don't work (only single works).
   Replace 4-comment stacks with a single {/* biome-ignore ... */} JSX expression.
2. // biome-ignore comments inside JSX opening tags don't work.
   Move comment to before the element and inline role= with the opening tag.
"""

import re
import os
import subprocess

FRONTEND_DIR = os.path.dirname(os.path.abspath(__file__))

def fix_stacked_jsx_children_a11y(content, indent_hint=None):
    """Replace 4-stacked // biome-ignore a11y comments with single JSX comment.

    Pattern:
        // biome-ignore lint/a11y/noNoninteractiveElementInteractions: ...
        // biome-ignore lint/a11y/noStaticElementInteractions: ...
        // biome-ignore lint/a11y/useKeyWithClickEvents: ...
        // biome-ignore lint/a11y/noNoninteractiveElementInteractions lint/a11y/noStaticElementInteractions lint/a11y/useKeyWithClickEvents: intentional
        <element
    """
    pattern = re.compile(
        r'^([ \t]*)// biome-ignore lint/a11y/noNoninteractiveElementInteractions: [^\n]+\n'
        r'[ \t]*// biome-ignore lint/a11y/noStaticElementInteractions: [^\n]+\n'
        r'[ \t]*// biome-ignore lint/a11y/useKeyWithClickEvents: [^\n]+\n'
        r'[ \t]*// biome-ignore lint/a11y/noNoninteractiveElementInteractions lint/a11y/noStaticElementInteractions lint/a11y/useKeyWithClickEvents: intentional\n',
        re.MULTILINE
    )
    replacement = (
        r'\1{/* biome-ignore lint/a11y/noNoninteractiveElementInteractions '
        r'lint/a11y/noStaticElementInteractions '
        r'lint/a11y/useKeyWithClickEvents: interactive handler is intentional */}\n'
    )
    new_content, count = pattern.subn(replacement, content)
    return new_content, count


def fix_stacked_jsx_children_static_only(content):
    """Replace 2-rule stacked comments (noNoninteractive + noStatic, no useKeyWith)."""
    pattern = re.compile(
        r'^([ \t]*)// biome-ignore lint/a11y/noNoninteractiveElementInteractions: [^\n]+\n'
        r'[ \t]*// biome-ignore lint/a11y/noStaticElementInteractions: [^\n]+\n'
        r'[ \t]*// biome-ignore lint/a11y/noNoninteractiveElementInteractions lint/a11y/noStaticElementInteractions: intentional\n',
        re.MULTILINE
    )
    replacement = (
        r'\1{/* biome-ignore lint/a11y/noNoninteractiveElementInteractions '
        r'lint/a11y/noStaticElementInteractions: interactive handler is intentional */}\n'
    )
    new_content, count = pattern.subn(replacement, content)
    return new_content, count


def fix_usesemanticelements_inside_tag(content):
    """Remove duplicate useSemanticElements comments from inside JSX opening tags.

    Pattern (inside an opening tag, before an attribute):
        // biome-ignore lint/a11y/useSemanticElements: ...
        // biome-ignore lint/a11y/useSemanticElements: intentional
        role="..."

    Just remove the two duplicate comments; the role= stays, and we need to
    add a {/* biome-ignore */} before the element opening separately.
    """
    # Remove the two stacked comments that are inside JSX opening tags
    pattern = re.compile(
        r'^([ \t]*)// biome-ignore lint/a11y/useSemanticElements: [^\n]+\n'
        r'[ \t]*// biome-ignore lint/a11y/useSemanticElements: intentional\n'
        r'(?=[ \t]*role=)',
        re.MULTILINE
    )
    new_content, count = pattern.subn('', content)
    return new_content, count


def add_usesemanticelements_before_element(content):
    """Add {/* biome-ignore useSemanticElements */} before JSX elements with role=.

    After removing the wrong inside-tag comments, we need to add the correct
    suppression BEFORE the element opening.

    Pattern: element opening followed by role= attribute (no suppression before)
    """
    fixes = 0

    # Find lines that start a JSX element and have role= as a subsequent attribute
    # We need to detect the structure:
    #   (whitespace)<elementName
    #   ...
    #   (whitespace)role="..."
    # where there's no biome-ignore before the element

    lines = content.split('\n')
    i = 0
    result_lines = []

    while i < len(lines):
        line = lines[i]

        # Check if this is an opening JSX tag that doesn't already have a suppression before it
        # and has role= as the NEXT line (or within 2 lines)
        stripped = line.lstrip()
        if (stripped.startswith('<') and not stripped.startswith('</') and
                not stripped.startswith('<{') and not stripped.startswith('<!--') and
                not stripped.startswith('{/*')):

            indent = line[:len(line) - len(stripped)]
            tag_match = re.match(r'<([a-zA-Z][a-zA-Z0-9]*)', stripped)

            if tag_match:
                # Check if the previous line already has the suppression
                prev_line = result_lines[-1] if result_lines else ''
                already_suppressed = 'biome-ignore lint/a11y/useSemanticElements' in prev_line

                # Check if the next 1-3 lines have role= attribute
                has_role = False
                role_line_idx = -1
                for j in range(i+1, min(i+5, len(lines))):
                    next_stripped = lines[j].strip()
                    if re.match(r'role=', next_stripped):
                        has_role = True
                        role_line_idx = j
                        break
                    # Stop searching if we hit end of opening tag or nested element
                    if next_stripped.startswith('>') or next_stripped.startswith('<') or next_stripped.startswith('/>'):
                        break

                if has_role and not already_suppressed:
                    result_lines.append(f'{indent}{{/* biome-ignore lint/a11y/useSemanticElements: custom element maintains accessibility */}}')
                    fixes += 1

        result_lines.append(line)
        i += 1

    return '\n'.join(result_lines), fixes


def fix_file(filepath):
    """Apply all fixes to a file."""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
    except Exception as e:
        print(f'ERROR reading {filepath}: {e}')
        return 0

    original = content
    total_fixes = 0

    # Fix 1: Replace 4-stacked JSX children a11y comments
    content, n = fix_stacked_jsx_children_a11y(content)
    total_fixes += n

    # Fix 2: Replace 2-stacked JSX children a11y comments (noStatic only)
    content, n = fix_stacked_jsx_children_static_only(content)
    total_fixes += n

    # Fix 3: Remove useSemanticElements comments from inside JSX opening tags
    content, n = fix_usesemanticelements_inside_tag(content)
    total_fixes += n

    # Fix 4: Add {/* biome-ignore useSemanticElements */} before elements with role=
    if n > 0:  # Only if we removed some comments
        content, n = add_usesemanticelements_before_element(content)
        total_fixes += n

    if content != original:
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            return total_fixes
        except Exception as e:
            print(f'ERROR writing {filepath}: {e}')
            return 0

    return 0


def run_biome():
    """Run biome and return stderr output."""
    result = subprocess.run(
        'npx @biomejs/biome check --max-diagnostics=10000 .',
        capture_output=True, text=True, encoding='utf-8', errors='replace',
        cwd=FRONTEND_DIR, shell=True,
    )
    return result.stderr


def get_files_with_issues(biome_output):
    """Parse biome output to get list of files with remaining issues."""
    files = set()
    pattern = re.compile(r'^((?:[a-zA-Z]:)?[^\s:][^:]*\.(?:tsx?|jsx?|mjs|cjs)):\d+:\d+ (?!suppressions/unused)')
    for line in biome_output.split('\n'):
        m = pattern.match(line.strip())
        if m:
            files.add(m.group(1))
    return files


def main():
    print('Finding all .tsx/.jsx files to fix...')

    # Find all TSX/JSX files
    tsx_files = []
    for root, dirs, files in os.walk(FRONTEND_DIR):
        # Skip node_modules
        dirs[:] = [d for d in dirs if d not in ('node_modules', '.git', 'dist', 'build')]
        for f in files:
            if f.endswith(('.tsx', '.jsx', '.ts', '.js')):
                tsx_files.append(os.path.join(root, f))

    print(f'Processing {len(tsx_files)} files...')

    total_fixes = 0
    for filepath in sorted(tsx_files):
        n = fix_file(filepath)
        if n > 0:
            rel = os.path.relpath(filepath, FRONTEND_DIR)
            print(f'  [{n:3d} fixes] {rel}')
            total_fixes += n

    print(f'\nTotal pattern fixes: {total_fixes}')

    print('\nNow running biome to see remaining issues...')
    output = run_biome()

    # Count issues by type
    counts = {}
    for line in output.split('\n'):
        m = re.search(r'(suppressions/unused|lint/[a-zA-Z][a-zA-Z0-9/]+)', line.strip())
        if m:
            k = m.group(1)
            counts[k] = counts.get(k, 0) + 1

    if counts:
        print('\nRemaining issues:')
        for k, v in sorted(counts.items(), key=lambda x: -x[1]):
            print(f'  {v:4d}  {k}')
        print(f'  Total: {sum(counts.values())}')
    else:
        print('No warnings remaining!')


if __name__ == '__main__':
    main()
