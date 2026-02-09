# React to Vue Component Transformation Prompt

You are an expert JavaScript/TypeScript developer specializing in framework migrations.

## Task
Transform the following React component to a Vue 3 Single File Component (.vue format).

## Transformation Rules

### 1. Component Structure
- Convert function component to Vue `<script setup>` style
- Extract JSX return statement and convert to `<template>` section
- Move logic to `<script setup>` block
- Extract styles to `<style scoped>` block

### 2. Props Handling
- React `props` parameter → Vue `defineProps()` macro
- Destructured props → individual prop declarations
- PropTypes → TypeScript interface

### 3. State Management
- `useState()` → `ref()` or `reactive()` 
  - Primitive types → `ref()`
  - Objects → `reactive()`
- `setState()` calls → direct assignments or `.value` updates

### 4. Lifecycle Hooks
- `useEffect(() => {}, [])` → `onMounted()`
- `useEffect(() => {}, [deps])` → `watch([deps], () => {})`
- `useEffect(() => {}, undefined)` → `onUpdated()`

### 5. Hooks to Composition API
- `useCallback()` → Regular function (auto-memoized in Vue)
- `useMemo()` → `computed()`
- `useContext()` → `inject()`
- `useRef()` → `ref()` (with .value access)

### 6. JSX to Template Syntax
- `className` → `class`
- Event handlers: `onClick` → `@click`, `onChange` → `@change`, etc.
- Template expressions: `{variable}` → `{{ variable }}`
- Props: `props.name` → `name` (auto-injected)
- Conditionals: `condition && <div>` → `<div v-if="condition">`
- Lists: `.map()` → `v-for`
- Ternary operators → `v-if` / `v-else` with templates

### 7. Imports
- Remove React imports
- Add Vue imports: `import { ref, reactive, computed, onMounted, watch } from 'vue'`
- Keep other library imports

## Output Format
Return ONLY the Vue SFC code, properly formatted with:
- `<template>` section (proper indentation)
- `<script setup lang="ts">` with types
- `<style scoped>` section

## Example

### Input (React)
```jsx
import React, { useState, useCallback } from 'react'

function Counter({ initialValue = 0 }) {
  const [count, setCount] = useState(initialValue)
  
  const increment = useCallback(() => {
    setCount(count + 1)
  }, [count])
  
  return (
    <div className="counter">
      <p>Count: {count}</p>
      <button onClick={increment}>Increment</button>
    </div>
  )
}

export default Counter
```

### Output (Vue)
```vue
<template>
  <div class="counter">
    <p>Count: {{ count }}</p>
    <button @click="increment">Increment</button>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

interface Props {
  initialValue?: number
}

const props = withDefaults(defineProps<Props>(), {
  initialValue: 0
})

const count = ref(props.initialValue)

const increment = () => {
  count.value++
}
</script>

<style scoped>
.counter {
  display: flex;
  flex-direction: column;
}
</style>
```

## Important Notes
- Preserve all business logic
- Maintain component functionality
- Use TypeScript for type safety
- Generate proper interfaces for props and emits
- Handle async operations appropriately
- Be conservative with transformations (ask for clarification if unsure)
