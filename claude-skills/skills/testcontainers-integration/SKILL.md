name: testcontainers-integration
description: Expertise TestContainers pour tests d'intégration distribués avec Docker. Patterns production pour PostgreSQL, Redis, RabbitMQ, et services cloud-native.
license: Complete terms in LICENSE.txt
---

# TestContainers Integration - Tests d'Intégration Distribués

## Vue d'ensemble

Skill spécialisé dans TestContainers pour créer des tests d'intégration distribués avec des conteneurs Docker réels, assurant la fiabilité des tests dans des environnements isolés.

**Mots-clés**: TestContainers, Docker, tests d'intégration, PostgreSQL, Redis, RabbitMQ, microservices, isolation de tests, CI/CD

## 🎯 Compétences Principales

### Container Management
- **Docker Containers**: Gestion de conteneurs pour tests
- **Lifecycle Management**: Démarrage/arrêt automatique des services
- **Resource Cleanup**: Nettoyage des ressources après tests
- **Port Mapping**: Configuration des ports dynamiques

### Database Testing
- **PostgreSQL**: Tests avec base de données PostgreSQL réelle
- **MySQL**: Tests avec base de données MySQL
- **Redis**: Tests avec cache Redis
- **MongoDB**: Tests avec base de données NoSQL

### Message Broker Testing
- **RabbitMQ**: Tests avec broker de messages
- **Kafka**: Tests avec streaming platform
- **Azure Service Bus**: Tests avec broker cloud
- **SQS**: Tests avec broker AWS

### Service Integration
- **API Testing**: Tests d'API avec services réels
- **Microservices**: Tests d'intégration entre services
- **Web Applications**: Tests E2E avec navigateur
- **Background Services**: Tests de services asynchrones

## 🛠️ Patterns Production

### 1. PostgreSQL Integration Tests
```csharp
// TestContainer PostgreSQL setup
public class PostgreSqlTestFixture : IDisposable
{
    private readonly TestcontainersContainer _container;
    private readonly string _connectionString;
    
    public PostgreSqlTestFixture()
    {
        // Configuration du conteneur PostgreSQL
        var containerBuilder = new TestcontainersBuilder<PostgreSqlTestcontainer>()
            .WithImage("postgres:15-alpine")
            .WithDatabase("testdb")
            .WithUsername("testuser")
            .WithPassword("testpass")
            .WithPortBinding(5432, true) // Port dynamique
            .WithWaitStrategy(Wait.ForUnixContainer()
                .UntilPortIsAvailable(5432)
                .UntilCommandIsCompleted("pg_isready -U testuser -d testdb")
                .WithStartupTimeout(TimeSpan.FromMinutes(2)))
            .WithEnvironment("POSTGRES_INITDB_ARGS", "--encoding=UTF-8")
            .WithEnvironment("PGTZ", "UTC");
        
        _container = containerBuilder.Build();
        _container.StartAsync().Wait();
        
        // Construction de la chaîne de connexion
        var port = _container.GetMappedPublicPort(5432);
        _connectionString = $"Host=localhost;Port={port};Database=testdb;Username=testuser;Password=testpass;";
        
        // Initialisation de la base de données
        InitializeDatabase();
    }
    
    public string ConnectionString => _connectionString;
    public int Port => _container.GetMappedPublicPort(5432);
    
    private void InitializeDatabase()
    {
        using var connection = new NpgsqlConnection(_connectionString);
        connection.Open();
        
        // Création des tables de test
        var createTablesSql = @"
            CREATE TABLE IF NOT EXISTS customers (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                name VARCHAR(255) NOT NULL,
                email VARCHAR(255) UNIQUE NOT NULL,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );
            
            CREATE TABLE IF NOT EXISTS orders (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                customer_id UUID NOT NULL REFERENCES customers(id),
                total_amount DECIMAL(10,2) NOT NULL,
                status VARCHAR(50) NOT NULL DEFAULT 'pending',
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );
            
            CREATE INDEX IF NOT EXISTS idx_orders_customer_id ON orders(customer_id);
            CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
        ";
        
        using var command = new NpgsqlCommand(createTablesSql, connection);
        command.ExecuteNonQuery();
    }
    
    public void Dispose()
    {
        _container?.StopAsync().Wait();
        _container?.DisposeAsync().Wait();
    }
}

// Tests d'intégration avec PostgreSQL
public class OrderRepositoryIntegrationTests : IClassFixture<PostgreSqlTestFixture>
{
    private readonly PostgreSqlTestFixture _fixture;
    private readonly OrderDbContext _dbContext;
    private readonly OrderRepository _repository;
    
    public OrderRepositoryIntegrationTests(PostgreSqlTestFixture fixture)
    {
        _fixture = fixture;
        
        var options = new DbContextOptionsBuilder<OrderDbContext>()
            .UseNpgsql(_fixture.ConnectionString)
            .Options;
            
        _dbContext = new OrderDbContext(options);
        _dbContext.Database.EnsureCreated();
        
        _repository = new OrderRepository(_dbContext);
    }
    
    [Fact]
    public async Task CreateOrder_ShouldPersistOrder_WhenValidOrder()
    {
        // Arrange
        var customer = await CreateTestCustomer();
        var order = new Order
        {
            CustomerId = customer.Id,
            TotalAmount = 99.99m,
            Status = "pending"
        };
        
        // Act
        var createdOrder = await _repository.CreateAsync(order);
        
        // Assert
        createdOrder.Should().NotBeNull();
        createdOrder.Id.Should().NotBe(Guid.Empty);
        createdOrder.CustomerId.Should().Be(customer.Id);
        createdOrder.TotalAmount.Should().Be(99.99m);
        createdOrder.Status.Should().Be("pending");
        
        // Verify in database
        var savedOrder = await _dbContext.Orders.FindAsync(createdOrder.Id);
        savedOrder.Should().NotBeNull();
        savedOrder.CustomerId.Should().Be(customer.Id);
    }
    
    [Fact]
    public async Task GetOrdersByCustomer_ShouldReturnOrders_WhenCustomerExists()
    {
        // Arrange
        var customer = await CreateTestCustomer();
        var orders = new[]
        {
            new Order { CustomerId = customer.Id, TotalAmount = 49.99m, Status = "pending" },
            new Order { CustomerId = customer.Id, TotalAmount = 29.99m, Status = "confirmed" },
            new Order { CustomerId = customer.Id, TotalAmount = 19.99m, Status = "shipped" }
        };
        
        foreach (var order in orders)
        {
            await _repository.CreateAsync(order);
        }
        
        // Act
        var customerOrders = await _repository.GetByCustomerIdAsync(customer.Id);
        
        // Assert
        customerOrders.Should().HaveCount(3);
        customerOrders.Should().OnlyContain(o => o.CustomerId == customer.Id);
    }
    
    private async Task<Customer> CreateTestCustomer()
    {
        var customer = new Customer
        {
            Name = "Test Customer",
            Email = "test@example.com"
        };
        
        _dbContext.Customers.Add(customer);
        await _dbContext.SaveChangesAsync();
        
        return customer;
    }
    
    public void Dispose()
    {
        _dbContext?.Dispose();
    }
}
```

