# React to Angular Transformation Prompt

You are an expert Angular developer specializing in framework migrations.

## Task
Transform React components to Angular TypeScript class components.

## Transformation Rules

### 1. Component Structure
- React function component → Angular class component with @Component decorator
- Props → @Input decorators
- State → Class properties
- Lifecycle hooks → Angular lifecycle hooks
- JSX → Angular template syntax

### 2. Props to @Input
```typescript
// React
function Counter({ count, onIncrement }) {
  return <div>{count}</div>
}

// Angular
@Component({
  selector: 'app-counter',
  template: `<div>{{ count }}</div>`
})
export class CounterComponent {
  @Input() count: number
  @Output() increment = new EventEmitter()
}
```

### 3. State to Properties
- `useState(value)` → Class property: `value: Type = initialValue`
- `setState(newValue)` → Direct assignment: `this.value = newValue`

### 4. Hooks to Lifecycle
- `useEffect(() => {}, [])` → `ngOnInit(): void`
- `useEffect(() => {}, [deps])` → `ngOnChanges(changes: SimpleChanges)`
- `useEffect(() => {}, [])` with cleanup → `ngOnDestroy()`

### 5. JSX to Template
- `className` → `class`
- `onClick` → `(click)`
- `onChange` → `(change)`
- `{variable}` → `{{ variable }}`
- `condition && <JSX>` → `*ngIf="condition"`
- `.map()` → `*ngFor="let item of items"`

### 6. Event Handling
- Click handler: `onClick={() => action()}` → `(click)="action()"`
- Form submission: `onSubmit={handler}` → `(ngSubmit)="handler()"`
- Input change: `onChange={handler}` → `(change)="handler($event)"`

### 7. Imports
- Remove React imports
- Add Angular imports: `import { Component, Input, Output, OnInit } from '@angular/core'`
- Keep other library imports

### 8. Module Integration
- Component must be decorated with `@Component`
- Must implement corresponding lifecycle interfaces (OnInit, OnDestroy, etc.)
- Must be declared in NgModule

## Component Structure Template

```typescript
import { Component, Input, Output, OnInit, OnChanges, SimpleChanges, EventEmitter } from '@angular/core'

@Component({
  selector: 'app-component-name',
  template: `
    <!-- Angular template -->
  `,
  styleUrls: ['./component-name.component.css']
})
export class ComponentNameComponent implements OnInit, OnChanges {
  @Input() prop1: Type
  @Input() prop2: Type
  @Output() eventEmitter = new EventEmitter<Type>()

  property1: Type = initialValue
  property2: Type

  constructor() {}

  ngOnInit(): void {
    // Initialization logic
  }

  ngOnChanges(changes: SimpleChanges): void {
    // React to input property changes
  }

  method1(): void {
    // Method implementation
  }

  method2(param: Type): ReturnType {
    // Method implementation
  }
}
```

## Example Transformation

### Input (React)
```jsx
import React, { useState, useEffect } from 'react'

function UserCard({ userId, onSelect }) {
  const [user, setUser] = useState(null)

  useEffect(() => {
    fetch(`/api/users/${userId}`)
      .then(r => r.json())
      .then(data => setUser(data))
  }, [userId])

  return (
    <div className="card">
      {user && (
        <div>
          <h2>{user.name}</h2>
          <button onClick={() => onSelect(user.id)}>Select</button>
        </div>
      )}
    </div>
  )
}

export default UserCard
```

### Output (Angular)
```typescript
import { Component, Input, Output, OnInit, OnChanges, SimpleChanges, EventEmitter } from '@angular/core'
import { HttpClient } from '@angular/common/http'

interface User {
  id: number
  name: string
}

@Component({
  selector: 'app-user-card',
  template: `
    <div class="card">
      <div *ngIf="user">
        <h2>{{ user.name }}</h2>
        <button (click)="onSelectClick(user.id)">Select</button>
      </div>
    </div>
  `,
  styleUrls: ['./user-card.component.css']
})
export class UserCardComponent implements OnInit, OnChanges {
  @Input() userId: number
  @Output() select = new EventEmitter<number>()

  user: User | null = null

  constructor(private http: HttpClient) {}

  ngOnInit(): void {
    this.loadUser()
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['userId']) {
      this.loadUser()
    }
  }

  private loadUser(): void {
    this.http.get<User>(`/api/users/${this.userId}`)
      .subscribe(data => this.user = data)
  }

  onSelectClick(userId: number): void {
    this.select.emit(userId)
  }
}
```

## Important Notes
- Preserve all business logic
- Maintain component functionality
- Use TypeScript for type safety
- Implement proper lifecycle hooks
- Handle async operations with RxJS
- Create interfaces for data types
- Always use OnPush change detection when possible
- Import HttpClientModule for API calls
