name: aspire-orchestration
description: Expertise .NET Aspire pour orchestration cloud-native d'applications distribuées. Patterns production pour microservices, conteneurs et observabilité.
license: Complete terms in LICENSE.txt
---

# .NET Aspire Orchestration - Cloud-Native Applications

## Vue d'ensemble

Skill spécialisé dans .NET Aspire pour orchestrer des applications cloud-native distribuées avec conteneurs, services, et observabilité intégrée.

**Mots-clés**: .NET Aspire, cloud-native, orchestration, microservices, conteneurs, observabilité, OpenTelemetry, health checks

## 🎯 Compétences Principales

### Orchestration d'Applications
- **DistributedApplication**: Configuration d'applications distribuées
- **Service Discovery**: Découverte automatique de services
- **Configuration Management**: Gestion centralisée de configuration
- **Resource Management**: Déclaration et gestion des ressources

### Conteneurisation & Déploiement
- **Docker Integration**: Conteneurs Docker pour services
- **Kubernetes Deployment**: Déploiement sur clusters K8s
- **Environment Management**: Gestion multi-environnements
- **Resource Scaling**: Scaling automatique et manuel

### Observabilité & Monitoring
- **OpenTelemetry**: Télémétrie distribuée intégrée
- **Health Checks**: Monitoring de santé des services
- **Logging Centralized**: Logs structurés et centralisés
- **Metrics Collection**: Métriques de performance et business

### Integration & Testing
- **Integration Testing**: Tests d'intégration distribués
- **Service Mesh**: Patterns de communication entre services
- **API Gateway**: Gestion et routing des APIs
- **Message Brokers**: Communication asynchrone

## 🛠️ Patterns Production

### 1. Application Host Configuration
```csharp
// Program.cs - Configuration principale Aspire
var builder = DistributedApplication.CreateBuilder(args);

// Services avec configuration production-ready
builder.AddProject<Projects.OrderService>("orderservice")
    .WithReference(builder.AddPostgres("ordersdb"))
    .WithReference(builder.AddRedis("orderscache"))
    .WithEnvironment("ASPNETCORE_ENVIRONMENT", "Production")
    .WithHttpEndpoint(
        port: 8080,
        name: "orderservice-http",
        targetPort: 8080);

builder.AddProject<Projects.InventoryService>("inventoryservice")
    .WithReference(builder.AddPostgres("inventorydb"))
    .WithReference(builder.AddRabbitMQ("messagebroker"))
    .WithEnvironment("ASPNETCORE_ENVIRONMENT", "Production")
    .WithHttpEndpoint(
        port: 8081,
        name: "inventoryservice-http",
        targetPort: 8081);

builder.AddProject<Projects.NotificationService>("notificationservice")
    .WithReference(builder.AddRabbitMQ("messagebroker"))
    .WithReference(builder.AddMailPit("mailpit"))
    .WithEnvironment("ASPNETCORE_ENVIRONMENT", "Production")
    .WithHttpEndpoint(
        port: 8082,
        name: "notificationservice-http",
        targetPort: 8082);

// API Gateway
builder.AddProject<Projects.ApiGateway>("apigateway")
    .WithReference(builder.AddPostgres("gatewaydb"))
    .WithHttpEndpoint(
        port: 8000,
        name: "apigateway-http",
        targetPort: 8000);

// Dashboard Aspire
builder.AddFrontend("frontend")
    .WithExternalHttpEndpoints(
        builder.GetEndpoint("apigateway-http", "apigateway"));

builder.Build().Run();
```