### 2. Redis Integration Tests
```csharp
// TestContainer Redis setup
public class RedisTestFixture : IDisposable
{
    private readonly TestcontainersContainer _container;
    private readonly string _connectionString;
    private readonly IConnectionMultiplexer _redis;
    
    public RedisTestFixture()
    {
        var containerBuilder = new TestcontainersBuilder<RedisTestcontainer>()
            .WithImage("redis:7-alpine")
            .WithPortBinding(6379, true)
            .WithWaitStrategy(Wait.ForUnixContainer()
                .UntilPortIsAvailable(6379)
                .UntilCommandIsCompleted("redis-cli ping")
                .WithStartupTimeout(TimeSpan.FromMinutes(1)));
        
        _container = containerBuilder.Build();
        _container.StartAsync().Wait();
        
        var port = _container.GetMappedPublicPort(6379);
        _connectionString = $"localhost:{port}";
        
        var options = ConfigurationOptions.Parse(_connectionString);
        _redis = ConnectionMultiplexer.Connect(options);
    }
    
    public IConnectionMultiplexer Redis => _redis;
    public IDatabase Database => _redis.GetDatabase();
    public string ConnectionString => _connectionString;
    
    public void Dispose()
    {
        _redis?.Dispose();
        _container?.StopAsync().Wait();
        _container?.DisposeAsync().Wait();
    }
}

// Tests avec Redis
public class CacheServiceIntegrationTests : IClassFixture<RedisTestFixture>
{
    private readonly RedisTestFixture _fixture;
    private readonly ICacheService _cacheService;
    
    public CacheServiceIntegrationTests(RedisTestFixture fixture)
    {
        _fixture = fixture;
        _cacheService = new RedisCacheService(_fixture.Database);
    }
    
    [Fact]
    public async Task SetAndGet_ShouldReturnCachedValue_WhenKeyExists()
    {
        // Arrange
        var key = "test:key";
        var value = new TestData { Id = 1, Name = "Test", CreatedAt = DateTime.UtcNow };
        
        // Act
        await _cacheService.SetAsync(key, value, TimeSpan.FromMinutes(5));
        var cachedValue = await _cacheService.GetAsync<TestData>(key);
        
        // Assert
        cachedValue.Should().NotBeNull();
        cachedValue.Id.Should().Be(value.Id);
        cachedValue.Name.Should().Be(value.Name);
        cachedValue.CreatedAt.Should().BeCloseTo(value.CreatedAt, TimeSpan.FromSeconds(1));
    }
    
    [Fact]
    public async Task SetWithExpiration_ShouldExpire_WhenTimeElapsed()
    {
        // Arrange
        var key = "test:expiration";
        var value = new TestData { Id = 2, Name = "Expiration Test" };
        
        // Act
        await _cacheService.SetAsync(key, value, TimeSpan.FromMilliseconds(100));
        
        // Wait for expiration
        await Task.Delay(200);
        
        var cachedValue = await _cacheService.GetAsync<TestData>(key);
        
        // Assert
        cachedValue.Should().BeNull();
    }
    
    [Fact]
    public async Task ConcurrentAccess_ShouldHandleMultipleOperations_WhenSimultaneousRequests()
    {
        // Arrange
        var tasks = new List<Task>();
        var keyPrefix = "test:concurrent:";
        
        // Act - Simulate concurrent cache operations
        for (int i = 0; i < 100; i++)
        {
            var index = i;
            tasks.Add(Task.Run(async () =>
            {
                var key = $"{keyPrefix}{index}";
                var value = new TestData { Id = index, Name = $"Item {index}" };
                
                await _cacheService.SetAsync(key, value, TimeSpan.FromMinutes(1));
                var retrieved = await _cacheService.GetAsync<TestData>(key);
                
                retrieved.Should().NotBeNull();
                retrieved.Id.Should().Be(index);
            }));
        }
        
        // Assert
        await Task.WhenAll(tasks);
    }
    
    private class TestData
    {
        public int Id { get; set; }
        public string Name { get; set; }
        public DateTime CreatedAt { get; set; }
    }
}
```

