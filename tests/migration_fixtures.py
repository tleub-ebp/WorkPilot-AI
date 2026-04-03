"""
Test fixtures for migration testing
Sample projects for testing transformations
"""

# React test fixture
REACT_COMPONENT_EXAMPLE = """
import React, { useState, useCallback, useEffect } from 'react'

function Counter({ initialValue = 0, onCountChange }) {
  const [count, setCount] = useState(initialValue)
  const [isDoubled, setIsDoubled] = useState(false)
  
  const increment = useCallback(() => {
    const newCount = count + 1
    setCount(newCount)
    onCountChange?.(newCount)
  }, [count, onCountChange])
  
  useEffect(() => {
    setIsDoubled(count > 5)
  }, [count])
  
  return (
    <div className="counter">
      <h2>Counter: {count}</h2>
      {isDoubled && <p className="warning">Count is doubled!</p>}
      <button onClick={increment} className="btn">
        Increment
      </button>
      {count > 0 && (
        <button onClick={() => setCount(0)} className="btn-secondary">
          Reset
        </button>
      )}
    </div>
  )
}

export default Counter
"""

# MySQL test fixture
MYSQL_SCHEMA_EXAMPLE = """
CREATE TABLE users (
  id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  email VARCHAR(255) NOT NULL UNIQUE,
  username VARCHAR(100) NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  is_active BOOLEAN DEFAULT true
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE posts (
  id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  title VARCHAR(255) NOT NULL,
  content LONGTEXT NOT NULL,
  status ENUM('draft', 'published', 'archived') DEFAULT 'draft',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  KEY idx_status (status),
  FULLTEXT INDEX ft_title (title)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE comments (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  post_id INT NOT NULL,
  author_id INT NOT NULL,
  content TEXT NOT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE,
  FOREIGN KEY (author_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB;
"""

# Python 2 test fixture
PYTHON2_CODE_EXAMPLE = """
#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function

import sys
import MySQLdb
from itertools import izip

class Database(object):
    def __init__(self, host, user, passwd, db):
        self.connection = MySQLdb.connect(
            host=host,
            user=user,
            passwd=passwd,
            db=db
        )
        self.cursor = self.connection.cursor()
    
    def query(self, sql):
        try:
            self.cursor.execute(sql)
            return self.cursor.fetchall()
        except MySQLdb.Error as e:
            print "Database error: %s" % e
            return None
    
    def get_user(self, user_id):
        sql = "SELECT * FROM users WHERE id = %s" % user_id
        result = self.query(sql)
        if result:
            user_dict = {
                'id': result[0][0],
                'name': unicode(result[0][1]),
                'email': result[0][2]
            }
            return user_dict
        return None
    
    def close(self):
        self.cursor.close()
        self.connection.close()

def main():
    db = Database('localhost', 'root', 'password', 'mydb')
    
    # Old-style string formatting
    user_id = 1
    print "Getting user %d..." % user_id
    
    user = db.get_user(user_id)
    if user:
        print "User: %s <%s>" % (user['name'], user['email'])
    else:
        print "User not found"
    
    db.close()

if __name__ == '__main__':
    main()
"""

# JavaScript test fixture
JAVASCRIPT_CODE_EXAMPLE = """
function calculateTotal(items) {
  return items.reduce(function(sum, item) {
    return sum + item.price * item.quantity
  }, 0)
}

function filterByPrice(items, maxPrice) {
  return items.filter(function(item) {
    return item.price <= maxPrice
  })
}

const user = {
  id: 1,
  name: 'John',
  email: 'john@example.com',
  addresses: [
    { street: '123 Main St', city: 'Boston' }
  ]
}

function displayUser(user) {
  const output = 'User: ' + user.name + ' <' + user.email + '>'
  console.log(output)
}

const asyncFetch = async function(url) {
  const response = await fetch(url)
  const data = await response.json()
  return data
}
"""