### 2. Service Configuration avec Health Checks
```csharp
// OrderService/Program.cs
var builder = WebApplication.CreateBuilder(args);

// Configuration Aspire
builder.AddServiceDefaults();
builder.AddRedisDistributedCache("cache");
builder.AddNpgsqlDbContext<OrderDbContext>("ordersdb");

// Health Checks
builder.Services.AddHealthChecks()
    .AddCheck<DatabaseHealthCheck>("database")
    .AddCheck<RedisHealthCheck>("redis")
    .AddCheck<RabbitMQHealthCheck>("rabbitmq")
    .AddCheck<ExternalServiceHealthCheck>("payment-service");

// OpenTelemetry
builder.Services.AddOpenTelemetry()
    .WithTracing(builder => builder
        .AddSource("OrderService")
        .AddAspNetCoreInstrumentation()
        .AddHttpClientInstrumentation()
        .AddNpgsql())
    .WithMetrics(builder => builder
        .AddAspNetCoreInstrumentation()
        .AddHttpClientInstrumentation()
        .AddNpgsql())
    .WithLogging(builder => builder
        .AddConsoleExporter()
        .AddOtlpExporter());

var app = builder.Build();

// Health Check endpoints
app.MapHealthChecks("/health", new HealthCheckOptions
{
    ResponseWriter = HealthCheckResponseWriter.WriteResponse,
    Predicate = check => check.Tags.Contains("ready")
});

app.MapHealthChecks("/health/live", new HealthCheckOptions
{
    Predicate = _ => false
});

// Observability endpoints
app.MapPrometheusScrapingEndpoint();

app.Run();
```

### 3. Custom Health Checks
```csharp
// Health Checks avancés
public class DatabaseHealthCheck : IHealthCheck
{
    private readonly OrderDbContext _dbContext;
    private readonly ILogger<DatabaseHealthCheck> _logger;
    
    public DatabaseHealthCheck(OrderDbContext dbContext, ILogger<DatabaseHealthCheck> logger)
    {
        _dbContext = dbContext;
        _logger = logger;
    }
    
    public async Task<HealthCheckResult> CheckHealthAsync(
        HealthCheckContext context,
        CancellationToken cancellationToken = default)
    {
        try
        {
            var canConnect = await _dbContext.Database.CanConnectAsync(cancellationToken);
            
            if (!canConnect)
            {
                return HealthCheckResult.Unhealthy("Cannot connect to database");
            }
            
            var migrations = await _dbContext.Database.GetPendingMigrationsAsync(cancellationToken);
            
            if (migrations.Any())
            {
                return HealthCheckResult.Degraded($"Pending migrations: {string.Join(", ", migrations)}");
            }
            
            // Test query performance
            var stopwatch = Stopwatch.StartNew();
            await _dbContext.Database.ExecuteSqlRawAsync("SELECT 1", cancellationToken);
            stopwatch.Stop();
            
            if (stopwatch.ElapsedMilliseconds > 1000)
            {
                return HealthCheckResult.Degraded($"Database query slow: {stopwatch.ElapsedMilliseconds}ms");
            }
            
            return HealthCheckResult.Healthy("Database connection and performance OK");
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Database health check failed");
            return HealthCheckResult.Unhealthy("Database health check failed", ex);
        }
    }
}

public class RabbitMQHealthCheck : IHealthCheck
{
    private readonly IConnection _connection;
    private readonly ILogger<RabbitMQHealthCheck> _logger;
    
    public RabbitMQHealthCheck(IConnection connection, ILogger<RabbitMQHealthCheck> logger)
    {
        _connection = connection;
        _logger = logger;
    }
    
    public async Task<HealthCheckResult> CheckHealthAsync(
        HealthCheckContext context,
        CancellationToken cancellationToken = default)
    {
        try
        {
            if (_connection.IsClosed)
            {
                return HealthCheckResult.Unhealthy("RabbitMQ connection is closed");
            }
            
            // Test channel creation
            using var channel = await _connection.CreateChannelAsync(cancellationToken);
            
            // Test queue operations
            await channel.QueueDeclareAsync(
                queue: "health-check-queue",
                durable: false,
                exclusive: true,
                autoDelete: true,
                arguments: null,
                cancellationToken: cancellationToken);
            
            return HealthCheckResult.Healthy("RabbitMQ connection and operations OK");
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "RabbitMQ health check failed");
            return HealthCheckResult.Unhealthy("RabbitMQ health check failed", ex);
        }
    }
}
```

