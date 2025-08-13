#!/usr/bin/env python3
"""
Add license headers to all source files in the Thinkube project.
Based on the formats defined in COPYRIGHT_HEADER.md

Copyright 2025 Alejandro Martínez Corriá and the Thinkube contributors
SPDX-License-Identifier: Apache-2.0
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Optional
import argparse
import re

# License headers for different file types
HEADERS = {
    'python': [
        '# Copyright 2025 Alejandro Martínez Corriá and the Thinkube contributors',
        '# SPDX-License-Identifier: Apache-2.0'
    ],
    'yaml': [
        '# Copyright 2025 Alejandro Martínez Corriá and the Thinkube contributors',
        '# SPDX-License-Identifier: Apache-2.0'
    ],
    'javascript': [
        '/*',
        ' * Copyright 2025 Alejandro Martínez Corriá and the Thinkube contributors',
        ' * SPDX-License-Identifier: Apache-2.0',
        ' */'
    ],
    'shell': [
        '# Copyright 2025 Alejandro Martínez Corriá and the Thinkube contributors',
        '# SPDX-License-Identifier: Apache-2.0'
    ],
    'dockerfile': [
        '# Copyright 2025 Alejandro Martínez Corriá and the Thinkube contributors',
        '# SPDX-License-Identifier: Apache-2.0'
    ],
    'rust': [
        '/*',
        ' * Copyright 2025 Alejandro Martínez Corriá and the Thinkube contributors',
        ' * SPDX-License-Identifier: Apache-2.0',
        ' */'
    ],
    'html': [
        '<!--',
        '  Copyright 2025 Alejandro Martínez Corriá and the Thinkube contributors',
        '  SPDX-License-Identifier: Apache-2.0',
        '-->'
    ]
}

# File extensions to file types mapping
EXTENSIONS = {
    '.py': 'python',
    '.yaml': 'yaml',
    '.yml': 'yaml',
    '.js': 'javascript',
    '.ts': 'javascript',
    '.jsx': 'javascript',
    '.tsx': 'javascript',
    '.vue': 'javascript',
    '.sh': 'shell',
    '.bash': 'shell',
    '.rs': 'rust',
    '.html': 'html',
    '.j2': 'yaml',  # Jinja2 templates usually YAML
    '.jinja': 'yaml',
    '.jinja2': 'yaml'
}

# Directories to skip
SKIP_DIRS = {
    '.git', 'node_modules', 'venv', 'dist', 'build', 'target',
    '__pycache__', '.pytest_cache', '.vscode', '.idea',
    'vendor', 'deps', '.terraform', 'coverage'
}

# Files to skip
SKIP_FILES = {
    'LICENSE', 'README.md', 'CHANGELOG.md', 'package-lock.json',
    'yarn.lock', 'Cargo.lock', 'poetry.lock', 'requirements.txt'
}


def has_copyright(content: str) -> bool:
    """Check if file already has a copyright header."""
    # Check for various copyright patterns
    patterns = [
        r'Copyright.*202\d',
        r'SPDX-License-Identifier',
        r'Licensed under the Apache License'
    ]
    
    # Check first 20 lines
    lines = content.split('\n')[:20]
    for line in lines:
        for pattern in patterns:
            if re.search(pattern, line, re.IGNORECASE):
                return True
    return False


def get_file_type(filepath: Path) -> Optional[str]:
    """Determine file type from extension or filename."""
    
    # Special cases for files without extensions
    if filepath.name == 'Dockerfile':
        return 'dockerfile'
    if filepath.name.startswith('Dockerfile.'):
        return 'dockerfile'
    
    # Check by extension
    ext = filepath.suffix.lower()
    return EXTENSIONS.get(ext)


def add_header_to_file(filepath: Path, file_type: str, dry_run: bool = False) -> bool:
    """Add license header to a file."""
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"  ⚠️  Error reading {filepath}: {e}")
        return False
    
    # Check if already has copyright
    if has_copyright(content):
        return False
    
    # Get appropriate header
    header_lines = HEADERS.get(file_type, [])
    if not header_lines:
        return False
    
    # Handle shebang for shell scripts and Python
    lines = content.split('\n')
    insert_pos = 0
    
    if lines and lines[0].startswith('#!'):
        # Preserve shebang
        insert_pos = 1
        header = '\n'.join([''] + header_lines + [''])
    else:
        header = '\n'.join(header_lines + ['', ''])
    
    # Build new content
    if insert_pos > 0:
        new_lines = lines[:insert_pos] + header.split('\n') + lines[insert_pos:]
        new_content = '\n'.join(new_lines)
    else:
        new_content = header + content
    
    if not dry_run:
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(new_content)
            return True
        except Exception as e:
            print(f"  ❌ Error writing {filepath}: {e}")
            return False
    
    return True


def process_directory(root_dir: Path, dry_run: bool = False, verbose: bool = False) -> Dict[str, int]:
    """Process all files in directory and add headers."""
    
    stats = {
        'processed': 0,
        'skipped': 0,
        'errors': 0,
        'already_has': 0
    }
    
    # Collect all files to process
    files_by_type: Dict[str, List[Path]] = {}
    
    for root, dirs, files in os.walk(root_dir):
        # Skip certain directories
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        
        root_path = Path(root)
        
        for filename in files:
            # Skip certain files
            if filename in SKIP_FILES:
                continue
            
            filepath = root_path / filename
            
            # Skip symlinks
            if filepath.is_symlink():
                continue
            
            file_type = get_file_type(filepath)
            if file_type:
                if file_type not in files_by_type:
                    files_by_type[file_type] = []
                files_by_type[file_type].append(filepath)
    
    # Process files by type
    for file_type, filepaths in sorted(files_by_type.items()):
        print(f"\n📝 Processing {len(filepaths)} {file_type} files...")
        
        for filepath in filepaths:
            rel_path = filepath.relative_to(root_dir)
            
            if verbose:
                print(f"  Processing: {rel_path}")
            
            result = add_header_to_file(filepath, file_type, dry_run)
            
            if result:
                stats['processed'] += 1
                if verbose:
                    print(f"    ✅ Added header")
            elif has_copyright(filepath.read_text(encoding='utf-8')):
                stats['already_has'] += 1
                if verbose:
                    print(f"    ⏭️  Already has copyright")
            else:
                stats['skipped'] += 1
    
    return stats


def main():
    """Main entry point."""
    
    parser = argparse.ArgumentParser(
        description='Add license headers to Thinkube source files'
    )
    parser.add_argument(
        'path',
        nargs='?',
        default='.',
        help='Path to process (default: current directory)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be done without making changes'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Show detailed progress'
    )
    
    args = parser.parse_args()
    
    root_dir = Path(args.path).resolve()
    
    if not root_dir.exists():
        print(f"❌ Error: Path {root_dir} does not exist")
        sys.exit(1)
    
    print(f"🚀 Adding license headers to files in: {root_dir}")
    
    if args.dry_run:
        print("🔍 DRY RUN MODE - No files will be modified")
    
    # Find project root (look for LICENSE file)
    project_root = root_dir
    while project_root.parent != project_root:
        if (project_root / 'LICENSE').exists():
            break
        project_root = project_root.parent
    
    if not (project_root / 'LICENSE').exists():
        print("⚠️  Warning: Could not find LICENSE file in project root")
        response = input("Continue anyway? (y/N): ")
        if response.lower() != 'y':
            sys.exit(0)
    
    # Process files
    stats = process_directory(root_dir, args.dry_run, args.verbose)
    
    # Print summary
    print("\n" + "=" * 50)
    print("📊 Summary:")
    print(f"  ✅ Headers added: {stats['processed']}")
    print(f"  ⏭️  Already had headers: {stats['already_has']}")
    print(f"  ⏩ Skipped: {stats['skipped']}")
    
    if stats['errors'] > 0:
        print(f"  ❌ Errors: {stats['errors']}")
    
    if args.dry_run:
        print("\n🔍 This was a dry run. No files were modified.")
        print("Run without --dry-run to apply changes.")
    else:
        print("\n✨ License headers have been added successfully!")
    
    # Return non-zero if there were errors
    sys.exit(1 if stats['errors'] > 0 else 0)


if __name__ == '__main__':
    main()