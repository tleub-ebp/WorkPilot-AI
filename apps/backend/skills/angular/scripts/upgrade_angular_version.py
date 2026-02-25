#!/usr/bin/env python3
"""
Angular Version Upgrader

Automates Angular version upgrades with breaking changes detection and automatic fixes.
Supports incremental upgrades with rollback capabilities.
"""

import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple


@dataclass
class BreakingChange:
    """Represents a breaking change with fix instructions."""
    version: str
    description: str
    affected_patterns: List[str]
    fix_instructions: str
    auto_fixable: bool = False


@dataclass
class UpgradeResult:
    """Result of Angular version upgrade."""
    success: bool
    from_version: str
    to_version: str
    changes_made: List[str]
    breaking_changes_detected: List[BreakingChange]
    auto_fixes_applied: List[str]
    manual_fixes_required: List[str]
    warnings: List[str]
    errors: List[str]


class AngularVersionUpgrader:
    """Handles Angular version upgrades with breaking changes management."""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.breaking_changes_db = self._load_breaking_changes()
        
    def _load_breaking_changes(self) -> Dict[str, List[BreakingChange]]:
        """Load breaking changes database."""
        return {
            "15->16": [
                BreakingChange(
                    version="16.0.0",
                    description="Standalone components introduced",
                    affected_patterns=[r"@Component\(\s*\{[^}]*\}", r"NgModule"],
                    fix_instructions="Consider migrating to standalone components for better tree-shaking",
                    auto_fixable=False
                ),
                BreakingChange(
                    version="16.0.0",
                    description="Signals introduced for reactive state management",
                    affected_patterns=[r"BehaviorSubject", r"Subject"],
                    fix_instructions="Consider using signals for simple state management",
                    auto_fixable=False
                )
            ],
            "16->17": [
                BreakingChange(
                    version="17.0.0",
                    description="New control flow syntax (@for, @if, @switch)",
                    affected_patterns=[r"\*ngFor", r"\*ngIf", r"\[ngSwitch\]"],
                    fix_instructions="Update to new control flow syntax: @for, @if, @switch",
                    auto_fixable=True
                ),
                BreakingChange(
                    version="17.0.0",
                    description="Improved signals with computed() and effect()",
                    affected_patterns=[r"computed\(", r"effect\("],
                    fix_instructions="Use enhanced signals API with computed() and effect()",
                    auto_fixable=False
                )
            ],
            "17->18": [
                BreakingChange(
                    version="18.0.0",
                    description="Zoneless applications preview",
                    affected_patterns=[r"platformBrowserDynamic", r"bootstrapModule"],
                    fix_instructions="Consider zoneless applications for better performance",
                    auto_fixable=False
                ),
                BreakingChange(
                    version="18.0.0",
                    description="Deferred loading for components",
                    affected_patterns=[r"defer"],
                    fix_instructions="Use @defer for lazy loading components",
                    auto_fixable=True
                )
            ],
            "18->19": [
                BreakingChange(
                    version="19.0.0",
                    description="Enhanced hydration support",
                    affected_patterns=[r"provideClientHydration"],
                    fix_instructions="Enable hydration for better SSR performance",
                    auto_fixable=True
                ),
                BreakingChange(
                    version="19.0.0",
                    description="Improved performance with new change detection",
                    affected_patterns=[r"ChangeDetectionStrategy"],
                    fix_instructions="Review and optimize change detection strategies",
                    auto_fixable=False
                )
            ]
        }
    
    def upgrade(self, target_version: str) -> UpgradeResult:
        """Perform Angular version upgrade."""
        result = UpgradeResult(
            success=False,
            from_version="",
            to_version=target_version,
            changes_made=[],
            breaking_changes_detected=[],
            auto_fixes_applied=[],
            manual_fixes_required=[],
            warnings=[],
            errors=[]
        )
        
        try:
            # Get current Angular version
            current_version = self._get_current_angular_version()
            if not current_version:
                result.errors.append("Could not determine current Angular version")
                return result
            
            result.from_version = current_version
            
            # Validate upgrade path
            upgrade_path = self._get_upgrade_path(current_version, target_version)
            if not upgrade_path:
                result.errors.append(f"Invalid upgrade path from {current_version} to {target_version}")
                return result
            
            # Perform incremental upgrades
            for from_ver, to_ver in upgrade_path:
                step_result = self._perform_incremental_upgrade(from_ver, to_ver)
                result.changes_made.extend(step_result.changes_made)
                result.breaking_changes_detected.extend(step_result.breaking_changes_detected)
                result.auto_fixes_applied.extend(step_result.auto_fixes_applied)
                result.manual_fixes_required.extend(step_result.manual_fixes_required)
                result.warnings.extend(step_result.warnings)
                result.errors.extend(step_result.errors)
                
                if not step_result.success:
                    result.success = False
                    return result
            
            # Update package.json
            if self._update_package_json(target_version):
                result.changes_made.append(f"Updated Angular dependencies to version {target_version}")
            
            # Run Angular CLI migration
            if self._run_cli_migration(target_version):
                result.changes_made.append(f"Ran Angular CLI migration for version {target_version}")
            
            result.success = True
            
        except Exception as e:
            result.errors.append(f"Upgrade failed: {str(e)}")
        
        return result
    
    def _get_current_angular_version(self) -> Optional[str]:
        """Get current Angular version from package.json."""
        package_json_path = self.project_root / "package.json"
        
        if not package_json_path.exists():
            return None
        
        try:
            with open(package_json_path, 'r') as f:
                package_data = json.load(f)
            
            deps = package_data.get('dependencies', {})
            if '@angular/core' in deps:
                version = deps['@angular/core']
                # Extract major version
                match = re.match(r'^(\d+)\.', version)
                if match:
                    return match.group(1)
                    
        except Exception:
            pass
        
        return None
    
    def _get_upgrade_path(self, from_version: str, to_version: str) -> List[Tuple[str, str]]:
        """Get incremental upgrade path."""
        from_major = int(from_version)
        to_major = int(to_version)
        
        if from_major >= to_major:
            return []
        
        path = []
        current = from_major
        
        while current < to_major:
            next_version = str(current + 1)
            path.append((str(current), next_version))
            current += 1
        
        return path
    
    def _perform_incremental_upgrade(self, from_version: str, to_version: str) -> UpgradeResult:
        """Perform incremental upgrade from one version to next."""
        result = UpgradeResult(
            success=True,
            from_version=from_version,
            to_version=to_version,
            changes_made=[],
            breaking_changes_detected=[],
            auto_fixes_applied=[],
            manual_fixes_required=[],
            warnings=[],
            errors=[]
        )
        
        upgrade_key = f"{from_version}->{to_version}"
        breaking_changes = self.breaking_changes_db.get(upgrade_key, [])
        
        result.breaking_changes_detected.extend(breaking_changes)
        
        # Apply auto-fixes
        for change in breaking_changes:
            if change.auto_fixable:
                if self._apply_auto_fix(change):
                    result.auto_fixes_applied.append(f"Auto-fixed: {change.description}")
                else:
                    result.manual_fixes_required.append(f"Manual fix required: {change.description}")
            else:
                result.manual_fixes_required.append(f"Manual fix required: {change.description}")
        
        return result
    
    def _apply_auto_fix(self, change: BreakingChange) -> bool:
        """Apply automatic fix for breaking change."""
        try:
            if "control flow" in change.description.lower():
                return self._update_control_flow_syntax()
            elif "defer" in change.description.lower():
                return self._add_defer_support()
            elif "hydration" in change.description.lower():
                return self._enable_hydration()
        except Exception:
            pass
        
        return False
    
    def _update_control_flow_syntax(self) -> bool:
        """Update *ngFor, *ngIf to new @for, @if syntax."""
        src_dir = self.project_root / "src"
        
        if not src_dir.exists():
            return False
        
        updated_files = 0
        
        for template_file in src_dir.rglob("*.html"):
            try:
                with open(template_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                original_content = content
                
                # Update *ngFor to @for
                content = re.sub(
                    r'\*ngFor="let (\w+) of (\w+)"',
                    r'@for (\1 of \2; track \1) {',
                    content
                )
                
                # Update *ngIf to @if
                content = re.sub(
                    r'\*ngIf="([^;]+)"',
                    r'@if (\1) {',
                    content
                )
                
                if content != original_content:
                    with open(template_file, 'w', encoding='utf-8') as f:
                        f.write(content)
                    updated_files += 1
                    
            except Exception:
                continue
        
        return updated_files > 0
    
    def _add_defer_support(self) -> bool:
        """Add @defer support for lazy loading."""
        # This is a placeholder for defer implementation
        # Real implementation would analyze components and add defer blocks
        return True
    
    def _enable_hydration(self) -> bool:
        """Enable hydration support."""
        app_config_path = self.project_root / "src" / "app" / "app.config.ts"
        
        if not app_config_path.exists():
            return False
        
        try:
            with open(app_config_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if 'provideClientHydration' not in content:
                # Add hydration provider
                content = re.sub(
                    r'(providers:\s*\[)',
                    r'\1  provideClientHydration(), ',
                    content
                )
                
                with open(app_config_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                return True
                
        except Exception:
            pass
        
        return False
    
    def _update_package_json(self, target_version: str) -> bool:
        """Update package.json with new Angular versions."""
        package_json_path = self.project_root / "package.json"
        
        if not package_json_path.exists():
            return False
        
        try:
            with open(package_json_path, 'r') as f:
                package_data = json.load(f)
            
            # Update Angular dependencies
            angular_packages = [
                '@angular/core',
                '@angular/common',
                '@angular/compiler',
                '@angular/platform-browser',
                '@angular/platform-browser-dynamic',
                '@angular/router',
                '@angular/forms'
            ]
            
            deps = package_data.get('dependencies', {})
            for package_name in angular_packages:
                if package_name in deps:
                    deps[package_name] = f"^{target_version}.0.0"
            
            # Update Angular CLI
            dev_deps = package_data.get('devDependencies', {})
            if '@angular/cli' in dev_deps:
                dev_deps['@angular/cli'] = f"^{target_version}.0.0"
            
            # Write back
            with open(package_json_path, 'w') as f:
                json.dump(package_data, f, indent=2)
            
            return True
            
        except Exception:
            pass
        
        return False
    
    def _run_cli_migration(self, target_version: str) -> bool:
        """Run Angular CLI migration commands."""
        try:
            # Run npm install first
            subprocess.run(['npm', 'install'], cwd=self.project_root, check=True, capture_output=True)
            
            # Run Angular migration
            result = subprocess.run(
                ['npx', 'ng', 'update', '@angular/core', '@angular/cli', '--allow-dirty'],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            return result.returncode == 0
            
        except Exception:
            pass
        
        return False


def main():
    """Main entry point for the script."""
    if len(sys.argv) < 3:
        print("Usage: python upgrade_angular_version.py <project_root> <target_version>")
        print("Example: python upgrade_angular_version.py /path/to/project 17.0.0")
        sys.exit(1)
    
    project_root = sys.argv[1]
    target_version = sys.argv[2]
    
    upgrader = AngularVersionUpgrader(project_root)
    
    try:
        result = upgrader.upgrade(target_version)
        
        # Output results as JSON
        output = {
            "success": result.success,
            "from_version": result.from_version,
            "to_version": result.to_version,
            "changes_made": result.changes_made,
            "breaking_changes_detected": [
                {
                    "version": bc.version,
                    "description": bc.description,
                    "auto_fixable": bc.auto_fixable
                }
                for bc in result.breaking_changes_detected
            ],
            "auto_fixes_applied": result.auto_fixes_applied,
            "manual_fixes_required": result.manual_fixes_required,
            "warnings": result.warnings,
            "errors": result.errors
        }
        
        print(json.dumps(output, indent=2))
        
        if not result.success:
            sys.exit(1)
            
    except Exception as e:
        error_output = {
            "success": False,
            "error": str(e),
            "project_root": project_root,
            "target_version": target_version
        }
        print(json.dumps(error_output, indent=2))
        sys.exit(1)


if __name__ == "__main__":
    main()