### 4. Integration Testing avec Aspire
```csharp
// Tests/OrderServiceIntegrationTests.cs
public class OrderServiceIntegrationTests : IClassFixture<AspireApplicationFixture>
{
    private readonly AspireApplicationFixture _fixture;
    private readonly HttpClient _httpClient;
    
    public OrderServiceIntegrationTests(AspireApplicationFixture fixture)
    {
        _fixture = fixture;
        _httpClient = fixture.CreateHttpClient("orderservice");
    }
    
    [Fact]
    public async Task CreateOrder_ShouldReturnSuccess_WhenValidRequest()
    {
        // Arrange
        var createOrderRequest = new
        {
            CustomerId = Guid.NewGuid(),
            Items = new[]
            {
                new { ProductId = Guid.NewGuid(), Quantity = 2, Price = 29.99m }
            }
        };
        
        // Act
        var response = await _httpClient.PostAsJsonAsync("/api/orders", createOrderRequest);
        
        // Assert
        response.StatusCode.Should().Be(HttpStatusCode.Created);
        
        var orderResponse = await response.Content.ReadFromJsonAsync<OrderResponse>();
        orderResponse.Should().NotBeNull();
        orderResponse.Status.Should().Be("Created");
        
        // Verify database state
        await VerifyOrderInDatabase(orderResponse.OrderId);
    }
    
    [Fact]
    public async Task OrderProcessing_ShouldTriggerEvents_WhenOrderCreated()
    {
        // Arrange
        var eventCollector = _fixture.GetEventCollector();
        
        // Act
        var orderId = await CreateTestOrder();
        
        // Assert
        var events = await eventCollector.GetEventsAsync<OrderEvent>(
            TimeSpan.FromSeconds(10));
            
        events.Should().Contain(e => e is OrderCreated);
        events.Should().Contain(e => e is InventoryReserved);
        events.Should().Contain(e => e is PaymentProcessed);
    }
    
    private async Task<Guid> CreateTestOrder()
    {
        var createOrderRequest = new
        {
            CustomerId = Guid.NewGuid(),
            Items = new[]
            {
                new { ProductId = Guid.NewGuid(), Quantity = 1, Price = 99.99m }
            }
        };
        
        var response = await _httpClient.PostAsJsonAsync("/api/orders", createOrderRequest);
        var orderResponse = await response.Content.ReadFromJsonAsync<OrderResponse>();
        
        return orderResponse.OrderId;
    }
    
    private async Task VerifyOrderInDatabase(Guid orderId)
    {
        var connectionString = _fixture.GetConnectionString("ordersdb");
        using var connection = new NpgsqlConnection(connectionString);
        
        var order = await connection.QuerySingleAsync<Order>(
            "SELECT * FROM Orders WHERE Id = @orderId",
            new { orderId });
            
        order.Should().NotBeNull();
        order.Status.Should().Be("Created");
    }
}

// Test fixture pour Aspire
public class AspireApplicationFixture : IDisposable
{
    private DistributedApplication _app;
    private IResourceBuilder<PostgresServerResource> _postgres;
    private IResourceBuilder<RedisResource> _redis;
    private IResourceBuilder<RabbitMQServerResource> _rabbitMQ;
    private IResourceBuilder<ProjectResource> _orderService;
    
    public AspireApplicationFixture()
    {
        var builder = DistributedApplication.CreateBuilder();
        
        // Setup test resources
        _postgres = builder.AddPostgres("test-ordersdb");
        _redis = builder.AddRedis("test-orderscache");
        _rabbitMQ = builder.AddRabbitMQ("test-messagebroker");
        
        // Setup test service
        _orderService = builder.AddProject<Projects.OrderService>("test-orderservice")
            .WithReference(_postgres)
            .WithReference(_redis)
            .WithReference(_rabbitMQ);
            
        _app = builder.Build();
        
        // Start the application
        _app.StartAsync().Wait();
    }
    
    public HttpClient CreateHttpClient(string resourceName)
    {
        var endpoint = _app.GetEndpoint($"{resourceName}-http");
        return _app.CreateHttpClient(resourceName);
    }
    
    public string GetConnectionString(string resourceName)
    {
        return _app.GetConnectionString(resourceName);
    }
    
    public EventCollector GetEventCollector()
    {
        return _app.Services.GetRequiredService<EventCollector>();
    }
    
    public void Dispose()
    {
        _app?.Dispose();
    }
}
```

