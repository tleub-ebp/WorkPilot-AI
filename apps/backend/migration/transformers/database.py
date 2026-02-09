"""
Database Transformer: MySQL to PostgreSQL
Transforms MySQL schema and queries to PostgreSQL
"""

import re
from typing import Dict, List
from pathlib import Path

from ..models import TransformationResult


class DatabaseTransformer:
    """Transform MySQL to PostgreSQL."""

    # Type mappings
    TYPE_MAPPINGS = {
        # Numeric types
        'TINYINT': 'SMALLINT',
        'SMALLINT': 'SMALLINT',
        'MEDIUMINT': 'INTEGER',
        'INT': 'INTEGER',
        'INTEGER': 'INTEGER',
        'BIGINT': 'BIGINT',
        'FLOAT': 'REAL',
        'DOUBLE': 'DOUBLE PRECISION',
        'DECIMAL': 'NUMERIC',
        'NUMERIC': 'NUMERIC',
        
        # String types
        'CHAR': 'CHAR',
        'VARCHAR': 'VARCHAR',
        'TEXT': 'TEXT',
        'TINYTEXT': 'VARCHAR(255)',
        'MEDIUMTEXT': 'TEXT',
        'LONGTEXT': 'TEXT',
        'BLOB': 'BYTEA',
        'TINYBLOB': 'BYTEA',
        'MEDIUMBLOB': 'BYTEA',
        'LONGBLOB': 'BYTEA',
        
        # Date/Time types
        'DATE': 'DATE',
        'TIME': 'TIME',
        'DATETIME': 'TIMESTAMP',
        'TIMESTAMP': 'TIMESTAMP',
        'YEAR': 'INTEGER',
        
        # Boolean
        'BOOLEAN': 'BOOLEAN',
        'BOOL': 'BOOLEAN',
        
        # JSON
        'JSON': 'JSONB',
        
        # Special
        'ENUM': 'TEXT',
        'SET': 'TEXT[]',
    }

    # Function mappings
    FUNCTION_MAPPINGS = {
        'CONCAT': 'CONCAT',
        'SUBSTR': 'SUBSTRING',
        'SUBSTRING': 'SUBSTRING',
        'LENGTH': 'LENGTH',
        'UPPER': 'UPPER',
        'LOWER': 'LOWER',
        'TRIM': 'TRIM',
        'COALESCE': 'COALESCE',
        'IFNULL': 'COALESCE',
        'IF': 'CASE WHEN',
        'NOW()': 'NOW()',
        'CURRENT_DATE': 'CURRENT_DATE',
        'CURRENT_TIMESTAMP': 'CURRENT_TIMESTAMP',
        'DATE_ADD': 'DATE_ADD',
        'DATE_SUB': 'DATE_SUB',
        'DATE_FORMAT': 'TO_CHAR',
        'COUNT': 'COUNT',
        'SUM': 'SUM',
        'AVG': 'AVG',
        'MAX': 'MAX',
        'MIN': 'MIN',
    }

    def __init__(self, project_dir: str):
        self.project_dir = Path(project_dir)
        self.transformations: List[TransformationResult] = []

    def transform_sql_files(self, file_paths: List[str]) -> List[TransformationResult]:
        """Transform MySQL SQL files to PostgreSQL."""
        results = []
        
        for file_path in file_paths:
            try:
                full_path = self.project_dir / file_path
                if not full_path.exists():
                    continue
                
                content = full_path.read_text()
                
                # Transform the SQL content
                transformed = self._transform_sql(content)
                
                result = TransformationResult(
                    file_path=file_path,
                    transformation_type="sql_conversion",
                    before=content,
                    after=transformed,
                    changes_count=self._count_changes(content, transformed),
                    confidence=0.90,
                    validation_passed=False,
                )
                results.append(result)
                
            except Exception as e:
                result = TransformationResult(
                    file_path=file_path,
                    transformation_type="sql_conversion",
                    before="",
                    after="",
                    changes_count=0,
                    confidence=0.0,
                    errors=[f"SQL transformation error: {str(e)}"],
                    validation_passed=False,
                )
                results.append(result)
        
        self.transformations = results
        return results

    def _transform_sql(self, content: str) -> str:
        """Transform MySQL SQL to PostgreSQL."""
        sql = content
        
        # 1. Transform CREATE TABLE statements
        sql = self._transform_create_table(sql)
        
        # 2. Transform data types
        sql = self._transform_data_types(sql)
        
        # 3. Transform functions
        sql = self._transform_functions(sql)
        
        # 4. Transform syntax
        sql = self._transform_syntax(sql)
        
        # 5. Transform auto-increment
        sql = self._transform_auto_increment(sql)
        
        # 6. Transform string functions
        sql = self._transform_string_functions(sql)
        
        return sql

    def _transform_create_table(self, sql: str) -> str:
        """Transform CREATE TABLE statements."""
        # Remove MySQL specific options
        sql = re.sub(r'ENGINE\s*=\s*\w+\s*[,;]?', '', sql, flags=re.IGNORECASE)
        sql = re.sub(r'DEFAULT\s+CHARSET\s*=\s*\w+\s*[,;]?', '', sql, flags=re.IGNORECASE)
        sql = re.sub(r'COLLATE\s*=\s*\w+\s*[,;]?', '', sql, flags=re.IGNORECASE)
        sql = re.sub(r'ROW_FORMAT\s*=\s*\w+\s*[,;]?', '', sql, flags=re.IGNORECASE)
        sql = re.sub(r'AUTO_INCREMENT\s*=\s*\d+\s*[,;]?', '', sql, flags=re.IGNORECASE)
        
        # Replace backticks with double quotes
        sql = sql.replace('`', '"')
        
        return sql

    def _transform_data_types(self, sql: str) -> str:
        """Transform MySQL data types to PostgreSQL."""
        for mysql_type, pg_type in self.TYPE_MAPPINGS.items():
            # Handle type definitions with parameters
            pattern = f'\\b{mysql_type}\\b(?:\\(([^)]+)\\))?'
            
            def replace_type(match):
                params = match.group(1)
                if params and mysql_type in ['VARCHAR', 'CHAR', 'DECIMAL']:
                    return f'{pg_type}({params})'
                else:
                    return pg_type
            
            sql = re.sub(pattern, replace_type, sql, flags=re.IGNORECASE)
        
        # Transform UNSIGNED INT to BIGINT
        sql = re.sub(
            r'UNSIGNED\s+INTEGER',
            'BIGINT',
            sql,
            flags=re.IGNORECASE
        )
        
        return sql

    def _transform_functions(self, sql: str) -> str:
        """Transform MySQL functions to PostgreSQL."""
        for mysql_func, pg_func in self.FUNCTION_MAPPINGS.items():
            pattern = f'\\b{mysql_func}\\b'
            sql = re.sub(pattern, pg_func, sql, flags=re.IGNORECASE)
        
        # Special case: IFNULL -> COALESCE
        sql = re.sub(
            r'IFNULL\s*\(\s*([^,]+)\s*,\s*([^)]+)\s*\)',
            r'COALESCE(\1, \2)',
            sql,
            flags=re.IGNORECASE
        )
        
        # Special case: IF -> CASE WHEN
        sql = re.sub(
            r'IF\s*\(\s*([^,]+)\s*,\s*([^,]+)\s*,\s*([^)]+)\s*\)',
            r'CASE WHEN \1 THEN \2 ELSE \3 END',
            sql,
            flags=re.IGNORECASE
        )
        
        return sql

    def _transform_syntax(self, sql: str) -> str:
        """Transform SQL syntax differences."""
        # Replace LIMIT with LIMIT/OFFSET
        sql = re.sub(
            r'LIMIT\s+(\d+)\s*,\s*(\d+)',
            r'LIMIT \2 OFFSET \1',
            sql,
            flags=re.IGNORECASE
        )
        
        # Transform ON DUPLICATE KEY UPDATE
        sql = re.sub(
            r'ON\s+DUPLICATE\s+KEY\s+UPDATE',
            'ON CONFLICT DO UPDATE SET',
            sql,
            flags=re.IGNORECASE
        )
        
        # Transform engine-specific syntax
        sql = re.sub(
            r'FULLTEXT\s+',
            '',
            sql,
            flags=re.IGNORECASE
        )
        
        return sql

    def _transform_auto_increment(self, sql: str) -> str:
        """Transform AUTO_INCREMENT to SERIAL."""
        # Replace AUTO_INCREMENT INT with SERIAL
        sql = re.sub(
            r'(\w+)\s+INT\s+NOT\s+NULL\s+AUTO_INCREMENT\s+PRIMARY\s+KEY',
            r'\1 SERIAL PRIMARY KEY',
            sql,
            flags=re.IGNORECASE
        )
        
        # Replace AUTO_INCREMENT INT with SERIAL
        sql = re.sub(
            r'INT\s+NOT\s+NULL\s+AUTO_INCREMENT',
            'SERIAL',
            sql,
            flags=re.IGNORECASE
        )
        
        # Replace BIGINT AUTO_INCREMENT with BIGSERIAL
        sql = re.sub(
            r'BIGINT\s+NOT\s+NULL\s+AUTO_INCREMENT',
            'BIGSERIAL',
            sql,
            flags=re.IGNORECASE
        )
        
        return sql

    def _transform_string_functions(self, sql: str) -> str:
        """Transform string function syntax."""
        # CONCAT -> ||
        sql = re.sub(
            r'CONCAT\s*\(\s*([^)]+)\s*\)',
            lambda m: ' || '.join(m.group(1).split(',')),
            sql
        )
        
        # DATE_FORMAT -> TO_CHAR
        sql = re.sub(
            r'DATE_FORMAT\s*\(\s*([^,]+)\s*,\s*\'([^\']+)\'\s*\)',
            r"TO_CHAR(\1, '\2')",
            sql
        )
        
        return sql

    def transform_application_code(self, file_paths: List[str]) -> List[TransformationResult]:
        """Transform application code that uses MySQL (Node.js/Python)."""
        results = []
        
        for file_path in file_paths:
            try:
                full_path = self.project_dir / file_path
                if not full_path.exists():
                    continue
                
                content = full_path.read_text()
                
                if not self._uses_database(content):
                    continue
                
                # Transform database calls
                transformed = self._transform_db_calls(content, file_path)
                
                result = TransformationResult(
                    file_path=file_path,
                    transformation_type="db_driver_update",
                    before=content,
                    after=transformed,
                    changes_count=self._count_changes(content, transformed),
                    confidence=0.85,
                    validation_passed=False,
                )
                results.append(result)
                
            except Exception as e:
                result = TransformationResult(
                    file_path=file_path,
                    transformation_type="db_driver_update",
                    before="",
                    after="",
                    changes_count=0,
                    confidence=0.0,
                    errors=[f"Code transformation error: {str(e)}"],
                    validation_passed=False,
                )
                results.append(result)
        
        return results

    def _uses_database(self, content: str) -> bool:
        """Check if file uses database."""
        return bool(
            re.search(r'mysql', content, re.IGNORECASE) or
            re.search(r'mysql2', content, re.IGNORECASE) or
            re.search(r'database', content, re.IGNORECASE) or
            re.search(r'connection\.query', content, re.IGNORECASE) or
            re.search(r'db\.query', content, re.IGNORECASE)
        )

    def _transform_db_calls(self, content: str, file_path: str) -> str:
        """Transform database calls from MySQL to PostgreSQL."""
        code = content
        
        # JavaScript/Node.js transformations
        if file_path.endswith('.js') or file_path.endswith('.ts'):
            # Replace mysql2 driver import
            code = re.sub(
                r'require\([\'"]mysql2[\'"](?:/promise)?\)',
                "require('pg')",
                code
            )
            code = re.sub(
                r'import\s+(?:.*?)\s+from\s+[\'"]mysql2[\'"]',
                "import { Pool } from 'pg'",
                code
            )
            
            # Transform connection creation
            code = self._transform_mysql_connection(code)
            
            # Transform query syntax
            code = self._transform_query_syntax_js(code)
        
        # Python transformations
        elif file_path.endswith('.py'):
            # Replace MySQLdb or mysql-connector-python
            code = re.sub(
                r'import\s+MySQLdb',
                'import psycopg2',
                code
            )
            code = re.sub(
                r'from\s+mysql\s+import\s+connector',
                'import psycopg2',
                code
            )
            
            # Transform connection
            code = self._transform_mysql_connection_python(code)
        
        return code

    def _transform_mysql_connection(self, code: str) -> str:
        """Transform MySQL connection to PostgreSQL in JS."""
        # Replace mysql2 connection with pg Pool
        code = re.sub(
            r'const\s+connection\s*=\s*mysql\.createConnection\s*\({[^}]+}\)',
            "const pool = new Pool({\n  host: 'localhost',\n  port: 5432,\n  database: 'mydb',\n  user: 'postgres',\n  password: 'password'\n})",
            code
        )
        
        code = re.sub(
            r'connection\.connect\(\)',
            '// Pool auto-connects',
            code
        )
        
        return code

    def _transform_mysql_connection_python(self, code: str) -> str:
        """Transform MySQL connection to PostgreSQL in Python."""
        code = re.sub(
            r'connection\s*=\s*MySQLdb\.connect\s*\(',
            'connection = psycopg2.connect(',
            code
        )
        
        code = re.sub(
            r'host\s*=\s*[\'"]localhost[\'"],?\s*'
            r'user\s*=\s*[\'"][^\'"]+ [\'"],?\s*'
            r'passwd\s*=\s*[\'"][^\'"]+ [\'"],?\s*'
            r'db\s*=\s*[\'"][^\'"]+ [\'"]',
            "host='localhost', user='postgres', password='password', database='mydb'",
            code
        )
        
        return code

    def _transform_query_syntax_js(self, code: str) -> str:
        """Transform query syntax in JavaScript."""
        # PostgreSQL uses different placeholder syntax
        code = re.sub(
            r'\?',
            r'$1',  # Will need numbered parameters
            code
        )
        
        return code

    def _count_changes(self, before: str, after: str) -> int:
        """Count lines changed."""
        before_lines = before.split('\n')
        after_lines = after.split('\n')
        
        changes = abs(len(before_lines) - len(after_lines))
        
        for b, a in zip(before_lines, after_lines):
            if b != a:
                changes += 1
        
        return changes

    def get_transformations(self) -> List[TransformationResult]:
        """Get all transformations."""
        return self.transformations
