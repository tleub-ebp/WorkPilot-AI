# 📝 Migration Prompts Guide

This directory contains specialized LLM prompts for guiding Claude through complex code transformations.

## Overview

Each migration type has a dedicated prompt that provides:
- Clear transformation rules and patterns
- Examples and expected outputs
- Important considerations and edge cases
- Best practices for the specific migration

## Prompts Available

### 1. React to Vue (`react_to_vue.md`)

**Purpose**: Transform React JSX components to Vue 3 Single File Components

**When to use**:
- Converting React function components to Vue
- Migrating from hooks to Composition API
- Transforming JSX syntax to Vue templates
- Converting React state management to Vue's ref/reactive

**Key transformations**:
- `useState()` → `ref()` or `reactive()`
- `useEffect()` → `onMounted()`, `watch()`
- `onClick` → `@click`
- JSX → Vue template syntax

**Example**:
```javascript
// Input (React)
function Counter() {
  const [count, setCount] = useState(0)
  return <button onClick={() => setCount(count + 1)}>Count: {count}</button>
}

// Output (Vue)
<template>
  <button @click="count++">Count: {{ count }}</button>
</template>
<script setup>
import { ref } from 'vue'
const count = ref(0)
</script>
```

### 2. Database Migration (`database.md`)

**Purpose**: Transform MySQL schemas and queries to PostgreSQL

**When to use**:
- Converting MySQL DDL to PostgreSQL syntax
- Updating application code for PostgreSQL driver
- Migrating data types between systems
- Updating SQL functions and syntax

**Key transformations**:
- `INT AUTO_INCREMENT PRIMARY KEY` → `SERIAL PRIMARY KEY`
- `TINYINT` → `SMALLINT`
- `` `table_name` `` → `"table_name"`
- `LIMIT n, m` → `LIMIT m OFFSET n`

**Example**:
```sql
-- Input (MySQL)
CREATE TABLE users (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(255),
  created_at DATETIME
) ENGINE=InnoDB;

-- Output (PostgreSQL)
CREATE TABLE users (
  id SERIAL PRIMARY KEY,
  name VARCHAR(255),
  created_at TIMESTAMP
);
```

### 3. Python Migration (`python.md`)

**Purpose**: Transform Python 2 code to Python 3

**When to use**:
- Converting print statements
- Updating imports for Python 3
- Handling unicode/string differences
- Modernizing Python 2 syntax

**Key transformations**:
- `print "text"` → `print("text")`
- `xrange()` → `range()`
- `unicode()` → `str()`
- `.iteritems()` → `.items()`
- `except E, e:` → `except E as e:`

**Example**:
```python
# Input (Python 2)
print "Hello"
for i in xrange(10):
    print i

# Output (Python 3)
print("Hello")
for i in range(10):
    print(i)
```

### 4. JavaScript to TypeScript (`js_to_ts.md`)

**Purpose**: Add type annotations to JavaScript code

**When to use**:
- Converting JavaScript files to TypeScript
- Adding type safety to existing code
- Generating interfaces for object types
- Enabling strict mode

**Key transformations**:
- Add function parameter types
- Add return type annotations
- Create interfaces for object types
- Infer primitive types

**Example**:
```typescript
// Input (JavaScript)
function greet(name) {
  return `Hello, ${name}!`
}

// Output (TypeScript)
function greet(name: string): string {
  return `Hello, ${name}!`
}
```

### 5. REST to GraphQL (`rest_to_graphql.md`)

**Purpose**: Transform REST API to GraphQL schema and resolvers

**When to use**:
- Converting REST endpoints to GraphQL queries/mutations
- Generating GraphQL schema from API responses
- Updating application code for GraphQL

**Key transformations**:
- `GET /api/users/:id` → `query getUser(id: ID!): User`
- `POST /api/users` → `mutation createUser(input: CreateUserInput!): User`
- Response types → GraphQL types
- Query parameters → GraphQL arguments

**Example**:
```graphql
# Input pattern: REST endpoints
# GET /api/users - list users
# POST /api/users - create user
# GET /api/users/:id - get user
# PUT /api/users/:id - update user
# DELETE /api/users/:id - delete user

# Output (GraphQL)
type Query {
  users(limit: Int, offset: Int): [User!]!
  user(id: ID!): User
}

type Mutation {
  createUser(input: CreateUserInput!): User!
  updateUser(id: ID!, input: UpdateUserInput!): User!
  deleteUser(id: ID!): Boolean!
}
```