### 3. RabbitMQ Integration Tests
```csharp
// TestContainer RabbitMQ setup
public class RabbitMqTestFixture : IDisposable
{
    private readonly TestcontainersContainer _container;
    private readonly string _connectionString;
    private readonly IConnection _connection;
    private readonly IModel _channel;
    
    public RabbitMqTestFixture()
    {
        var containerBuilder = new TestcontainersBuilder<RabbitMqTestcontainer>()
            .WithImage("rabbitmq:3-management-alpine")
            .WithPortBinding(5672, true) // AMQP port
            .WithPortBinding(15672, true) // Management UI port
            .WithEnvironment("RABBITMQ_DEFAULT_USER", "testuser")
            .WithEnvironment("RABBITMQ_DEFAULT_PASS", "testpass")
            .WithEnvironment("RABBITMQ_DEFAULT_VHOST", "testvhost")
            .WithWaitStrategy(Wait.ForUnixContainer()
                .UntilPortIsAvailable(5672)
                .UntilCommandIsCompleted("rabbitmq-diagnostics check_port_connectivity")
                .WithStartupTimeout(TimeSpan.FromMinutes(2)));
        
        _container = containerBuilder.Build();
        _container.StartAsync().Wait();
        
        var amqpPort = _container.GetMappedPublicPort(5672);
        _connectionString = $"amqp://testuser:testpass@localhost:{amqpPort}/testvhost";
        
        var factory = new ConnectionFactory
        {
            Uri = new Uri(_connectionString),
            AutomaticRecoveryEnabled = true,
            NetworkRecoveryInterval = TimeSpan.FromSeconds(10)
        };
        
        _connection = factory.CreateConnection();
        _channel = _connection.CreateModel();
        
        // Declare test exchanges and queues
        SetupTestInfrastructure();
    }
    
    public IConnection Connection => _connection;
    public IModel Channel => _channel;
    public string ConnectionString => _connectionString;
    public int ManagementPort => _container.GetMappedPublicPort(15672);
    
    private void SetupTestInfrastructure()
    {
        // Declare exchanges
        _channel.ExchangeDeclare("test.direct", ExchangeType.Direct, durable: true);
        _channel.ExchangeDeclare("test.fanout", ExchangeType.Fanout, durable: true);
        _channel.ExchangeDeclare("test.topic", ExchangeType.Topic, durable: true);
        
        // Declare queues
        _channel.QueueDeclare("test.queue1", durable: true, exclusive: false, autoDelete: false);
        _channel.QueueDeclare("test.queue2", durable: true, exclusive: false, autoDelete: false);
        
        // Bind queues to exchanges
        _channel.QueueBind("test.queue1", "test.direct", "routing.key1");
        _channel.QueueBind("test.queue2", "test.direct", "routing.key2");
        _channel.QueueBind("test.queue1", "test.fanout", "");
        _channel.QueueBind("test.queue2", "test.fanout", "");
    }
    
    public void Dispose()
    {
        _channel?.Dispose();
        _connection?.Dispose();
        _container?.StopAsync().Wait();
        _container?.DisposeAsync().Wait();
    }
}

// Tests avec RabbitMQ
public class MessageBrokerIntegrationTests : IClassFixture<RabbitMqTestFixture>
{
    private readonly RabbitMqTestFixture _fixture;
    private readonly IMessageBrokerService _brokerService;
    
    public MessageBrokerIntegrationTests(RabbitMqTestFixture fixture)
    {
        _fixture = fixture;
        _brokerService = new RabbitMqMessageBrokerService(_fixture.Connection);
    }
    
    [Fact]
    public async Task PublishAndSubscribe_ShouldDeliverMessage_WhenValidRouting()
    {
        // Arrange
        var message = new OrderCreatedEvent
        {
            OrderId = Guid.NewGuid(),
            CustomerId = Guid.NewGuid(),
            TotalAmount = 99.99m,
            CreatedAt = DateTime.UtcNow
        };
        
        var receivedMessage = new TaskCompletionSource<OrderCreatedEvent>();
        
        // Subscribe to message
        await _brokerService.SubscribeAsync<OrderCreatedEvent>("test.queue1", msg =>
        {
            receivedMessage.SetResult(msg);
        });
        
        // Act
        await _brokerService.PublishAsync(message, "test.direct", "routing.key1");
        
        // Assert
        var result = await receivedMessage.Task.WaitAsync(TimeSpan.FromSeconds(5));
        result.Should().NotBeNull();
        result.OrderId.Should().Be(message.OrderId);
        result.CustomerId.Should().Be(message.CustomerId);
        result.TotalAmount.Should().Be(message.TotalAmount);
    }
    
    [Fact]
    public async Task PublishMultipleMessages_ShouldDeliverAll_WhenBatchPublish()
    {
        // Arrange
        var messages = Enumerable.Range(1, 100)
            .Select(i => new OrderCreatedEvent
            {
                OrderId = Guid.NewGuid(),
                CustomerId = Guid.NewGuid(),
                TotalAmount = i * 10m,
                CreatedAt = DateTime.UtcNow
            })
            .ToList();
        
        var receivedCount = 0;
        var receivedMessages = new ConcurrentBag<OrderCreatedEvent>();
        
        // Subscribe to messages
        await _brokerService.SubscribeAsync<OrderCreatedEvent>("test.queue1", msg =>
        {
            Interlocked.Increment(ref receivedCount);
            receivedMessages.Add(msg);
        });
        
        // Act
        await _brokerService.PublishBatchAsync(messages, "test.direct", "routing.key1");
        
        // Wait for all messages
        await Task.Delay(TimeSpan.FromSeconds(2));
        
        // Assert
        receivedCount.Should().Be(100);
        receivedMessages.Should().HaveCount(100);
        
        foreach (var originalMessage in messages)
        {
            receivedMessages.Should().Contain(m => m.OrderId == originalMessage.OrderId);
        }
    }
    
    [Fact]
    public async Task DeadLetterQueue_ShouldRouteFailedMessages_WhenProcessingFails()
    {
        // Arrange
        var message = new OrderCreatedEvent
        {
            OrderId = Guid.NewGuid(),
            CustomerId = Guid.NewGuid(),
            TotalAmount = 99.99m,
            CreatedAt = DateTime.UtcNow
        };
        
        // Setup dead letter queue
        await _fixture.Channel.QueueDeclare("test.dlq", durable: true, exclusive: false, autoDelete: false);
        await _fixture.Channel.QueueBind("test.dlq", "test.direct", "routing.dlq");
        
        // Subscribe with failure simulation
        await _brokerService.SubscribeAsync<OrderCreatedEvent>("test.queue1", msg =>
        {
            throw new InvalidOperationException("Simulated processing failure");
        });
        
        // Act
        await _brokerService.PublishAsync(message, "test.direct", "routing.key1");
        
        // Wait for message to be dead-lettered
        await Task.Delay(TimeSpan.FromSeconds(2));
        
        // Assert - Check dead letter queue
        var deadLetterMessage = await GetDeadLetterMessage();
        deadLetterMessage.Should().NotBeNull();
        deadLetterMessage.OrderId.Should().Be(message.OrderId);
    }
    
    private async Task<OrderCreatedEvent> GetDeadLetterMessage()
    {
        var consumer = new EventingBasicConsumer(_fixture.Channel);
        var messageTask = new TaskCompletionSource<OrderCreatedEvent>();
        
        consumer.Received += (model, ea) =>
        {
            var body = ea.Body.ToArray();
            var message = JsonSerializer.Deserialize<OrderCreatedEvent>(body);
            messageTask.SetResult(message);
        };
        
        _fixture.Channel.BasicConsume("test.dlq", false, consumer);
        
        return await messageTask.Task.WaitAsync(TimeSpan.FromSeconds(5));
    }
    
    private class OrderCreatedEvent
    {
        public Guid OrderId { get; set; }
        public Guid CustomerId { get; set; }
        public decimal TotalAmount { get; set; }
        public DateTime CreatedAt { get; set; }
    }
}
```

