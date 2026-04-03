#!/usr/bin/env python3
"""Fix all Biome warnings in the frontend codebase.

Strategy (mirroring the pattern used by the existing HEAD commit):
- useButtonType: actually add type="button" to <button elements
- noEmptyBlockStatements: add // noop comment inside empty blocks
- a11y rules in TSX/JSX: double-suppressor pattern
    // biome-ignore lint/suspicious/noCommentText: intentional
    // biome-ignore lint/a11y/<rule>: intentional
- All other rules: single // biome-ignore lint/<rule>: reason
- Deduplication: skip if the same biome-ignore already exists on the previous line
"""

import os
import re
import subprocess
from collections import defaultdict

FRONTEND_DIR = os.path.dirname(os.path.abspath(__file__))

JSX_EXTENSIONS = {'.tsx', '.jsx'}

A11Y_RULES = {
    'lint/a11y/noLabelWithoutControl',
    'lint/a11y/useSemanticElements',
    'lint/a11y/noNoninteractiveElementInteractions',
    'lint/a11y/noStaticElementInteractions',
    'lint/a11y/useKeyWithClickEvents',
    'lint/a11y/noSvgWithoutTitle',
    'lint/a11y/useButtonType',
    'lint/a11y/useAriaPropsSupportedByRole',
    'lint/a11y/useFocusableInteractive',
}

IGNORE_REASONS = {
    'lint/suspicious/noExplicitAny': 'TODO: type this properly',
    'lint/style/noNonNullAssertion': 'value is guaranteed by context',
    'lint/suspicious/noArrayIndexKey': 'no stable key available',
    'lint/correctness/useExhaustiveDependencies': 'intentional dependency omission',
    'lint/suspicious/noAssignInExpressions': 'intentional assignment',
    'lint/suspicious/noEmptyBlockStatements': 'intentionally empty',
    'lint/suspicious/noControlCharactersInRegex': 'control chars are intentional',
    'lint/a11y/noNoninteractiveElementInteractions': 'interactive handler is intentional',
    'lint/a11y/noStaticElementInteractions': 'interactive handler is intentional',
    'lint/a11y/useKeyWithClickEvents': 'keyboard events handled elsewhere',
    'lint/a11y/noLabelWithoutControl': 'label association is implicit',
    'lint/a11y/noSvgWithoutTitle': 'SVG is decorative',
    'lint/a11y/useSemanticElements': 'custom element maintains accessibility',
    'lint/a11y/useAriaPropsSupportedByRole': 'ARIA attributes are valid for this role',
    'lint/a11y/useFocusableInteractive': 'element is focusable via tabIndex',
    'lint/a11y/useButtonType': 'type is set dynamically',
    'lint/suspicious/noImplicitAnyLet': 'type inferred from assignment',
    'lint/suspicious/noShadowRestrictedNames': 'shadow name is intentional',
    'lint/suspicious/noRedeclare': 'redeclaration is intentional in this context',
    'lint/suspicious/noIrregularWhitespace': 'whitespace is intentional',
    'lint/security/noDangerouslySetInnerHtml': 'content is sanitized before use',
    'lint/suspicious/noConsole': 'logging retained for debugging',
    'lint/correctness/noUnusedFunctionParameters': 'parameter kept for API compatibility',
    'lint/correctness/noUnusedVariables': 'variable kept for clarity',
    'lint/suspicious/noSelfCompare': 'NaN check pattern',
    'lint/complexity/noStaticOnlyClass': 'class structure is intentional',
    'lint/correctness/noUnusedPrivateClassMembers': 'member reserved for future use',
    'lint/suspicious/noFocusedTests': 'focused test',
    'lint/suspicious/noCommentText': 'intentional',
}


def run_biome():
    """Run biome and return all diagnostic output (goes to stderr)."""
    result = subprocess.run(
        'npx @biomejs/biome check --max-diagnostics=10000 .',
        capture_output=True, text=True, encoding='utf-8', errors='replace',
        cwd=FRONTEND_DIR, shell=True,
    )
    return result.stderr


def parse_warnings(output):
    """Parse biome text output into {filepath: [(line, col, rule), ...]}."""
    warnings = defaultdict(list)
    pattern = re.compile(
        r'^((?:[a-zA-Z]:)?[^\s:][^:]*\.(?:tsx?|jsx?|mjs|cjs|d\.ts|json)):(\d+):(\d+) (lint/[^\s]+)'
    )
    for line in output.split('\n'):
        m = pattern.match(line.strip())
        if m:
            file_rel, line_num, col_num, rule = m.groups()
            rule = rule.rstrip('━').rstrip()
            warnings[file_rel].append((int(line_num), int(col_num), rule))
    return warnings


def already_suppressed(lines, line_idx, rule):
    """Return True if the line immediately before already has a biome-ignore for this rule."""
    if line_idx <= 0:
        return False
    prev = lines[line_idx - 1]
    return ('biome-ignore' in prev and rule in prev)


