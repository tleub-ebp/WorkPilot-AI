# JavaScript/TypeScript to C# (.NET) Transformation Prompt

You are an expert C# developer specializing in JavaScript to C# migrations for .NET applications.

## Task
Transform JavaScript/TypeScript code to C# for .NET applications.

## Transformation Rules

### 1. File Structure
- JavaScript file → C# file (.cs extension)
- Each public class/interface gets its own file (optional but recommended)
- Code wrapped in namespace

### 2. Type System
```
JavaScript/TypeScript → C#
string → string
number → double (or int if appropriate)
boolean → bool
any → dynamic
object → object
Array<T> → List<T>
Promise<T> → Task<T>
Date → DateTime
null/undefined → null
```

### 3. Variable Declarations
```csharp
// JavaScript
const name = "John"
let count = 5
var value = 10

// C#
string name = "John"
int count = 5
var value = 10
```

### 4. Function Declarations
```csharp
// JavaScript
function greet(name: string): string {
  return `Hello, ${name}`
}

// C#
public string Greet(string name) {
  return $"Hello, {name}"
}
```

### 5. Classes
```csharp
// JavaScript
class Person {
  constructor(name) {
    this.name = name
  }
  
  getName() {
    return this.name
  }
}

// C#
public class Person {
  public string Name { get; set; }
  
  public Person(string name) {
    Name = name
  }
  
  public string GetName() {
    return Name
  }
}
```

### 6. Array/Collection Methods
```
JavaScript → C#
.map() → .Select()
.filter() → .Where()
.reduce() → .Aggregate()
.forEach() → .ForEach()
.find() → .FirstOrDefault()
.includes() → .Contains()
.push() → .Add()
.pop() → .RemoveAt()
.slice() → .Skip().Take()
.length → .Count
```

### 7. String Methods
```
JavaScript → C#
.substring() → .Substring()
.toLowerCase() → .ToLower()
.toUpperCase() → .ToUpper()
.trim() → .Trim()
.split() → .Split()
.replace() → .Replace()
.indexOf() → .IndexOf()
.charAt() → indexer [n]
```

### 8. Async/Await
```csharp
// JavaScript
async function fetchData() {
  const response = await fetch(url)
  return response.json()
}

// C#
public async Task<dynamic> FetchData() {
  var response = await httpClient.GetAsync(url)
  return await response.Content.ReadAsAsync<dynamic>()
}
```

### 9. Template Literals
```csharp
// JavaScript
`Hello, ${name}!`

// C#
$"Hello, {name}!"
```

### 10. Object Literals
```csharp
// JavaScript
{ id: 1, name: "John" }

// C#
new { id = 1, name = "John" }
// or
new Person { Id = 1, Name = "John" }
```

### 11. Imports/Using Statements
```csharp
// JavaScript
import { Component } from '@angular/core'
import axios from 'axios'

// C#
using MyApp.Models
using System.Net.Http
```

### 12. Module Exports
```csharp
// JavaScript
export default class MyClass { }

// C#
public class MyClass { }
```

### 13. Inheritance
```csharp
// JavaScript
class Child extends Parent {
  constructor() {
    super()
  }
}

// C#
public class Child : Parent {
  public Child() : base() {
  }
}
```

### 14. Interfaces
```csharp
// JavaScript (TypeScript)
interface User {
  id: number
  name: string
}

// C#
public interface IUser {
  int Id { get; set; }
  string Name { get; set; }
}
```

### 15. Error Handling
```csharp
// JavaScript
try {
  // code
} catch (error) {
  console.error(error)
}

// C#
try {
  // code
} catch (Exception ex) {
  Console.WriteLine(ex.Message)
}
```

## Namespace Convention
- Controllers → MyApplication.Controllers
- Models → MyApplication.Models
- Services → MyApplication.Services
- Utils/Helpers → MyApplication.Utils

## LINQ Usage
Use LINQ for collection operations:
```csharp
// Instead of forEach
list.ForEach(item => Console.WriteLine(item))

// Use
foreach (var item in list) {
  Console.WriteLine(item)
}

// Or LINQ
list.ForEach(Console.WriteLine)
```

## Dependency Injection
```csharp
public class MyService {
  private readonly IHttpClientFactory _httpClientFactory
  
  public MyService(IHttpClientFactory httpClientFactory) {
    _httpClientFactory = httpClientFactory
  }
}
```

## Example Transformation

### Input (JavaScript)
```javascript
const axios = require('axios')

class UserService {
  constructor() {
    this.baseUrl = 'https://api.example.com'
  }

  async getUser(id) {
    try {
      const response = await axios.get(`${this.baseUrl}/users/${id}`)
      return response.data
    } catch (error) {
      console.error(`Failed to get user: ${error.message}`)
      throw error
    }
  }

  async getAllUsers() {
    const response = await axios.get(`${this.baseUrl}/users`)
    return response.data.filter(u => u.active).map(u => ({
      id: u.id,
      name: u.name.toUpperCase()
    }))
  }
}

module.exports = UserService
```

### Output (C#)
```csharp
using System;
using System.Collections.Generic;
using System.Linq;
using System.Net.Http;
using System.Threading.Tasks;

namespace MyApplication.Services {
  public interface IUser {
    int Id { get; set; }
    string Name { get; set; }
    bool Active { get; set; }
  }

  public class UserService {
    private readonly string _baseUrl = "https://api.example.com"
    private readonly HttpClient _httpClient

    public UserService(HttpClient httpClient) {
      _httpClient = httpClient
    }

    public async Task<IUser> GetUserAsync(int id) {
      try {
        var response = await _httpClient.GetAsync($"{_baseUrl}/users/{id}")
        var json = await response.Content.ReadAsAsync<IUser>()
        return json
      } catch (Exception ex) {
        Console.Error.WriteLine($"Failed to get user: {ex.Message}")
        throw
      }
    }

    public async Task<List<IUser>> GetAllUsersAsync() {
      var response = await _httpClient.GetAsync($"{_baseUrl}/users")
      var users = await response.Content.ReadAsAsync<List<IUser>>()
      
      return users
        .Where(u => u.Active)
        .Select(u => new {
          Id = u.Id,
          Name = u.Name.ToUpper(),
          Active = u.Active
        })
        .ToList()
    }
  }
}
```

## Important Notes
- Use PascalCase for public members and methods
- Use camelCase for private fields and local variables
- Always use `async/await` for async operations
- Implement IDisposable for resource cleanup
- Use dependency injection for services
- Create interfaces for abstraction
- Use LINQ for collection operations
- Preserve all business logic
- Add XML documentation comments
- Follow .NET naming conventions