### 4. Multi-Service Integration Tests
```csharp
// TestContainer pour environnement multi-services
public class MultiServiceTestFixture : IDisposable
{
    private readonly Dictionary<string, TestcontainersContainer> _containers;
    private readonly Dictionary<string, string> _connectionStrings;
    
    public MultiServiceTestFixture()
    {
        _containers = new Dictionary<string, TestcontainersContainer>();
        _connectionStrings = new Dictionary<string, string>();
        
        SetupPostgres();
        SetupRedis();
        SetupRabbitMQ();
        SetupElasticsearch();
        
        // Wait for all services to be ready
        Task.WaitAll(_containers.Values.Select(c => c.StartAsync())).Wait();
        
        // Build connection strings
        BuildConnectionStrings();
    }
    
    private void SetupPostgres()
    {
        var container = new TestcontainersBuilder<PostgreSqlTestcontainer>()
            .WithImage("postgres:15-alpine")
            .WithDatabase("integrationdb")
            .WithUsername("integrationuser")
            .WithPassword("integrationpass")
            .WithPortBinding(5432, true)
            .WithWaitStrategy(Wait.ForUnixContainer()
                .UntilPortIsAvailable(5432)
                .UntilCommandIsCompleted("pg_isready -U integrationuser -d integrationdb"))
            .Build();
            
        _containers["postgres"] = container;
    }
    
    private void SetupRedis()
    {
        var container = new TestcontainersBuilder<RedisTestcontainer>()
            .WithImage("redis:7-alpine")
            .WithPortBinding(6379, true)
            .WithWaitStrategy(Wait.ForUnixContainer()
                .UntilPortIsAvailable(6379)
                .UntilCommandIsCompleted("redis-cli ping"))
            .Build();
            
        _containers["redis"] = container;
    }
    
    private void SetupRabbitMQ()
    {
        var container = new TestcontainersBuilder<RabbitMqTestcontainer>()
            .WithImage("rabbitmq:3-management-alpine")
            .WithEnvironment("RABBITMQ_DEFAULT_USER", "integrationuser")
            .WithEnvironment("RABBITMQ_DEFAULT_PASS", "integrationpass")
            .WithPortBinding(5672, true)
            .WithPortBinding(15672, true)
            .WithWaitStrategy(Wait.ForUnixContainer()
                .UntilPortIsAvailable(5672)
                .UntilCommandIsCompleted("rabbitmq-diagnostics check_port_connectivity"))
            .Build();
            
        _containers["rabbitmq"] = container;
    }
    
    private void SetupElasticsearch()
    {
        var container = new TestcontainersBuilder<ElasticsearchTestcontainer>()
            .WithImage("docker.elastic.co/elasticsearch/elasticsearch:8.8.0")
            .WithEnvironment("discovery.type", "single-node")
            .WithEnvironment("xpack.security.enabled", "false")
            .WithPortBinding(9200, true)
            .WithPortBinding(9300, true)
            .WithWaitStrategy(Wait.ForUnixContainer()
                .UntilPortIsAvailable(9200)
                .UntilHttpRequestIsSucceeded("http://localhost:9200/_cluster/health"))
            .Build();
            
        _containers["elasticsearch"] = container;
    }
    
    private void BuildConnectionStrings()
    {
        // PostgreSQL
        var pgPort = _containers["postgres"].GetMappedPublicPort(5432);
        _connectionStrings["postgres"] = $"Host=localhost;Port={pgPort};Database=integrationdb;Username=integrationuser;Password=integrationpass";
        
        // Redis
        var redisPort = _containers["redis"].GetMappedPublicPort(6379);
        _connectionStrings["redis"] = $"localhost:{redisPort}";
        
        // RabbitMQ
        var rabbitPort = _containers["rabbitmq"].GetMappedPublicPort(5672);
        _connectionStrings["rabbitmq"] = $"amqp://integrationuser:integrationpass@localhost:{rabbitPort}/";
        
        // Elasticsearch
        var esPort = _containers["elasticsearch"].GetMappedPublicPort(9200);
        _connectionStrings["elasticsearch"] = $"http://localhost:{esPort}";
    }
    
    public string GetConnectionString(string service) => _connectionStrings[service];
    public int GetPort(string service) => _containers[service].GetMappedPublicPort(GetDefaultPort(service));
    
    private int GetDefaultPort(string service) => service switch
    {
        "postgres" => 5432,
        "redis" => 6379,
        "rabbitmq" => 5672,
        "elasticsearch" => 9200,
        _ => throw new ArgumentException($"Unknown service: {service}")
    };
    
    public void Dispose()
    {
        foreach (var container in _containers.Values)
        {
            container.StopAsync().Wait();
            container.DisposeAsync().Wait();
        }
    }
}

// Tests d'intégration multi-services
public class OrderProcessingIntegrationTests : IClassFixture<MultiServiceTestFixture>
{
    private readonly MultiServiceTestFixture _fixture;
    private readonly OrderProcessingService _orderService;
    
    public OrderProcessingIntegrationTests(MultiServiceTestFixture fixture)
    {
        _fixture = fixture;
        
        // Configure services with TestContainers connection strings
        var services = new ServiceCollection();
        
        services.AddDbContext<OrderDbContext>(options =>
            options.UseNpgsql(_fixture.GetConnectionString("postgres")));
            
        services.AddSingleton<IConnectionMultiplexer>(provider =>
            ConnectionMultiplexer.Connect(_fixture.GetConnectionString("redis")));
            
        services.AddSingleton<IConnection>(provider =>
        {
            var factory = new ConnectionFactory
            {
                Uri = new Uri(_fixture.GetConnectionString("rabbitmq")),
                AutomaticRecoveryEnabled = true
            };
            return factory.CreateConnection();
        });
        
        services.AddScoped<IOrderRepository, OrderRepository>();
        services.AddScoped<ICacheService, RedisCacheService>();
        services.AddScoped<IMessageBrokerService, RabbitMqMessageBrokerService>();
        services.AddScoped<OrderProcessingService>();
        
        var serviceProvider = services.BuildServiceProvider();
        _orderService = serviceProvider.GetRequiredService<OrderProcessingService>();
    }
    
    [Fact]
    public async Task ProcessOrder_ShouldPersistAndNotify_WhenValidOrder()
    {
        // Arrange
        var orderRequest = new ProcessOrderRequest
        {
            CustomerId = Guid.NewGuid(),
            Items = new[]
            {
                new OrderItem { ProductId = Guid.NewGuid(), Quantity = 2, UnitPrice = 29.99m },
                new OrderItem { ProductId = Guid.NewGuid(), Quantity = 1, UnitPrice = 49.99m }
            }
        };
        
        // Act
        var result = await _orderService.ProcessOrderAsync(orderRequest);
        
        // Assert
        result.Should().NotBeNull();
        result.Success.Should().BeTrue();
        result.OrderId.Should().NotBe(Guid.Empty());
        result.TotalAmount.Should().Be(109.97m);
        
        // Verify order was persisted
        var persistedOrder = await GetOrderFromDatabase(result.OrderId);
        persistedOrder.Should().NotBeNull();
        persistedOrder.Status.Should().Be("processed");
        
        // Verify cache was updated
        var cachedOrder = await GetOrderFromCache(result.OrderId);
        cachedOrder.Should().NotBeNull();
        cachedOrder.Status.Should().Be("processed");
        
        // Verify notification was sent
        var notification = await GetNotificationFromQueue(result.OrderId);
        notification.Should().NotBeNull();
        notification.EventType.Should().Be("OrderProcessed");
    }
    
    private async Task<Order> GetOrderFromDatabase(Guid orderId)
    {
        // Implementation to retrieve order from PostgreSQL
        using var connection = new NpgsqlConnection(_fixture.GetConnectionString("postgres"));
        await connection.OpenAsync();
        
        var sql = "SELECT * FROM orders WHERE id = @id";
        using var command = new NpgsqlCommand(sql, connection);
        command.Parameters.AddWithValue("id", orderId);
        
        using var reader = await command.ExecuteReaderAsync();
        if (await reader.ReadAsync())
        {
            return new Order
            {
                Id = reader.GetGuid("id"),
                CustomerId = reader.GetGuid("customer_id"),
                TotalAmount = reader.GetDecimal("total_amount"),
                Status = reader.GetString("status"),
                CreatedAt = reader.GetDateTime("created_at")
            };
        }
        
        return null;
    }
    
    private async Task<Order> GetOrderFromCache(Guid orderId)
    {
        // Implementation to retrieve order from Redis
        var redis = ConnectionMultiplexer.Connect(_fixture.GetConnectionString("redis"));
        var db = redis.GetDatabase();
        
        var key = $"order:{orderId}";
        var json = await db.StringGetAsync(key);
        
        if (json.HasValue)
        {
            return JsonSerializer.Deserialize<Order>(json);
        }
        
        return null;
    }
    
    private async Task<OrderNotification> GetNotificationFromQueue(Guid orderId)
    {
        // Implementation to retrieve notification from RabbitMQ
        var factory = new ConnectionFactory
        {
            Uri = new Uri(_fixture.GetConnectionString("rabbitmq")),
            AutomaticRecoveryEnabled = true
        };
        
        using var connection = factory.CreateConnection();
        using var channel = connection.CreateModel();
        
        var consumer = new EventingBasicConsumer(channel);
        var notificationTask = new TaskCompletionSource<OrderNotification>();
        
        consumer.Received += (model, ea) =>
        {
            var body = ea.Body.ToArray();
            var notification = JsonSerializer.Deserialize<OrderNotification>(body);
            
            if (notification.OrderId == orderId)
            {
                notificationTask.SetResult(notification);
            }
        };
        
        channel.BasicConsume("order.notifications", false, consumer);
        
        return await notificationTask.Task.WaitAsync(TimeSpan.FromSeconds(5));
    }
    
    private class Order
    {
        public Guid Id { get; set; }
        public Guid CustomerId { get; set; }
        public decimal TotalAmount { get; set; }
        public string Status { get; set; }
        public DateTime CreatedAt { get; set; }
    }
    
    private class OrderNotification
    {
        public Guid OrderId { get; set; }
        public string EventType { get; set; }
        public DateTime Timestamp { get; set; }
    }
}
```