### 5. Configuration Production avec .NET 10
```csharp
// appsettings.Production.json
{
  "Logging": {
    "LogLevel": {
      "Default": "Information",
      "Microsoft.AspNetCore": "Warning",
      "Microsoft.EntityFrameworkCore": "Warning"
    },
    "Console": {
      "IncludeScopes": true,
      "TimestampFormat": "yyyy-MM-dd HH:mm:ss "
    },
    "OpenTelemetry": {
      "LogLevel": "Information"
    }
  },
  "HealthChecks": {
    "UI": {
      "Enabled": true,
      "Path": "/health-ui"
    },
    "Publisher": {
      "Type": "Prometheus"
    }
  },
  "OpenTelemetry": {
    "Endpoint": "http://otel-collector:4317",
    "Headers": {
      "api-key": "your-api-key"
    },
    "BatchSize": 1000,
    "ExportIntervalMilliseconds": 5000,
    "EnablePerformanceCounters": true
  },
  "ConnectionStrings": {
    "OrdersDb": "Host=postgres;Port=5432;Database=orders;Username=orders_user;Password=orders_pass;",
    "Cache": "redis:6379",
    "MessageBroker": "amqp://rabbitmq:5672"
  },
  "Resilience": {
    "Http": {
      "CircuitBreaker": {
        "FailureRatio": 0.1,
        "MinimumThroughput": 8,
        "SamplingDuration": "00:00:30",
        "BreakDuration": "00:00:05"
      },
      "Retry": {
        "Count": 3,
        "BackoffType": "Exponential",
        "Delay": "00:00:01"
      },
      "Timeout": {
        "Timeout": "00:00:30"
      }
    }
  }
}
```

### 6. Docker Compose pour Développement
```yaml
# docker-compose.yml
version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: orders
      POSTGRES_USER: orders_user
      POSTGRES_PASSWORD: orders_pass
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U orders_user -d orders"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  rabbitmq:
    image: rabbitmq:3-management-alpine
    environment:
      RABBITMQ_DEFAULT_USER: admin
      RABBITMQ_DEFAULT_PASS: admin123
    ports:
      - "5672:5672"
      - "15672:15672"
    healthcheck:
      test: ["CMD", "rabbitmq-diagnostics", "ping"]
      interval: 30s
      timeout: 10s
      retries: 3

  mailpit:
    image: axllent/mailpit
    ports:
      - "1025:1025"
      - "8025:8025"
    healthcheck:
      test: ["CMD", "wget", "--quiet", "--tries=1", "--spider", "http://localhost:8025/"]
      interval: 30s
      timeout: 10s
      retries: 3

  otel-collector:
    image: otel/opentelemetry-collector-contrib:latest
    command: ["--config=/etc/otel-collector-config.yaml"]
    volumes:
      - ./otel-collector-config.yaml:/etc/otel-collector-config.yaml
    ports:
      - "4317:4317"
      - "8888:8888"
      - "8889:8889"
    depends_on:
      - postgres
      - redis
      - rabbitmq

volumes:
  postgres_data:
```

### 7. Kubernetes Deployment
```yaml
# k8s/aspire-app.yml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: orderservice
  labels:
    app: orderservice
spec:
  replicas: 3
  selector:
    matchLabels:
      app: orderservice
  template:
    metadata:
      labels:
        app: orderservice
    spec:
      containers:
      - name: orderservice
        image: orderservice:latest
        ports:
        - containerPort: 8080
        env:
        - name: ConnectionStrings__OrdersDb
          valueFrom:
            secretKeyRef:
              name: app-secrets
              key: orders-db-connection-string
        - name: ConnectionStrings__Cache
          value: redis:6379
        - name: ConnectionStrings__MessageBroker
          value: amqp://rabbitmq:5672
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health/live
            port: 8080
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 5
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: orderservice
spec:
  selector:
    app: orderservice
  ports:
  - port: 8080
    targetPort: 8080
  type: ClusterIP
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: orderservice-config
data:
  appsettings.json: |
    {
      "Logging": {
        "LogLevel": {
          "Default": "Information"
        }
      },
      "OpenTelemetry": {
        "Endpoint": "http://otel-collector:4317"
      }
    }
```

## 🚀 .NET 10 Integration

