#!/usr/bin/env python3
"""
Versioned Skills Management System

Manages multiple versions of skills with compatibility checking,
automatic version selection, and migration support.

Features:
- Semantic versioning support
- Compatibility matrix management
- Automatic version selection
- Version migration and rollback
- Dependency version resolution
- Version lifecycle management
"""

import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Any, Tuple
from enum import Enum
import time

logger = logging.getLogger(__name__)


class VersionCompatibility(Enum):
    """Version compatibility levels."""
    COMPATIBLE = "compatible"
    INCOMPATIBLE = "incompatible"
    UNKNOWN = "unknown"
    DEPRECATED = "deprecated"


@dataclass
class SkillVersion:
    """Represents a specific version of a skill."""
    version: str
    skill_path: Path
    metadata: Dict[str, Any]
    compatibility_matrix: Dict[str, VersionCompatibility] = field(default_factory=dict)
    dependencies: Dict[str, str] = field(default_factory=dict)  # skill_name -> version
    deprecated: bool = False
    created_at: float = field(default_factory=time.time)
    last_modified: float = field(default_factory=time.time)
    
    def __post_init__(self):
        # Parse version for comparison
        self.version_tuple = self._parse_version(self.version)
    
    def _parse_version(self, version: str) -> Tuple[int, int, int]:
        """Parse semantic version string."""
        # Remove 'v' prefix if present
        version = version.lstrip('v')
        
        # Extract version numbers
        match = re.match(r'^(\d+)\.(\d+)\.(\d+)', version)
        if match:
            return tuple(map(int, match.groups()))
        
        # Handle pre-release versions
        match = re.match(r'^(\d+)\.(\d+)', version)
        if match:
            return (int(match.group(1)), int(match.group(2)), 0)
        
        # Default to 0.0.0 for invalid versions
        return (0, 0, 0)
    
    def is_compatible_with(self, other_version: str) -> bool:
        """Check if this version is compatible with another version."""
        compatibility = self.compatibility_matrix.get(other_version, VersionCompatibility.UNKNOWN)
        return compatibility == VersionCompatibility.COMPATIBLE
    
    def is_newer_than(self, other_version: str) -> bool:
        """Check if this version is newer than another version."""
        other_tuple = SkillVersion(other_version, Path(""), {})._parse_version(other_version)
        return self.version_tuple > other_tuple
    
    def get_major_version(self) -> int:
        """Get major version number."""
        return self.version_tuple[0]
    
    def get_minor_version(self) -> int:
        """Get minor version number."""
        return self.version_tuple[1]
    
    def get_patch_version(self) -> int:
        """Get patch version number."""
        return self.version_tuple[2]


@dataclass
class VersionMigration:
    """Represents a migration between skill versions."""
    from_version: str
    to_version: str
    migration_script: Optional[str] = None
    auto_migrate: bool = False
    breaking_changes: List[str] = field(default_factory=list)
    migration_steps: List[str] = field(default_factory=list)
    
    def execute_migration(self, skill_path: Path) -> bool:
        """Execute the migration."""
        if not self.migration_script:
            logger.warning(f"No migration script available for {self.from_version} -> {self.to_version}")
            return False
        
        try:
            # In a real implementation, this would execute the migration script
            logger.info(f"Executing migration {self.from_version} -> {self.to_version}")
            return True
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            return False