### 5. CI/CD Integration avec GitHub Actions
```yaml
# .github/workflows/integration-tests.yml
name: Integration Tests

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  integration-tests:
    runs-on: ubuntu-latest
    
    services:
      docker:
        image: docker:24.0.5
        options: --privileged
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Setup .NET
      uses: actions/setup-dotnet@v3
      with:
        dotnet-version: '10.0.x'
    
    - name: Start TestContainers
      run: |
        docker compose -f docker-compose.test.yml up -d
        sleep 30
    
    - name: Wait for services
      run: |
        timeout 300 bash -c 'until curl -f http://localhost:5432/health; do sleep 5; done'
        timeout 300 bash -c 'until curl -f http://localhost:6379/health; do sleep 5; done'
        timeout 300 bash -c 'until curl -f http://localhost:5672/health; do sleep 5; done'
    
    - name: Run integration tests
      run: |
        dotnet test --configuration Release \
          --logger "console;verbosity=detailed" \
          --results-path TestResults \
          --collect:"XPlat Code Coverage"
    
    - name: Upload coverage
      uses: codecov/codecov-action@v3
      with:
        file: ./TestResults/coverage.cobertura.xml
    
    - name: Stop TestContainers
      if: always()
      run: |
        docker compose -f docker-compose.test.yml down -v
    
    - name: Cleanup
      if: always()
      run: |
        docker system prune -f
```