### Modern C# Patterns avec Aspire
```csharp
// Configuration moderne avec records
public sealed record ServiceConfiguration(
    string ServiceName,
    Uri BaseAddress,
    TimeSpan Timeout,
    RetryPolicy RetryPolicy
);

// Pattern matching pour service discovery
public static class ServiceResolver
{
    public static Uri ResolveService(this IConfiguration config, string serviceName) =>
        config[$"Services:{serviceName}:Url"] switch
        {
            null => throw new InvalidOperationException($"Service {serviceName} not configured"),
            var url when Uri.TryCreate(url, UriKind.Absolute, out var uri) => uri,
            _ => throw new InvalidOperationException($"Invalid URL for service {serviceName}")
        };
}

// Value objects pour configuration
public sealed record RetryPolicy(
    int MaxAttempts,
    TimeSpan InitialDelay,
    TimeSpan MaxDelay,
    BackoffType BackoffType
)
{
    public static RetryPolicy Default => new(
        MaxAttempts: 3,
        InitialDelay: TimeSpan.FromSeconds(1),
        MaxDelay: TimeSpan.FromSeconds(30),
        BackoffType: BackoffType.Exponential
    );
}

// Span<T> optimization pour configuration parsing
public static class ConfigurationParser
{
    public static ServiceConfiguration ParseServiceConfig(
        this IConfiguration config,
        ReadOnlySpan<char> serviceName)
    {
        var baseAddress = config[$"Services:{serviceName}:Url"];
        var timeout = TimeSpan.Parse(config[$"Services:{serviceName}:Timeout"] ?? "00:00:30");
        
        var retryConfig = ParseRetryPolicy(config, serviceName);
        
        return new ServiceConfiguration(
            ServiceName: serviceName.ToString(),
            BaseAddress: new Uri(baseAddress),
            Timeout: timeout,
            RetryPolicy: retryConfig
        );
    }
    
    private static RetryPolicy ParseRetryPolicy(
        IConfiguration config,
        ReadOnlySpan<char> serviceName)
    {
        var maxAttempts = config.GetValue<int>($"Services:{serviceName}:Retry:MaxAttempts", 3);
        var initialDelay = TimeSpan.Parse(config[$"Services:{serviceName}:Retry:InitialDelay"] ?? "00:00:01");
        var maxDelay = TimeSpan.Parse(config[$"Services:{serviceName}:Retry:MaxDelay"] ?? "00:00:30");
        var backoffType = config.GetValue<BackoffType>($"Services:{serviceName}:Retry:BackoffType", BackoffType.Exponential);
        
        return new RetryPolicy(maxAttempts, initialDelay, maxDelay, backoffType);
    }
}
```

