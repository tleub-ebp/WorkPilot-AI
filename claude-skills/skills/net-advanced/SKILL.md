name: net-advanced
description: Expertise .NET 10 complète avec Akka.NET, Aspire, BenchmarkDotNet, TestContainers. Patterns modernes, performance optimisée, et systèmes distribués.
license: Complete terms in LICENSE.txt
---

# .NET 10 Advanced Expertise

## Vue d'ensemble

Skill complet pour développement .NET 10 moderne avec expertise en systèmes distribués, performance, et cloud-native.

**Mots-clés**: .NET 10, C# 13, Akka.NET, Aspire, BenchmarkDotNet, TestContainers, microservices, performance, cloud-native

## 🎯 Compétences Principales

### Core .NET 10
- **C# 13**: params spans, extension types, improved pattern matching
- **ASP.NET Core 10**: Performance optimisée, minimal APIs
- **Entity Framework Core 10**: Améliorations de performance
- **Blazor 10**: Améliorations de rendu

### Systèmes Distribués
- **Akka.NET**: Actors, clustering, persistence, streams
- **.NET Aspire**: Orchestration cloud-native, service discovery
- **Event Sourcing**: Patterns de persistance événementielle
- **CQRS**: Command Query Responsibility Segregation

### Performance & Testing
- **BenchmarkDotNet**: Performance testing automatisé
- **TestContainers**: Tests d'intégration distribués
- **Span<T>**: Memory-efficient processing
- **Object Pooling**: Réduction des allocations

## 🛠️ Patterns Production

### 1. Modern C# Patterns
```csharp
// Immutabilité par défaut
public sealed record OrderEvent(
    Guid OrderId,
    DateTime Timestamp,
    OrderEventType Type
);

// Type safety avec nullable reference types
public sealed class OrderProcessor
{
    public async Task<OrderResult?> ProcessOrderAsync(OrderRequest? request)
    {
        if (request is null) return null;
        // Processing logic avec ValueTask
    }
}

// Performance-aware avec Span<T>
public static bool ValidateData(ReadOnlySpan<byte> data)
{
    return data.Length > 0 && data[0] == 0x89;
}

// Composition over inheritance
public sealed class OrderService
{
    private readonly IOrderRepository _repository;
    private readonly IEventPublisher _publisher;
    
    public OrderService(IOrderRepository repository, IEventPublisher publisher)
    {
        _repository = repository;
        _publisher = publisher;
    }
}
```

### 2. Akka.NET Distributed Systems
```csharp
// Actor system configuration
var actorSystem = ActorSystem.Create("OrderSystem");
var orderProcessor = actorSystem.ActorOf<OrderProcessorActor>("orderProcessor");

// Clustering avec Akka.Cluster
var cluster = Cluster.Get(actorSystem);
cluster.Join(cluster.SelfAddress);

// Persistence avec Event Sourcing
public class OrderProcessorActor : PersistentActor
{
    private readonly IActorRef _eventPublisher;
    
    public override string PersistenceId => $"order-processor-{Self.Path.Name}";
    
    protected override bool ReceiveRecover(object message)
    {
        return message switch
        {
            OrderEvent evt => ApplyEvent(evt),
            _ => false
        };
    }
    
    protected override bool ReceiveCommand(object message)
    {
        return message switch
        {
            ProcessOrder cmd => ProcessOrder(cmd),
            _ => false
        };
    }
}
```

### 3. .NET Aspire Orchestration
```csharp
// apphost.csproj
<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <OutputType>Exe</OutputType>
    <TargetFramework>net10.0</TargetFramework>
    <ImplicitUsings>enable</ImplicitUsings>
    <Nullable>enable</Nullable>
  </PropertyGroup>
  
  <ItemGroup>
    <PackageReference Include="Microsoft.Extensions.Hosting" />
    <PackageReference Include="Aspire.Hosting.AppHost" />
  </ItemGroup>
</Project>

// Program.cs
var builder = DistributedApplication.CreateBuilder(args);

var postgres = builder.AddPostgresContainer("postgres");
var redis = builder.AddRedisContainer("redis");
var rabbitmq = builder.AddRabbitMQContainer("rabbitmq");

var apiService = builder.AddProject<Projects.MyApi>("api")
    .WithReference(postgres)
    .WithReference(redis)
    .WithReference(rabbitmq);

builder.Build().Run();
```

### 4. BenchmarkDotNet Performance Testing
```csharp
[MemoryDiagnoser]
[SimpleJob(RuntimeMoniker.Net80)]
public class OrderProcessingBenchmark
{
    private OrderService _service = null!;
    private OrderRequest _request = null!;
    
    [GlobalSetup]
    public void Setup()
    {
        _service = new OrderService();
        _request = new OrderRequest
        {
            CustomerId = Guid.NewGuid(),
            Items = new[] { new OrderItem { ProductId = Guid.NewGuid(), Quantity = 2 } }
        };
    }
    
    [Benchmark]
    public async Task<Order> ProcessOrder()
    {
        return await _service.ProcessOrderAsync(_request);
    }
    
    [Benchmark]
    public bool ValidateOrderData()
    {
        var data = new byte[] { 0x89, 0x50, 0x4E, 0x47 };
        return ValidateData(data);
    }
}
```

