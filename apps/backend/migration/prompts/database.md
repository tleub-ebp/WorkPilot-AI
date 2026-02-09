# MySQL to PostgreSQL Migration Prompt

You are an expert database administrator specializing in database migrations.

## Task
Transform MySQL SQL DDL and application code to PostgreSQL compatible format.

## SQL Transformation Rules

### 1. Data Type Mappings
- `TINYINT` → `SMALLINT`
- `MEDIUMINT` → `INTEGER`
- `INT` → `INTEGER`
- `BIGINT` → `BIGINT`
- `FLOAT` → `REAL`
- `DOUBLE` → `DOUBLE PRECISION`
- `VARCHAR(n)` → `VARCHAR(n)` (keep size)
- `TEXT` → `TEXT`
- `BLOB` → `BYTEA`
- `DATETIME` → `TIMESTAMP`
- `TIMESTAMP` → `TIMESTAMP`
- `ENUM('a','b')` → `TEXT` (with CHECK constraint)
- `JSON` → `JSONB`

### 2. Auto-Increment
- MySQL: `INT NOT NULL AUTO_INCREMENT PRIMARY KEY`
- PostgreSQL: `SERIAL PRIMARY KEY`
- MySQL: `BIGINT NOT NULL AUTO_INCREMENT`
- PostgreSQL: `BIGSERIAL PRIMARY KEY`

### 3. CREATE TABLE Syntax
- Remove MySQL specific options: ENGINE, DEFAULT CHARSET, COLLATE, ROW_FORMAT
- Replace backticks (`) with double quotes (")
- Keep all constraints and indexes

### 4. Function Mappings
- `CONCAT(a, b)` → `a || b` or `CONCAT(a, b)`
- `SUBSTR()` → `SUBSTRING()`
- `IFNULL(a, b)` → `COALESCE(a, b)`
- `IF(cond, a, b)` → `CASE WHEN cond THEN a ELSE b END`
- `NOW()` → `NOW()`
- `DATE_FORMAT()` → `TO_CHAR()`

### 5. Query Syntax
- `LIMIT n, m` → `LIMIT m OFFSET n`
- `ON DUPLICATE KEY UPDATE` → `ON CONFLICT DO UPDATE SET`
- `<>` operator → `!=`

### 6. String Delimiters
- Backticks: `` `table_name` `` → `"table_name"`
- Single quotes for values remain the same

## Application Code Transformation

### JavaScript/Node.js
- `require('mysql2')` → `require('pg')`
- `mysql.createConnection()` → `new Pool()` from pg
- Query placeholders: `?` → `$1, $2, ...` (numbered)
- `.query(sql, params, callback)` → `.query(sql, params)`

### Python
- `MySQLdb.connect()` → `psycopg2.connect()`
- Parameter names remain consistent
- Exception handling may need updates

## Important Notes
- Data integrity is critical - verify all constraints
- Test migrations with sample data
- Check for application-level differences in driver APIs
- PostgreSQL has stricter type requirements
- Consider performance implications of type changes
- Preserve all comments in DDL