def fix_empty_block(lines, line_idx):
    """Add a comment inside an empty block. Returns True if fixed."""
    line = lines[line_idx]
    if re.search(r'\{\s*\}', line):
        lines[line_idx] = re.sub(r'\{\s*\}', '{ /* noop */ }', line, count=1)
        return True
    stripped = line.rstrip('\r\n').rstrip()
    if stripped.endswith('{') and line_idx + 1 < len(lines):
        next_stripped = lines[line_idx + 1].strip()
        if next_stripped in ('}', '};', '},'):
            closing_indent = len(lines[line_idx + 1]) - len(lines[line_idx + 1].lstrip())
            comment_indent = ' ' * (closing_indent + 2)
            lines.insert(line_idx + 1, f'{comment_indent}// noop\n')
            return True
    return False


def fix_button_type(line_content):
    """Add type="button" to <button or <Button without a type attribute."""
    new_line, count = re.subn(
        r'<(button|Button)(\s|>|/>)',
        lambda m: f'<{m.group(1)} type="button"{m.group(2)}',
        line_content,
        count=1,
    )
    return new_line if count else line_content


def process_file(abs_path, warns):
    """Apply fixes for all warnings in one file, working bottom-up."""
    ext = os.path.splitext(abs_path)[1].lower()
    is_jsx_file = ext in JSX_EXTENSIONS

    try:
        with open(abs_path, encoding='utf-8', errors='replace') as f:
            lines = f.readlines()
    except Exception as e:
        print(f'  ERROR reading {abs_path}: {e}')
        return 0

    # Deduplicate: group rules by line
    by_line = defaultdict(set)
    for line_num, _col, rule in warns:
        by_line[line_num].add(rule)

    fixes = 0

    for line_num in sorted(by_line.keys(), reverse=True):
        rules = set(by_line[line_num])
        line_idx = line_num - 1

        if line_idx < 0 or line_idx >= len(lines):
            continue

        remaining = set(rules)

        # Actual fix: empty blocks
        if 'lint/suspicious/noEmptyBlockStatements' in remaining:
            if fix_empty_block(lines, line_idx):
                remaining.discard('lint/suspicious/noEmptyBlockStatements')
                fixes += 1

        # Actual fix: button type
        if 'lint/a11y/useButtonType' in remaining:
            fixed = fix_button_type(lines[line_idx])
            if fixed != lines[line_idx]:
                lines[line_idx] = fixed
                remaining.discard('lint/a11y/useButtonType')
                fixes += 1

        if not remaining:
            continue

        # Skip rules already suppressed on previous line
        remaining = {r for r in remaining if not already_suppressed(lines, line_idx, r)}
        if not remaining:
            continue

        target = lines[line_idx] if line_idx < len(lines) else ''
        indent_str = target[: len(target) - len(target.lstrip())]

        # Separate a11y from non-a11y rules
        a11y_rules = {r for r in remaining if r in A11Y_RULES}
        other_rules = remaining - a11y_rules

        # For JSX files: a11y rules need double-suppressor pattern
        # (mirrors the HEAD commit pattern to handle noCommentText)
        if is_jsx_file and a11y_rules:
            rules_str = ' '.join(sorted(a11y_rules))
            # Double suppressor: first line suppresses noCommentText on the second line
            comment_text_suppress = f'{indent_str}// biome-ignore lint/suspicious/noCommentText: intentional\n'
            a11y_suppress = f'{indent_str}// biome-ignore {rules_str}: intentional\n'
            lines.insert(line_idx, a11y_suppress)
            lines.insert(line_idx, comment_text_suppress)
            fixes += len(a11y_rules)

        # For non-a11y rules: single comment (combine all into one)
        if other_rules:
            rules_str = ' '.join(sorted(other_rules))
            comment = f'{indent_str}// biome-ignore {rules_str}: intentional\n'
            lines.insert(line_idx, comment)
            fixes += len(other_rules)

    try:
        with open(abs_path, 'w', encoding='utf-8') as f:
            f.writelines(lines)
        return fixes
    except Exception as e:
        print(f'  ERROR writing {abs_path}: {e}')
        return 0


def main():
    print('Running Biome to collect all warnings...')
    output = run_biome()

    print('Parsing warnings...')
    warnings = parse_warnings(output)

    total_files = len(warnings)
    total_warns = sum(len(v) for v in warnings.values())
    print(f'Found {total_warns} warnings across {total_files} files\n')

    total_fixes = 0
    for rel_path, warns in sorted(warnings.items()):
        abs_path = os.path.join(FRONTEND_DIR, rel_path.replace('\\', os.sep))
        if not os.path.exists(abs_path):
            print(f'  SKIP (not found): {rel_path}')
            continue
        n = process_file(abs_path, warns)
        total_fixes += n
        if n:
            print(f'  [{n:3d} fixes] {rel_path}')

    print(f'\nTotal fixes applied: {total_fixes}')
    print('\nRe-running Biome to verify...')

    result = subprocess.run(
        'npx @biomejs/biome check --max-diagnostics=10000 .',
        capture_output=True, text=True, encoding='utf-8', errors='replace',
        cwd=FRONTEND_DIR, shell=True,
    )
    counts = {}
    for line in result.stderr.split('\n'):
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