# REST API test fixture
REST_API_EXAMPLE = """
// Express.js REST API
app.get('/api/users', (req, res) => {
  const limit = req.query.limit || 10
  const offset = req.query.offset || 0
  
  User.findAll({ limit, offset })
    .then(users => res.json({ data: users, total: users.length }))
    .catch(err => res.status(500).json({ error: err.message }))
})

app.get('/api/users/:id', (req, res) => {
  User.findById(req.params.id)
    .then(user => {
      if (!user) return res.status(404).json({ error: 'Not found' })
      res.json(user)
    })
    .catch(err => res.status(500).json({ error: err.message }))
})

app.post('/api/users', (req, res) => {
  const { name, email } = req.body
  
  User.create({ name, email })
    .then(user => res.status(201).json(user))
    .catch(err => res.status(400).json({ error: err.message }))
})

app.put('/api/users/:id', (req, res) => {
  const { name, email } = req.body
  
  User.findById(req.params.id)
    .then(user => {
      return user.update({ name, email })
    })
    .then(user => res.json(user))
    .catch(err => res.status(500).json({ error: err.message }))
})

app.delete('/api/users/:id', (req, res) => {
  User.findById(req.params.id)
    .then(user => user.destroy())
    .then(() => res.status(204).send())
    .catch(err => res.status(500).json({ error: err.message }))
})
"""

# React to Angular test fixture
REACT_ANGULAR_COMPONENT_EXAMPLE = """
import React, { useState, useEffect } from 'react'

function UserProfile({ userId, onUserChange }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    setLoading(true)
    fetch(`/api/users/${userId}`)
      .then(r => r.json())
      .then(data => {
        setUser(data)
        setLoading(false)
      })
  }, [userId])

  const handleUpdate = () => {
    if (user) {
      onUserChange?.(user)
    }
  }

  return (
    <div className="profile">
      {loading && <p>Loading...</p>}
      {user && (
        <div>
          <h1>{user.name}</h1>
          <p>{user.email}</p>
          <button onClick={handleUpdate}>Update Profile</button>
        </div>
      )}
    </div>
  )
}

export default UserProfile
"""

# JavaScript to C# test fixture
JS_TO_CSHARP_SERVICE_EXAMPLE = """
import axios from 'axios'

class UserService {
  constructor() {
    this.baseUrl = 'https://api.example.com'
    this.client = axios.create()
  }

  async getUser(id) {
    const response = await this.client.get(`${this.baseUrl}/users/${id}`)
    return response.data
  }

  async getAllUsers() {
    const response = await this.client.get(`${this.baseUrl}/users`)
    return response.data
      .filter(u => u.active)
      .map(u => ({
        id: u.id,
        name: u.name.toUpperCase(),
        email: u.email.toLowerCase()
      }))
      .sort((a, b) => a.name.localeCompare(b.name))
  }

  async createUser(userData) {
    try {
      const response = await this.client.post(`${this.baseUrl}/users`, userData)
      return response.data
    } catch (error) {
      console.error(`Failed to create user: ${error.message}`)
      throw error
    }
  }

  async deleteUser(id) {
    await this.client.delete(`${this.baseUrl}/users/${id}`)
    return true
  }
}

export default UserService
"""

# Test metadata
TEST_FIXTURES = {
    'react_component': {
        'filename': 'Counter.jsx',
        'content': REACT_COMPONENT_EXAMPLE,
        'migration_type': 'react_to_vue',
        'expected_output_filename': 'Counter.vue'
    },
    'mysql_schema': {
        'filename': 'schema.sql',
        'content': MYSQL_SCHEMA_EXAMPLE,
        'migration_type': 'mysql_to_postgresql',
        'expected_output_filename': 'schema.sql'
    },
    'python2_code': {
        'filename': 'database.py',
        'content': PYTHON2_CODE_EXAMPLE,
        'migration_type': 'python2_to_3',
        'expected_output_filename': 'database.py'
    },
    'javascript_code': {
        'filename': 'utils.js',
        'content': JAVASCRIPT_CODE_EXAMPLE,
        'migration_type': 'js_to_ts',
        'expected_output_filename': 'utils.ts'
    },
    'rest_api': {
        'filename': 'routes.js',
        'content': REST_API_EXAMPLE,
        'migration_type': 'rest_to_graphql',
        'expected_output_filename': 'schema.graphql'
    },
    'react_angular_component': {
        'filename': 'UserProfile.jsx',
        'content': REACT_ANGULAR_COMPONENT_EXAMPLE,
        'migration_type': 'react_to_angular',
        'expected_output_filename': 'user-profile.component.ts'
    },
    'js_to_csharp_service': {
        'filename': 'UserService.js',
        'content': JS_TO_CSHARP_SERVICE_EXAMPLE,
        'migration_type': 'js_to_csharp',
        'expected_output_filename': 'UserService.cs'
    }
}