### 6. Docker Compose pour Tests
```yaml
# docker-compose.test.yml
version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: integrationdb
      POSTGRES_USER: integrationuser
      POSTGRES_PASSWORD: integrationpass
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./scripts/init-postgres.sql:/docker-entrypoint-initdb.d/init.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U integrationuser -d integrationdb"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 30s

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  rabbitmq:
    image: rabbitmq:3-management-alpine
    environment:
      RABBITMQ_DEFAULT_USER: integrationuser
      RABBITMQ_DEFAULT_PASS: integrationpass
    ports:
      - "5672:5672"
      - "15672:15672"
    volumes:
      - rabbitmq_data:/var/lib/rabbitmq
    healthcheck:
      test: ["CMD", "rabbitmq-diagnostics", "ping"]
      interval: 30s
      timeout: 10s
      retries: 3

  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.8.0
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
      - "ES_JAVA_OPTS=-Xms512m -Xmx512m"
    ports:
      - "9200:9200"
      - "9300:9300"
    volumes:
      - es_data:/usr/share/elasticsearch/data
    healthcheck:
      test: ["CMD-SHELL", "curl -f http://localhost:9200/_cluster/health || exit 1"]
      interval: 30s
      timeout: 10s
      retries: 5

volumes:
  postgres_data:
  redis_data:
  rabbitmq_data:
  es_data:
```