### Performance Optimization
```csharp
// HttpClientFactory avec Polly et performance
public static class ServiceCollectionExtensions
{
    public static IServiceCollection AddResilientHttpClient<T>(
        this IServiceCollection services,
        string serviceName,
        Action<HttpClient>? configureClient = null) where T : class
    {
        services.AddHttpClient<T>(serviceName, configureClient)
            .AddTransientHttpErrorPolicy(policy =>
                policy.WaitAndRetryAsync(
                    retryCount: 3,
                    sleepDurationProvider: retryAttempt => TimeSpan.FromSeconds(Math.Pow(2, retryAttempt)),
                    onRetry: (outcome, timespan, retryAttempt, context) =>
                    {
                        var logger = context.GetLogger<ResilientHttpClientFactory<T>>();
                        logger.LogWarning(
                            "Request failed with {StatusCode}. Waiting {Delay} before next retry. Retry attempt {RetryAttempt}",
                            outcome.Result?.StatusCode,
                            timespan,
                            retryAttempt);
                    }))
            .AddCircuitBreakerAsync(
                handledEventsAllowedBeforeBreaking: 3,
                durationOfBreak: TimeSpan.FromSeconds(30),
                onBreak: (exception, duration) =>
                {
                    var logger = context.GetLogger<ResilientHttpClientFactory<T>>();
                    logger.LogError(
                        "Circuit breaker opened for {Duration} due to exception: {Exception}",
                        duration,
                        exception);
                },
                onReset: () =>
                {
                    var logger = context.GetLogger<ResilientHttpClientFactory<T>>();
                    logger.LogInformation("Circuit breaker reset");
                })
            .AddPolicyHandlerAsync(Policy.TimeoutAsync<HttpResponseMessage>(
                TimeSpan.FromSeconds(30)));
        
        return services;
    }
}

// Memory-efficient event processing
public sealed class EventProcessor : IHostedService
{
    private readonly IChannel<EventWrapper> _eventChannel;
    private readonly ILogger<EventProcessor> _logger;
    private readonly Task _processingTask;
    
    public EventProcessor(ILogger<EventProcessor> logger)
    {
        _eventChannel = Channel.CreateUnbounded<EventWrapper>();
        _logger = logger;
        _processingTask = ProcessEventsAsync();
    }
    
    public async Task StartAsync(CancellationToken cancellationToken)
    {
        _logger.LogInformation("Event processor started");
        await Task.CompletedTask;
    }
    
    public async Task StopAsync(CancellationToken cancellationToken)
    {
        _eventChannel.Writer.Complete();
        await _processingTask;
        _logger.LogInformation("Event processor stopped");
    }
    
    public ValueTask PublishEventAsync<T>(T @event, CancellationToken cancellationToken = default) where T : notnull
    {
        return _eventChannel.Writer.WriteAsync(
            new EventWrapper(@event, DateTime.UtcNow, typeof(T)),
            cancellationToken);
    }
    
    private async Task ProcessEventsAsync()
    {
        await foreach (var eventWrapper in _eventChannel.Reader.ReadAllAsync())
        {
            try
            {
                await ProcessSingleEventAsync(eventWrapper);
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Failed to process event {EventType}", eventWrapper.EventType.Name);
            }
        }
    }
    
    private async Task ProcessSingleEventAsync(EventWrapper eventWrapper)
    {
        var stopwatch = Stopwatch.StartNew();
        
        // Process event with reflection-free pattern matching
        var result = eventWrapper.Event switch
        {
            OrderCreated created => await HandleOrderCreated(created),
            OrderUpdated updated => await HandleOrderUpdated(updated),
            OrderDeleted deleted => await HandleOrderDeleted(deleted),
            _ => throw new InvalidOperationException($"Unknown event type: {eventWrapper.EventType.Name}")
        };
        
        stopwatch.Stop();
        
        _logger.LogDebug(
            "Processed event {EventType} in {ElapsedMs}ms",
            eventWrapper.EventType.Name,
            stopwatch.ElapsedMilliseconds);
    }
    
    private record EventWrapper(object Event, DateTime Timestamp, Type EventType);
}
```

## 📊 Monitoring & Observabilité

### OpenTelemetry Configuration Avancée
```csharp
// OpenTelemetry configuration avec .NET 10
public static class OpenTelemetryConfiguration
{
    public static IServiceCollection AddCustomOpenTelemetry(
        this IServiceCollection services,
        IConfiguration configuration)
    {
        var otelConfig = configuration.GetSection("OpenTelemetry");
        
        services.AddOpenTelemetry()
            .ConfigureResource(resource => resource
                .AddService(configuration["Application:Name"])
                .AddAttributes(new Dictionary<string, object>
                {
                    ["service.version"] = typeof(Program).Assembly.GetName().Version?.ToString(),
                    ["service.instance.id"] = Environment.MachineName,
                    ["deployment.environment"] = configuration["ASPNETCORE_ENVIRONMENT"]
                }))
            .WithTracing(builder => builder
                .AddSource("Microsoft.AspNetCore")
                .AddSource("System.Net.Http")
                .AddSource("OrderService")
                .AddAspNetCoreInstrumentation(options =>
                {
                    options.RecordException = true;
                    options.EnrichWithHttpRequest = (activity, request) =>
                    {
                        activity.SetTag("user.id", GetUserFromRequest(request));
                        activity.SetTag("tenant.id", GetTenantFromRequest(request));
                    };
                })
                .AddHttpClientInstrumentation()
                .AddNpgsql()
                .AddRedis()
                .AddOtlpExporter(options =>
                {
                    options.Endpoint = new Uri(otelConfig["Endpoint"]);
                    options.Headers = otelConfig.GetSection("Headers")
                        .AsEnumerable()
                        .ToDictionary(x => x.Key, x => x.Value);
                    options.BatchExportProcessorOptions<BatchExportActivityProcessorOptions>(opt =>
                    {
                        opt.MaxQueueSize = 1000;
                        opt.MaxExportBatchSize = 100;
                        opt.ScheduledDelayMilliseconds = 5000;
                    });
                }))
            .WithMetrics(builder => builder
                .AddAspNetCoreInstrumentation()
                .AddHttpClientInstrumentation()
                .AddRuntimeInstrumentation()
                .AddNpgsql()
                .AddRedis()
                .AddPrometheusExporter()
                .AddOtlpExporter())
            .WithLogging(builder => builder
                .AddConsoleExporter()
                .AddOtlpExporter());
        
        return services;
    }
    
    private static string GetUserFromRequest(HttpRequest request)
    {
        // Extract user from JWT token or headers
        return request.Headers["X-User-Id"].FirstOrDefault() ?? "anonymous";
    }
    
    private static string GetTenantFromRequest(HttpRequest request)
    {
        // Extract tenant from headers or JWT claims
        return request.Headers["X-Tenant-Id"].FirstOrDefault() ?? "default";
    }
}
```