class VersionedSkillManager:
    """Manages versioned skills with compatibility and migration."""
    
    def __init__(self, skills_dir: str = "skills"):
        self.skills_dir = Path(skills_dir)
        self.skill_versions: Dict[str, Dict[str, SkillVersion]] = {}  # skill_name -> version -> SkillVersion
        self.active_versions: Dict[str, str] = {}  # skill_name -> active_version
        self.migrations: Dict[str, List[VersionMigration]] = {}  # skill_name -> migrations
        self.compatibility_cache: Dict[str, Dict[str, VersionCompatibility]] = {}
        
        # Load existing skills
        self._load_versioned_skills()
        
        logger.info(f"Versioned skill manager initialized with {len(self.skill_versions)} skills")
    
    def _load_versioned_skills(self):
        """Load all versioned skills from directory."""
        for skill_dir in self.skills_dir.iterdir():
            if not skill_dir.is_dir():
                continue
            
            skill_name = skill_dir.name
            self.skill_versions[skill_name] = {}
            
            # Look for version subdirectories
            for version_dir in skill_dir.iterdir():
                if not version_dir.is_dir():
                    continue
                
                # Check if this looks like a version directory
                version_name = version_dir.name
                if self._is_valid_version(version_name):
                    self._load_skill_version(skill_name, version_name, version_dir)
            
            # Set active version (latest stable)
            if self.skill_versions[skill_name]:
                self.active_versions[skill_name] = self._select_active_version(skill_name)
    
    def _is_valid_version(self, version: str) -> bool:
        """Check if version string is valid."""
        # Accept semantic versions like "1.0.0", "v2.1.3", "1.2"
        return bool(re.match(r'^v?\d+(\.\d+)*', version))
    
    def _load_skill_version(self, skill_name: str, version: str, version_dir: Path):
        """Load a specific skill version."""
        skill_file = version_dir / "SKILL.md"
        if not skill_file.exists():
            logger.warning(f"SKILL.md not found for {skill_name} v{version}")
            return
        
        try:
            # Parse metadata
            metadata = self._parse_skill_metadata(skill_file)
            
            # Load compatibility matrix
            compatibility_file = version_dir / "compatibility.json"
            compatibility_matrix = {}
            if compatibility_file.exists():
                with open(compatibility_file, 'r') as f:
                    compat_data = json.load(f)
                    for other_version, compat_level in compat_data.items():
                        compatibility_matrix[other_version] = VersionCompatibility(compat_level)
            
            # Load dependencies
            deps_file = version_dir / "dependencies.json"
            dependencies = {}
            if deps_file.exists():
                with open(deps_file, 'r') as f:
                    dependencies = json.load(f)
            
            # Create skill version
            skill_version = SkillVersion(
                version=version,
                skill_path=version_dir,
                metadata=metadata,
                compatibility_matrix=compatibility_matrix,
                dependencies=dependencies
            )
            
            self.skill_versions[skill_name][version] = skill_version
            logger.debug(f"Loaded {skill_name} v{version}")
            
        except Exception as e:
            logger.error(f"Failed to load {skill_name} v{version}: {e}")
    
    def _parse_skill_metadata(self, skill_file: Path) -> Dict:
        """Parse metadata from SKILL.md file."""
        content = skill_file.read_text(encoding="utf-8")
        
        # Extract YAML frontmatter
        if content.startswith("---"):
            try:
                end_marker = content.find("---", 3)
                if end_marker != -1:
                    frontmatter = content[3:end_marker].strip()
                    metadata = {}
                    
                    for line in frontmatter.split("\n"):
                        if ":" in line:
                            key, value = line.split(":", 1)
                            key = key.strip()
                            value = value.strip()
                            
                            # Handle different field types
                            if key == "triggers":
                                value = value.strip("[]").split(",")
                                value = [t.strip().strip('"\'') for t in value if t.strip()]
                            elif key.startswith('"') and key.endswith('"'):
                                value = value.strip('"\'')
                            
                            metadata[key] = value
                    
                    return metadata
            except Exception as e:
                logger.warning(f"Error parsing frontmatter: {e}")
        
        # Fallback metadata
        return {
            'name': skill_file.parent.parent.name,
            'description': f'Skill version {skill_file.parent.name}',
            'triggers': []
        }
    
    def _select_active_version(self, skill_name: str) -> str:
        """Select the active version for a skill."""
        versions = self.skill_versions[skill_name]
        
        if not versions:
            return "1.0.0"
        
        # Sort versions and select the latest non-deprecated
        sorted_versions = sorted(
            versions.keys(),
            key=lambda v: versions[v].version_tuple,
            reverse=True
        )
        
        for version in sorted_versions:
            skill_version = versions[version]
            if not skill_version.deprecated:
                return version
        
        # Fallback to latest version even if deprecated
        return sorted_versions[0]
    
    def get_skill(self, skill_name: str, version: Optional[str] = None) -> Optional[SkillVersion]:
        """Get a skill version."""
        if skill_name not in self.skill_versions:
            return None
        
        if version is None:
            version = self.active_versions.get(skill_name)
        
        return self.skill_versions[skill_name].get(version)
    
    def get_latest_version(self, skill_name: str) -> Optional[str]:
        """Get the latest version of a skill."""
        if skill_name not in self.skill_versions:
            return None
        
        versions = self.skill_versions[skill_name]
        if not versions:
            return None
        
        return max(versions.keys(), key=lambda v: versions[v].version_tuple)
    
    def get_compatible_versions(self, skill_name: str, target_version: str) -> List[str]:
        """Get all versions compatible with target version."""
        skill = self.get_skill(skill_name, target_version)
        if not skill:
            return []
        
        compatible = []
        for version, skill_version in self.skill_versions[skill_name].items():
            if skill_version.is_compatible_with(target_version):
                compatible.append(version)
        
        return compatible
    
    def add_skill_version(self, skill_name: str, version: str, skill_path: Path,
                         compatibility_matrix: Optional[Dict[str, str]] = None,
                         dependencies: Optional[Dict[str, str]] = None) -> bool:
        """Add a new skill version."""
        try:
            # Parse compatibility matrix
            compat_matrix = {}
            if compatibility_matrix:
                for other_version, compat_level in compatibility_matrix.items():
                    compat_matrix[other_version] = VersionCompatibility(compat_level)
            
            # Parse metadata
            skill_file = skill_path / "SKILL.md"
            metadata = self._parse_skill_metadata(skill_file)
            
            # Create skill version
            skill_version = SkillVersion(
                version=version,
                skill_path=skill_path,
                metadata=metadata,
                compatibility_matrix=compat_matrix,
                dependencies=dependencies or {}
            )
            
            # Add to registry
            if skill_name not in self.skill_versions:
                self.skill_versions[skill_name] = {}
            
            self.skill_versions[skill_name][version] = skill_version
            
            # Update active version if this is newer
            current_active = self.active_versions.get(skill_name)
            if not current_active or skill_version.is_newer_than(current_active):
                self.active_versions[skill_name] = version
            
            logger.info(f"Added {skill_name} v{version}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add {skill_name} v{version}: {e}")
            return False
    
    def create_migration(self, skill_name: str, from_version: str, to_version: str,
                        migration_script: Optional[str] = None, auto_migrate: bool = False) -> bool:
        """Create a migration between versions."""
        if skill_name not in self.skill_versions:
            logger.error(f"Skill not found: {skill_name}")
            return False
        
        if from_version not in self.skill_versions[skill_name]:
            logger.error(f"Source version not found: {from_version}")
            return False
        
        if to_version not in self.skill_versions[skill_name]:
            logger.error(f"Target version not found: {to_version}")
            return False
        
        migration = VersionMigration(
            from_version=from_version,
            to_version=to_version,
            migration_script=migration_script,
            auto_migrate=auto_migrate
        )
        
        if skill_name not in self.migrations:
            self.migrations[skill_name] = []
        
        self.migrations[skill_name].append(migration)
        logger.info(f"Created migration {skill_name} {from_version} -> {to_version}")
        return True
    
    def migrate_skill(self, skill_name: str, target_version: str, force: bool = False) -> bool:
        """Migrate a skill to a target version."""
        current_version = self.active_versions.get(skill_name)
        if not current_version:
            logger.error(f"No active version found for {skill_name}")
            return False
        
        if current_version == target_version:
            logger.info(f"Skill {skill_name} already at version {target_version}")
            return True
        
        # Find migration path
        migration_path = self._find_migration_path(skill_name, current_version, target_version)
        if not migration_path:
            logger.error(f"No migration path found for {skill_name} {current_version} -> {target_version}")
            return False
        
        # Execute migrations
        for migration in migration_path:
            if not migration.auto_migrate and not force:
                logger.warning(f"Manual migration required for {skill_name} {migration.from_version} -> {migration.to_version}")
                return False
            
            if not migration.execute_migration(self.skill_versions[skill_name][migration.from_version].skill_path):
                logger.error(f"Migration failed for {skill_name} {migration.from_version} -> {migration.to_version}")
                return False
        
        # Update active version
        self.active_versions[skill_name] = target_version
        logger.info(f"Migrated {skill_name} to version {target_version}")
        return True
    
    def _find_migration_path(self, skill_name: str, from_version: str, to_version: str) -> Optional[List[VersionMigration]]:
        """Find migration path between versions."""
        if skill_name not in self.migrations:
            return None
        
        migrations = self.migrations[skill_name]
        
        # Simple direct migration
        for migration in migrations:
            if migration.from_version == from_version and migration.to_version == to_version:
                return [migration]
        
        # TODO: Implement more complex path finding for multi-step migrations
        return None
    
    def rollback_skill(self, skill_name: str, target_version: str) -> bool:
        """Rollback a skill to a previous version."""
        if skill_name not in self.skill_versions:
            logger.error(f"Skill not found: {skill_name}")
            return False
        
        if target_version not in self.skill_versions[skill_name]:
            logger.error(f"Target version not found: {target_version}")
            return False
        
        current_version = self.active_versions.get(skill_name)
        if current_version == target_version:
            logger.info(f"Skill {skill_name} already at version {target_version}")
            return True
        
        # Check if rollback is safe (compatible)
        target_skill = self.skill_versions[skill_name][target_version]
        if not target_skill.is_compatible_with(current_version):
            logger.warning(f"Rollback may cause compatibility issues: {target_version} not compatible with {current_version}")
        
        # Perform rollback
        self.active_versions[skill_name] = target_version
        logger.info(f"Rolled back {skill_name} to version {target_version}")
        return True
    
    def deprecate_version(self, skill_name: str, version: str, reason: str = ""):
        """Deprecate a specific version."""
        if skill_name not in self.skill_versions or version not in self.skill_versions[skill_name]:
            logger.error(f"Version not found: {skill_name} v{version}")
            return
        
        self.skill_versions[skill_name][version].deprecated = True
        
        # Update active version if it was deprecated
        if self.active_versions.get(skill_name) == version:
            new_active = self._select_active_version(skill_name)
            self.active_versions[skill_name] = new_active
            logger.info(f"Updated active version for {skill_name} to {new_active} (previous version deprecated)")
        
        logger.info(f"Deprecated {skill_name} v{version}: {reason}")
    
    def get_version_info(self, skill_name: str) -> Dict[str, Any]:
        """Get comprehensive version information for a skill."""
        if skill_name not in self.skill_versions:
            return {}
        
        versions = self.skill_versions[skill_name]
        active_version = self.active_versions.get(skill_name)
        
        info = {
            'skill_name': skill_name,
            'active_version': active_version,
            'total_versions': len(versions),
            'versions': {},
            'available_migrations': []
        }
        
        # Add version details
        for version, skill_version in versions.items():
            info['versions'][version] = {
                'is_active': version == active_version,
                'is_deprecated': skill_version.deprecated,
                'created_at': skill_version.created_at,
                'dependencies': skill_version.dependencies,
                'compatibility_count': len(skill_version.compatibility_matrix)
            }
        
        # Add migration info
        if skill_name in self.migrations:
            info['available_migrations'] = [
                {
                    'from_version': m.from_version,
                    'to_version': m.to_version,
                    'auto_migrate': m.auto_migrate,
                    'breaking_changes_count': len(m.breaking_changes)
                }
                for m in self.migrations[skill_name]
            ]
        
        return info
    
    def resolve_dependencies(self, skill_name: str, version: Optional[str] = None) -> Dict[str, str]:
        """Resolve dependency versions for a skill."""
        skill = self.get_skill(skill_name, version)
        if not skill:
            return {}
        
        resolved = {}
        
        for dep_name, required_version in skill.dependencies.items():
            # Find compatible version of dependency
            dep_skill = self.get_skill(dep_name)
            if dep_skill:
                # Try to find exact version first
                if required_version in self.skill_versions.get(dep_name, {}):
                    resolved[dep_name] = required_version
                else:
                    # Find latest compatible version
                    latest = self.get_latest_version(dep_name)
                    if latest:
                        resolved[dep_name] = latest
                    else:
                        logger.warning(f"Could not resolve dependency: {dep_name}")
            else:
                logger.warning(f"Dependency not found: {dep_name}")
        
        return resolved
    
    def list_skills(self) -> List[str]:
        """List all available skills."""
        return list(self.skill_versions.keys())
    
    def get_skill_versions(self, skill_name: str) -> List[str]:
        """Get all available versions for a skill."""
        if skill_name not in self.skill_versions:
            return []
        
        return sorted(
            self.skill_versions[skill_name].keys(),
            key=lambda v: self.skill_versions[skill_name][v].version_tuple,
            reverse=True
        )
    
    def export_version_info(self, filepath: str):
        """Export version information to file."""
        try:
            export_data = {
                'export_timestamp': time.time(),
                'skills': {}
            }
            
            for skill_name in self.skill_versions:
                export_data['skills'][skill_name] = self.get_version_info(skill_name)
            
            with open(filepath, 'w') as f:
                json.dump(export_data, f, indent=2)
            
            logger.info(f"Exported version info to {filepath}")
        except Exception as e:
            logger.error(f"Failed to export version info: {e}")
    
    def check_compatibility(self, skill_name: str, version1: str, version2: str) -> VersionCompatibility:
        """Check compatibility between two versions."""
        cache_key = f"{skill_name}:{version1}:{version2}"
        
        if cache_key in self.compatibility_cache:
            return self.compatibility_cache[cache_key]
        
        skill1 = self.get_skill(skill_name, version1)
        if not skill1:
            return VersionCompatibility.UNKNOWN
        
        compatibility = skill1.compatibility_matrix.get(version2, VersionCompatibility.UNKNOWN)
        self.compatibility_cache[cache_key] = compatibility
        
        return compatibility
    
    def get_upgrade_path(self, skill_name: str, from_version: str, to_version: str) -> List[str]:
        """Get upgrade path between versions."""
        if skill_name not in self.skill_versions:
            return []
        
        versions = self.skill_versions[skill_name]
        
        # Simple case: direct upgrade
        if from_version in versions and to_version in versions:
            return [from_version, to_version]
        
        # TODO: Implement more complex path finding
        return []
    
    def cleanup_old_versions(self, skill_name: str, keep_count: int = 3):
        """Clean up old versions, keeping only the most recent ones."""
        if skill_name not in self.skill_versions:
            return
        
        versions = self.skill_versions[skill_name]
        
        # Sort by version (newest first)
        sorted_versions = sorted(
            versions.keys(),
            key=lambda v: versions[v].version_tuple,
            reverse=True
        )
        
        # Keep active version and recent ones
        versions_to_keep = set()
        versions_to_keep.add(self.active_versions.get(skill_name))
        
        for version in sorted_versions:
            if len(versions_to_keep) >= keep_count:
                break
            versions_to_keep.add(version)
        
        # Remove old versions
        versions_to_remove = [v for v in versions.keys() if v not in versions_to_keep]
        for version in versions_to_remove:
            del versions[version]
            logger.info(f"Removed old version: {skill_name} v{version}")
        
        logger.info(f"Cleaned up {skill_name}: kept {len(versions_to_keep)} versions, removed {len(versions_to_remove)}")