## How to Use These Prompts

### Method 1: Direct Claude Integration

When using with Claude directly:

```python
from anthropic import Anthropic

client = Anthropic()

# Load the prompt
with open('apps/backend/migration/prompts/react_to_vue.md', 'r') as f:
    system_prompt = f.read()

# Send code for transformation
response = client.messages.create(
    model="claude-opus-4-1",
    max_tokens=4000,
    system=system_prompt,
    messages=[
        {
            "role": "user",
            "content": f"Please transform this React component:\n\n{jsx_code}"
        }
    ]
)

print(response.content[0].text)
```

### Method 2: Within Migration Engine

```python
from apps.backend.migration.orchestrator import MigrationOrchestrator
from apps.backend.migration.transformer import TransformationEngine

# Prompts are automatically used during transformation
engine = TransformationEngine(
    project_dir="./src",
    source_framework="react",
    target_framework="vue"
)

# Loads react_to_vue.md prompt automatically
results = engine.transform_code(file_paths)
```

### Method 3: Manual Claude Interaction

1. Copy the relevant prompt from `prompts/` directory
2. Paste it as the system message in Claude
3. Provide your code for transformation
4. Review the output and iterate

## Customizing Prompts

### Adding New Transformation Rules

Edit the relevant `.md` file and add:

```markdown
### New Rule Name

**Description**: What this transformation does

**Example**:
```code
Before → After
```
```

### Adjusting Confidence Levels

Each transformer has a default confidence score. To adjust:

```python
# In transformer.py
result = TransformationResult(
    file_path=file_path,
    transformation_type="...",
    before=before,
    after=after,
    confidence=0.85,  # Adjust this value (0-1)
    ...
)
```

Higher confidence = more conservative transformations  
Lower confidence = more aggressive transformations

## Best Practices

### When Creating New Prompts

1. **Be Specific**: List exact rules, not general guidance
2. **Provide Examples**: Show before and after code
3. **Mention Edge Cases**: What the transformer should be careful about
4. **Include Limitations**: What the transformer can't handle
5. **Add Context**: Explain why certain transformations are important

### When Using Prompts

1. **Review Carefully**: Always review Claude's output
2. **Test Thoroughly**: Run tests after transformations
3. **Iterate if Needed**: If output isn't perfect, provide feedback
4. **Document Changes**: Keep track of what was transformed

## Prompt Maintenance

### Regular Updates

- Review and update prompts quarterly
- Add new patterns as they emerge
- Remove outdated patterns
- Improve examples based on actual transformations

### Version Control

Prompts are version-controlled in git. Keep history of changes:

```bash
git log -p apps/backend/migration/prompts/
```

## Troubleshooting

### Transformation Quality Issues

If transformations aren't working well:

1. **Check the prompt**: Review if rules are clear and complete
2. **Test with simple code**: Start with minimal examples
3. **Provide context**: Add comments explaining business logic
4. **Adjust confidence**: Try different confidence thresholds
5. **Use hybrid approach**: Manual + automated

### Missing Edge Cases

If certain patterns aren't handled:

1. Add the pattern to the prompt with an example
2. Create a test case for the pattern
3. Update the transformer if needed
4. Re-run transformations

## Examples Directory

Sample transformed code is available in:
- `tests/migration_fixtures.py` - Original code samples
- `docs/examples/` - Fully transformed examples (coming soon)

## Performance Tips

- Break large files into smaller chunks
- Use parallel transformation for multiple files
- Cache transformation results
- Pre-process code to fix obvious issues

## Integration with Teams

When integrated with Claude Teams, each agent gets specialized prompts:

- **Architect**: Uses full prompt for architectural review
- **Developer**: Uses prompt without warning sections
- **QA**: Gets validation sections of prompts
- **Security**: Gets security-relevant sections

---

For more information, see:
- 📖 Main Migration Engine docs: `apps/backend/migration/README.md`
- 🚀 Quick start guide: `docs/features/MIGRATION_QUICK_START.md`
- 📝 Implementation details: `FEATURE_20_WEEK1_SUMMARY.md`