## 🚀 .NET 10 Integration

### Modern Testing Patterns
```csharp
// .NET 10 testing patterns avec TestContainers
public class ModernTestContainerTests
{
    // Span<T> pour efficient data processing
    public static bool ValidateData_Span(ReadOnlySpan<byte> data)
    {
        if (data.Length < 4)
            return false;
            
        // Check header
        var header = data[..4];
        if (!header.SequenceEqual(new byte[] { 0x89, 0x50, 0x4E, 0x47 }))
            return false;
            
        return true;
    }
    
    // ValueTask pour async operations
    public static async ValueTask<bool> ValidateDataAsync(ReadOnlyMemory<byte> data)
    {
        if (data.Length < 4)
            return false;
            
        var header = data.Span[..4];
        return header.SequenceEqual(new byte[] { 0x89, 0x50, 0x4E, 0x47 });
    }
    
    // Pattern matching for container types
    public static TestcontainersContainer CreateContainer(string containerType) => containerType switch
    {
        "postgres" => new TestcontainersBuilder<PostgreSqlTestcontainer>()
            .WithImage("postgres:15-alpine")
            .Build(),
        "redis" => new TestcontainersBuilder<RedisTestcontainer>()
            .WithImage("redis:7-alpine")
            .Build(),
        "rabbitmq" => new TestcontainersBuilder<RabbitMqTestcontainer>()
            .WithImage("rabbitmq:3-management-alpine")
            .Build(),
        _ => throw new ArgumentException($"Unknown container type: {containerType}")
    };
    
    // Records immutables pour configuration
    public sealed record ContainerConfig(
        string Image,
        IReadOnlyDictionary<string, string> Environment,
        IReadOnlyDictionary<int, int> PortMappings,
        TimeSpan StartupTimeout
    )
    {
        public static ContainerConfig Default(string image) => new(
            Image: image,
            Environment: new Dictionary<string, string>(),
            PortMappings: new Dictionary<int, int>(),
            StartupTimeout: TimeSpan.FromMinutes(2)
        );
    }
    
    // Memory-efficient data processing
    public static void ProcessLargeDataset(ReadOnlySpan<byte> data)
    {
        const int chunkSize = 4096;
        
        for (int offset = 0; offset < data.Length; offset += chunkSize)
        {
            var chunk = data[Math.Min(offset, data.Length - chunkSize)..Math.Min(offset + chunkSize, data.Length)];
            ProcessChunk(chunk);
        }
    }
    
    private static void ProcessChunk(ReadOnlySpan<byte> chunk)
    {
        // Process chunk efficiently
    }
}
```