### 5. TestContainers Integration
```csharp
public class OrderRepositoryTests : IClassFixture<PostgreSqlTestFixture>
{
    private readonly PostgreSqlTestFixture _fixture;
    private readonly OrderDbContext _dbContext;
    private readonly OrderRepository _repository;
    
    public OrderRepositoryTests(PostgreSqlTestFixture fixture)
    {
        _fixture = fixture;
        
        var options = new DbContextOptionsBuilder<OrderDbContext>()
            .UseNpgsql(_fixture.ConnectionString)
            .Options;
            
        _dbContext = new OrderDbContext(options);
        _repository = new OrderRepository(_dbContext);
    }
    
    [Fact]
    public async Task CreateOrder_ShouldPersistOrder_WhenValidOrder()
    {
        // Arrange
        var order = new Order
        {
            CustomerId = Guid.NewGuid(),
            TotalAmount = 99.99m,
            Status = "pending"
        };
        
        // Act
        var result = await _repository.CreateAsync(order);
        
        // Assert
        result.Should().NotBeNull();
        result.Id.Should().NotBe(Guid.Empty());
    }
}

public class PostgreSqlTestFixture : IDisposable
{
    private readonly TestcontainersContainer _container;
    public string ConnectionString { get; }
    
    public PostgreSqlTestFixture()
    {
        _container = new TestcontainersBuilder<PostgreSqlTestcontainer>()
            .WithImage("postgres:15-alpine")
            .WithDatabase("testdb")
            .WithUsername("testuser")
            .WithPassword("testpass")
            .WithPortBinding(5432, true)
            .Build();
            
        _container.StartAsync().Wait();
        
        var port = _container.GetMappedPublicPort(5432);
        ConnectionString = $"Host=localhost;Port={port};Database=testdb;Username=testuser;Password=testpass";
    }
    
    public void Dispose()
    {
        _container?.StopAsync().Wait();
        _container?.DisposeAsync().Wait();
    }
}
```

## 🚀 Architecture Patterns

### Clean Architecture .NET 10
```
src/
├── Domain/                 # Entités, value objects, domain events
│   ├── Entities/
│   ├── ValueObjects/
│   └── Events/
├── Application/            # Use cases, services, DTOs
│   ├── UseCases/
│   ├── Services/
│   └── DTOs/
├── Infrastructure/         # EF Core, external services
│   ├── Persistence/
│   ├── External/
│   └── Messaging/
└── API/                   # Controllers, minimal APIs
    ├── Controllers/
    └── Endpoints/
```

### Microservices with Aspire
```yaml
# docker-compose.yml
services:
  orders-api:
    build: ./src/Orders.API
    environment:
      - ConnectionStrings__Postgres=Host=postgres;Database=orders
      - ConnectionStrings__Redis=redis:6379
    depends_on:
      - postgres
      - redis
      
  notifications-service:
    build: ./src/Notifications.Service
    environment:
      - RabbitMQ__Host=rabbitmq
    depends_on:
      - rabbitmq
      
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: orders
      
  redis:
    image: redis:7-alpine
    
  rabbitmq:
    image: rabbitmq:3-management-alpine
```

## 📊 Performance Optimization

### Memory-Efficient Processing
```csharp
// Span<T> pour zero-allocation
public static bool ValidateHeader(ReadOnlySpan<byte> data)
{
    if (data.Length < 4) return false;
    
    var header = data[..4];
    return header.SequenceEqual(new byte[] { 0x89, 0x50, 0x4E, 0x47 });
}

// Object pooling
public sealed class StringBuilderPool
{
    private static readonly ObjectPool<StringBuilder> _pool = 
        new DefaultObjectPool<StringBuilder>(new StringBuilderPooledObjectPolicy());
    
    public static StringBuilder Get() => _pool.Get();
    public static void Return(StringBuilder sb) => _pool.Return(sb);
}

// Async streams pour gros datasets
public async IAsyncEnumerable<Order> GetOrdersAsync()
{
    await foreach (var order in _dbContext.Orders.AsAsyncEnumerable())
    {
        yield return order;
    }
}
```

### Benchmarking Strategy
```csharp
// Performance gates dans CI/CD
[Fact]
public async Task OrderProcessing_ShouldCompleteUnder100ms()
{
    // Arrange
    var stopwatch = Stopwatch.StartNew();
    
    // Act
    await _orderService.ProcessOrderAsync(_testOrder);
    
    // Assert
    stopwatch.Stop();
    stopwatch.ElapsedMilliseconds.Should().BeLessThan(100);
}
```

## 🔧 Development Workflow

### Project Creation Script
```bash
# Créer projet .NET 10 avec tous les patterns
python scripts/create_project.py --name "MyApp" --type webapi --framework net10.0 --database postgresql --architecture clean
```

### Testing Strategy
```bash
# Tests unitaires avec performance
dotnet test --configuration Release --collect:"XPlat Code Coverage"

# Benchmarks
dotnet run -c Release --project MyBenchmarks

# Tests d'intégration avec TestContainers
dotnet test --configuration Release --filter "Category=Integration"
```

## 📚 Anti-Patterns à Éviter

- **❌** AutoMapper (préférer Mapster ou Mapster)
- **❌** Lazy loading dans les APIs
- **❌** Réflexion lourde (préférer source generators)
- **❌** Classes non sealed (préférer sealed par défaut)
- **❌** Mutabilité par défaut (préférer records et immutabilité)
- **❌** Tests sans isolation (utiliser TestContainers)

## 🎯 Cas d'Usage

### High-Performance APIs
- Minimal APIs avec Span<T>
- Object pooling pour réduire allocations
- Async streams pour gros datasets

### Distributed Systems
- Akka.NET pour actors et clustering
- .NET Aspire pour orchestration
- Event sourcing avec Akka.Persistence

### Enterprise Applications
- Clean Architecture avec DDD
- CQRS avec MediatR
- TestContainers pour tests d'intégration

Ce skill consolidé optimise les tokens tout en fournissant une expertise .NET 10 complète et production-ready.