### Custom Metrics
```csharp
// Metrics personnalisées avec .NET 10
public sealed class OrderMetrics
{
    private readonly Counter<long> _ordersCreated;
    private readonly Histogram<double> _orderProcessingDuration;
    private readonly Gauge<int> _activeOrders;
    private readonly Counter<long> _orderFailures;
    
    public OrderMetrics(IMeterFactory meterFactory)
    {
        var meter = meterFactory.Create("OrderService");
        
        _ordersCreated = meter.CreateCounter<long>(
            "orders_created_total",
            "Total number of orders created",
            new[] { "customer_type", "payment_method" });
            
        _orderProcessingDuration = meter.CreateHistogram<double>(
            "order_processing_duration_seconds",
            "Order processing duration in seconds",
            new[] { "order_type", "processing_stage" });
            
        _activeOrders = meter.CreateGauge<int>(
            "active_orders",
            "Number of currently active orders");
            
        _orderFailures = meter.CreateCounter<long>(
            "order_failures_total",
            "Total number of order processing failures",
            new[] { "failure_type", "processing_stage" });
    }
    
    public void RecordOrderCreated(string customerType, string paymentMethod)
    {
        _ordersCreated.Add(1, new KeyValuePair<string, object>[]
        {
            new("customer_type", customerType),
            new("payment_method", paymentMethod)
        });
    }
    
    public void RecordProcessingDuration(TimeSpan duration, string orderType, string processingStage)
    {
        _orderProcessingDuration.Record(duration.TotalSeconds, new KeyValuePair<string, object>[]
        {
            new("order_type", orderType),
            new("processing_stage", processingStage)
        });
    }
    
    public void SetActiveOrders(int count)
    {
        _activeOrders.Record(count);
    }
    
    public void RecordOrderFailure(string failureType, string processingStage)
    {
        _orderFailures.Add(1, new KeyValuePair<string, object>[]
        {
            new("failure_type", failureType),
            new("processing_stage", processingStage)
        });
    }
}
```

## 🎯 Cas d'Usage

### E-Commerce Platform
- Orchestration de microservices e-commerce
- Gestion des commandes distribuées
- Inventory management temps réel

### SaaS Multi-Tenant
- Isolation tenant au niveau orchestration
- Scaling automatique par tenant
- Monitoring tenant-aware

### Financial Services
- Transaction processing haute disponibilité
- Compliance et audit trails
- Latency monitoring sub-millisecond

## 📚 Anti-Patterns à Éviter

- **❌** Services sans health checks
- **❌** Configuration hardcodée dans les services
- **❌** Pas de retry policies pour les appels externes
- **❌** Logs non structurés
- **❌** Pas de monitoring de performance
- **❌** Circuit breaker sans configuration appropriée

Ce skill fournit une expertise complète pour orchestrer des applications cloud-native avec .NET Aspire et .NET 10.