## 📊 Performance & Monitoring

### Test Performance Optimization
```csharp
// Optimized test execution
public class OptimizedTestExecution
{
    private static readonly ObjectPool<StringBuilder> StringBuilderPool = 
        new DefaultObjectPool<StringBuilder>(
            new StringBuilderPooledObjectPolicy());
    
    public static async Task RunParallelTests<T>(IEnumerable<T> testData, Func<T, Task> testFunc)
    {
        var tasks = testData.Select(testFunc).ToArray();
        await Task.WhenAll(tasks);
    }
    
    public static string BuildEfficientString(IEnumerable<string> parts)
    {
        var sb = StringBuilderPool.Get();
        try
        {
            foreach (var part in parts)
            {
                sb.Append(part);
            }
            return sb.ToString();
        }
        finally
        {
            StringBuilderPool.Return(sb);
        }
    }
    
    // Memory-efficient test data generation
    public static ReadOnlyMemory<byte> GenerateTestData(int size)
    {
        var buffer = new byte[size];
        Random.Shared.NextBytes(buffer);
        return buffer;
    }
    
    // Concurrent test execution with synchronization
    public static async Task<Dictionary<TKey, TResult>> ExecuteConcurrentTests<TKey, TResult>(
        IEnumerable<TKey> keys,
        Func<TKey, Task<TResult>> testFunc)
    {
        var results = new ConcurrentDictionary<TKey, TResult>();
        var tasks = keys.Select(async key =>
        {
            var result = await testFunc(key);
            results[key] = result;
        });
        
        await Task.WhenAll(tasks);
        return new Dictionary<TKey, TResult>(results);
    }
}
```

## 🎯 Cas d'Usage

### Microservices Testing
- Tests d'intégration entre services
- Validation de communication API
- Tests de résilience et retry

### Database Migration Testing
- Tests de migrations de schéma
- Validation de performance de requêtes
- Tests de concurrence de base de données

### Message Queue Testing
- Tests de delivery de messages
- Validation de dead letter queues
- Tests de performance de throughput

## 📚 Anti-Patterns à Éviter

- **❌** Tests sans cleanup des ressources
- **❌** Ports hardcodés dans les tests
- **❌** Tests dépendants de l'ordre d'exécution
- **❌** Pas de timeout pour les conteneurs
- **❌** Tests sans isolation complète
- **❌** Tests avec données trop volumineuses

Ce skill fournit une expertise complète pour créer des tests d'intégration distribués fiables avec TestContainers et .NET 10.
