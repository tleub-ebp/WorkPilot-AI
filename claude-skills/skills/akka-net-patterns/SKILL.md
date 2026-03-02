name: akka-net-patterns
description: Expertise Akka.NET pour systèmes distribués avec acteurs, clustering, persistence et streams. Patterns production pour applications scalables et résilientes.
license: Complete terms in LICENSE.txt
---

# Akka.NET Patterns - Systèmes Distribués Résilients

## Vue d'ensemble

Skill spécialisé dans les patterns Akka.NET pour construire des systèmes distribués de production avec actors, clustering, persistence et streaming.

**Mots-clés**: Akka.NET, actors, clustering, persistence, streams, systèmes distribués, résilience, scalabilité

## 🎯 Compétences Principales

### Actor Systems Architecture
- **Actor Hierarchies**: Conception de hiérarchies d'acteurs optimales
- **Supervision Strategies**: Patterns de supervision et recovery
- **Actor Lifecycle**: Gestion complète du cycle de vie
- **Message Patterns**: Communication asynchrone et patterns messaging

### Clustering & Distribution
- **Cluster Bootstrap**: Configuration et initialisation de cluster
- **Distributed Data**: Gestion de données distribuées avec CRDTs
- **Cluster Sharding**: Partitionnement automatique des acteurs
- **Split Brain Resolver**: Gestion des scénarios de split-brain

### Persistence & Event Sourcing
- **Event Sourcing**: Patterns de persistance événementielle
- **Snapshot Strategy**: Optimisation des snapshots
- **Journaling**: Configuration des journaux de persistance
- **Recovery**: Patterns de récupération après crash

### Akka.Streams
- **Stream Processing**: Processing de flux avec back-pressure
- **Graph Stages**: Construction de graphes de streaming
- **Integration**: Connecteurs externes (Kafka, RabbitMQ, SQL)
- **Performance**: Optimisation des streams haute performance

## 🛠️ Patterns Production

### 1. Actor Hierarchies
```csharp
// Root Actor avec supervision
public sealed class OrderManagerActor : ReceivePersistentActor
{
    private readonly IActorRef _orderProcessor;
    private readonly IActorRef _inventoryManager;
    
    public OrderManagerActor()
    {
        // Configuration avec retry et backoff
        var strategy = new OneForOneStrategy(
            maxNumberOfRetries: 3,
            withinTimeRange: TimeSpan.FromMinutes(1),
            decider: Decider.From(
                Directive.Restart,
                Directive.Stop,
                Directive.Escalate
            ));
        
        // Child actors avec scope DI
        _orderProcessor = Context.ActorOf(
            Props.Create<OrderProcessorActor>()
                .WithSupervisorStrategy(strategy), 
            "order-processor");
            
        _inventoryManager = Context.ActorOf<InventoryManagerActor>("inventory-manager");
    }
    
    protected override void OnRecover(object message)
    {
        // Recovery from snapshots + events
        if (message is OrderManagerState state)
        {
            // Restore state from snapshot
        }
    }
    
    protected override void OnCommand(object message)
    {
        switch (message)
        {
            case CreateOrder cmd:
                Persist(new OrderCreated(cmd.OrderId, cmd.CustomerId), OnOrderCreated);
                break;
                
            case GetOrderStatus query:
                Sender.Tell(_orderProcessor.Ask<OrderStatus>(query));
                break;
        }
    }
    
    private void OnOrderCreated(OrderCreated evt)
    {
        // Update state and forward to child
        _orderProcessor.Tell(evt);
    }
}
```

### 2. Cluster Configuration
```csharp
// Hocon configuration pour clustering
var config = ConfigurationFactory.ParseString(@"
    akka {
        actor {
            provider = cluster
            serializers {
                hyperion = ""Akka.Serialization.Hyperion.HyperionSerializer, Akka.Serialization.Hyperion""
            }
            serialization-bindings {
                ""System.Object"" = hyperion
            }
        }
        remote {
            dot-netty.tcp {
                hostname = ""0.0.0.0""
                port = 0
                public-hostname = ""localhost""
                public-port = 4053
            }
        }
        cluster {
            seed-nodes = [""akka.tcp://OrderSystem@localhost:4051""]
            downing-provider-class = ""Akka.Cluster.SplitBrainResolver, Akka.Cluster""
            split-brain-resolver {
                active-strategy = keep-majority
                keep-majority {
                    role = """"
                }
            }
        }
        persistence {
            journal {
                plugin = ""akka.persistence.journal.sql-server""
                sql-server {
                    connection-string = ""Server=localhost;Database=OrderSystem;Trusted_Connection=true;""
                    table-name = ""EventJournal""
                    schema-name = ""dbo""
                    auto-initialize = on
                }
            }
            snapshot-store {
                plugin = ""akka.persistence.snapshot-store.sql-server""
                sql-server {
                    connection-string = ""Server=localhost;Database=OrderSystem;Trusted_Connection=true;""
                    table-name = ""SnapshotStore""
                    schema-name = ""dbo""
                    auto-initialize = on
                }
            }
        }
    }");
```

### 3. Event Sourcing Pattern
```csharp
public sealed class OrderAggregate : ReceivePersistentActor
{
    private OrderState _state = OrderState.Empty;
    
    public OrderAggregate()
    {
        Command<CreateOrder>(HandleCreateOrder);
        Command<AddItem>(HandleAddItem);
        Command<ConfirmOrder>(HandleConfirmOrder);
        
        Recover<OrderCreated>(Apply);
        Recover<ItemAdded>(Apply);
        Recover<OrderConfirmed>(Apply);
    }
    
    private void HandleCreateOrder(CreateOrder cmd)
    {
        if (_state != OrderState.Empty)
        {
            Sender.Tell(new CommandFailed("Order already exists"));
            return;
        }
        
        Persist(new OrderCreated(cmd.OrderId, cmd.CustomerId, DateTime.UtcNow), Apply);
    }
    
    private void HandleAddItem(AddItem cmd)
    {
        if (_state == OrderState.Empty)
        {
            Sender.Tell(new CommandFailed("Order not created"));
            return;
        }
        
        if (_state == OrderState.Confirmed)
        {
            Sender.Tell(new CommandFailed("Order already confirmed"));
            return;
        }
        
        Persist(new ItemAdded(cmd.OrderId, cmd.ProductId, cmd.Quantity, cmd.Price), Apply);
    }
    
    private void Apply(OrderCreated evt)
    {
        _state = OrderState.Active;
        Context.System.EventStream.Publish(evt);
    }
    
    private void Apply(ItemAdded evt)
    {
        // Update internal state
        Context.System.EventStream.Publish(evt);
    }
}
```

### 4. Stream Processing
```csharp
public sealed class OrderProcessingStream : ActorBase
{
    private readonly IActorRef _orderProcessor;
    private readonly IActorRef _notificationService;
    
    public OrderProcessingStream(IActorRef orderProcessor, IActorRef notificationService)
    {
        _orderProcessor = orderProcessor;
        _notificationService = notificationService;
    }
    
    protected override void OnReceive(object message)
    {
        switch (message)
        {
            case StartOrderProcessing:
                var source = Source.From(new[] { new ProcessOrders() })
                    .Via(new OrderValidationStage())
                    .Via(new InventoryCheckStage())
                    .Via(new PaymentProcessingStage())
                    .To(Sink.ActorRef<OrderProcessed>(_orderProcessor))
                    .Run(Context.System.Materializer());
                    
                Sender.Tell(new ProcessingStarted(source));
                break;
        }
    }
}

// Custom stage pour validation
public sealed class OrderValidationStage : GraphStage<FlowShape<OrderEvent, ValidatedOrder>>
{
    public FlowShape<OrderEvent, ValidatedOrder> Shape { get; }
    
    public OrderValidationStage()
    {
        var inlet = new Inlet<OrderEvent>("validation.in");
        var outlet = new Outlet<ValidatedOrder>("validation.out");
        
        Shape = new FlowShape<OrderEvent, ValidatedOrder>(inlet, outlet);
    }
    
    public override ILogicAndMaterializedValue<FlowShape<OrderEvent, ValidatedOrder>> CreateLogic(
        IActorMaterializer materializer)
    {
        return new Logic(Shape);
    }
    
    private sealed class Logic : GraphStageLogic
    {
        public Logic(FlowShape<OrderEvent, ValidatedOrder> shape) : base(shape)
        {
            SetHandler(shape.Inlet, this, onPush: () =>
            {
                var evt = Grab(shape.Inlet);
                var validated = ValidateOrder(evt);
                Push(shape.Outlet, validated);
            });
            
            SetHandler(shape.Outlet, this, onPull: () => Pull(shape.Inlet));
        }
        
        private ValidatedOrder ValidateOrder(OrderEvent evt)
        {
            // Validation logic
            return new ValidatedOrder(evt.OrderId, true);
        }
    }
}
```

## 🚀 Integration .NET 10

### Modern C# Patterns
```csharp
// Records immutables pour les events
public sealed record OrderCreated(
    Guid OrderId,
    Guid CustomerId,
    DateTime CreatedAt
) : IOrderEvent;

// Value objects avec pattern matching
public abstract record OrderState
{
    public static readonly OrderState Empty = new EmptyState();
    
    public sealed record ActiveState(
        ImmutableList<OrderItem> Items,
        decimal TotalAmount
    ) : OrderState;
    
    public sealed record ConfirmedState(
        ImmutableList<OrderItem> Items,
        decimal TotalAmount,
        DateTime ConfirmedAt
    ) : OrderState;
    
    public sealed record EmptyState() : OrderState;
}

// Pattern matching pour state transitions
public OrderState Transition(OrderState currentState, IOrderEvent evt) => (currentState, evt) switch
{
    (OrderState.Empty, OrderCreated created) => new OrderState.ActiveState(
        ImmutableList<OrderItem>.Empty,
        0m
    ),
    (OrderState.ActiveState active, ItemAdded added) => active with
    {
        Items = active.Items.Add(new OrderItem(added.ProductId, added.Quantity, added.Price)),
        TotalAmount = active.TotalAmount + (added.Quantity * added.Price)
    },
    (OrderState.ActiveState active, OrderConfirmed confirmed) => new OrderState.ConfirmedState(
        active.Items,
        active.TotalAmount,
        confirmed.ConfirmedAt
    ),
    _ => throw new InvalidOperationException($"Invalid transition: {currentState} -> {evt.GetType().Name}")
};
```

### Performance Optimization
```csharp
// Span<T> pour performance memory-efficient
public sealed class OrderParser
{
    public static OrderEvent ParseEvent(ReadOnlySpan<char> eventData)
    {
        var reader = new SpanReader(eventData);
        
        // Efficient parsing without allocations
        var eventType = reader.ReadUntil('|');
        var payload = reader.Remaining;
        
        return eventType switch
        {
            "ORDER_CREATED" => ParseOrderCreated(payload),
            "ITEM_ADDED" => ParseItemAdded(payload),
            "ORDER_CONFIRMED" => ParseOrderConfirmed(payload),
            _ => throw new InvalidOperationException($"Unknown event type: {eventType}")
        };
    }
    
    private static OrderCreated ParseOrderCreated(ReadOnlySpan<char> payload)
    {
        var parts = payload.Split('|');
        return new OrderCreated(
            Guid.Parse(parts[0]),
            Guid.Parse(parts[1]),
            DateTime.Parse(parts[2])
        );
    }
}

// Value objects avec IEquatable<T>
public sealed record OrderItem(
    Guid ProductId,
    int Quantity,
    decimal Price
) : IEquatable<OrderItem>
{
    public decimal TotalPrice => Quantity * Price;
    
    public bool Equals(OrderItem? other) =>
        other is not null &&
        ProductId == other.ProductId &&
        Quantity == other.Quantity &&
        Math.Abs(Price - other.Price) < 0.01m;
}
```

## 📊 Testing Patterns

### Akka.TestKit Integration
```csharp
public class OrderManagerActorTests : TestKit
{
    [Fact]
    public async Task OrderManager_ShouldCreateOrder_WhenValidCommand()
    {
        // Arrange
        var probe = CreateTestProbe<OrderStatus>();
        var orderManager = Sys.ActorOf<OrderManagerActor>("order-manager");
        
        var createOrder = new CreateOrder(
            OrderId: Guid.NewGuid(),
            CustomerId: Guid.NewGuid(),
            Items: new[] { new OrderItem(Guid.NewGuid(), 2, 29.99m) }
        );
        
        // Act
        orderManager.Tell(createOrder, probe.Ref);
        
        // Assert
        var status = await probe.ExpectMsgAsync<OrderStatus>(TimeSpan.FromSeconds(3));
        status.State.Should().Be(OrderState.Active);
    }
    
    [Fact]
    public async Task OrderManager_ShouldRecoverFromSnapshot()
    {
        // Arrange
        var snapshot = new OrderManagerState(
            Orders: new Dictionary<Guid, OrderState>(),
            LastSequenceNr: 42L
        );
        
        var orderManager = Sys.ActorOf<OrderManagerActor>("order-manager");
        
        // Act
        orderManager.Tell(new SaveSnapshotSuccess(snapshot.SequenceNr));
        
        // Assert
        await AwaitCondition(() =>
        {
            var state = orderManager.Ask<OrderManagerState>(new GetState())
                .Result;
            return state.LastSequenceNr == snapshot.SequenceNr;
        }, TimeSpan.FromSeconds(5));
    }
}
```

### Integration Testing with TestContainers
```csharp
public class OrderManagerIntegrationTests : IClassFixture<SqlContainerFixture>
{
    private readonly SqlContainerFixture _container;
    
    public OrderManagerIntegrationTests(SqlContainerFixture container)
    {
        _container = container;
    }
    
    [Fact]
    public async Task OrderManager_ShouldPersistEvents_InDatabase()
    {
        // Arrange
        var config = ConfigurationFactory.ParseString($@"
            akka.persistence.journal.sql-server.connection-string = ""{_container.ConnectionString}""
            akka.persistence.snapshot-store.sql-server.connection-string = ""{_container.ConnectionString}""");
            
        var system = ActorSystem.Create("test-system", config);
        var orderManager = system.ActorOf<OrderManagerActor>("order-manager");
        
        // Act
        var orderId = Guid.NewGuid();
        orderManager.Tell(new CreateOrder(orderId, Guid.NewGuid()));
        
        // Wait for persistence
        await Task.Delay(1000);
        
        // Assert
        using var connection = new SqlConnection(_container.ConnectionString);
        var events = await connection.QueryAsync<EventJournalRow>(
            "SELECT * FROM EventJournal WHERE PersistenceId = @persistenceId ORDER BY SequenceNr",
            new { persistenceId = $"order-{orderId}" });
            
        events.Should().HaveCount(1);
        events.First().EventType.Should().Be("OrderCreated");
    }
}
```

## 🔧 Configuration & Deployment

### Docker Integration
```dockerfile
# Dockerfile pour Akka.NET avec .NET 10
FROM mcr.microsoft.com/dotnet/aspnet:10.0 AS base
WORKDIR /app
EXPOSE 8080
EXPOSE 4053

FROM mcr.microsoft.com/dotnet/sdk:10.0 AS build
WORKDIR /src
COPY ["src/OrderSystem.Api/OrderSystem.Api.csproj", "src/OrderSystem.Api/"]
RUN dotnet restore "src/OrderSystem.Api/OrderSystem.Api.csproj"
COPY . .
WORKDIR "/src/src/OrderSystem.Api"
RUN dotnet build "OrderSystem.Api.csproj" -c Release -o /app/build

FROM build AS publish
RUN dotnet publish "OrderSystem.Api.csproj" -c Release -o /app/publish

FROM base AS final
WORKDIR /app
COPY --from=publish /app/publish .
ENTRYPOINT ["dotnet", "OrderSystem.Api.dll"]
```

### Kubernetes Deployment
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: order-system
spec:
  replicas: 3
  selector:
    matchLabels:
      app: order-system
  template:
    metadata:
      labels:
        app: order-system
    spec:
      containers:
      - name: order-system
        image: order-system:latest
        ports:
        - containerPort: 8080
        - containerPort: 4053
        env:
        - name: AKKA__CLUSTER__SEED_NODES
          value: "akka.tcp://OrderSystem@order-system-0:4053,akka.tcp://OrderSystem@order-system-1:4053,akka.tcp://OrderSystem@order-system-2:4053"
        - name: CONNECTION_STRING
          valueFrom:
            secretKeyRef:
              name: order-system-secrets
              key: database-connection-string
---
apiVersion: v1
kind: Service
metadata:
  name: order-system
spec:
  selector:
    app: order-system
  ports:
  - port: 8080
    targetPort: 8080
  - port: 4053
    targetPort: 4053
  type: LoadBalancer
```

## 📈 Performance & Monitoring

### Metrics Integration
```csharp
public sealed class OrderMetrics : ReceiveActor
{
    private readonly Counter _ordersCreated;
    private readonly Histogram _orderProcessingTime;
    
    public OrderMetrics(IMeterFactory meterFactory)
    {
        _ordersCreated = meterFactory.CreateCounter("orders_created_total", "Total orders created");
        _orderProcessingTime = meterFactory.CreateHistogram("order_processing_duration_seconds", "Order processing time");
        
        Receive<OrderCreated>(HandleOrderCreated);
        Receive<OrderProcessingCompleted>(HandleProcessingCompleted);
    }
    
    private void HandleOrderCreated(OrderCreated evt)
    {
        _ordersCreated.Add(1);
    }
    
    private void HandleProcessingCompleted(OrderProcessingCompleted evt)
    {
        _orderProcessingTime.Record(evt.Duration.TotalSeconds);
    }
}
```

### Health Checks
```csharp
public sealed class AkkaHealthCheck : IHealthCheck
{
    private readonly ActorSystem _system;
    
    public AkkaHealthCheck(ActorSystem system)
    {
        _system = system;
    }
    
    public async Task<HealthCheckResult> CheckHealthAsync(
        HealthCheckContext context,
        CancellationToken cancellationToken = default)
    {
        try
        {
            var cluster = Cluster.Get(_system);
            var status = await cluster.Ask<ClusterStatus>(GetClusterStatus.Instance, 
                TimeSpan.FromSeconds(5));
                
            return status.Members.All(m => m.Status == MemberStatus.Up) 
                ? HealthCheckResult.Healthy("All cluster members are up")
                : HealthCheckResult.Degraded($"Some members are down: {string.Join(", ", status.Members.Where(m => m.Status != MemberStatus.Up).Select(m => m.Address))}");
        }
        catch (Exception ex)
        {
            return HealthCheckResult.Unhealthy("Failed to check cluster status", ex);
        }
    }
}
```

## 🎯 Cas d'Usage

### Systèmes E-Commerce
- Gestion des commandes avec actors
- Inventory management distribué
- Payment processing résilient

### Plateformes Financières
- Transaction processing haute performance
- Audit trails avec event sourcing
- Compliance et régulation

### IoT & Edge Computing
- Device actors pour capteurs
- Stream processing temps réel
- Edge deployment avec clustering

## 📚 Anti-Patterns à Éviter

- **❌** Acteurs avec état mutable externe
- **❌** Blocking calls dans les acteurs
- **❌** Messages trop larges (>1MB)
- **❌** Clustering sans split-brain resolver
- **❌** Persistence sans snapshots
- **❌** Streams sans back-pressure handling

Ce skill fournit une expertise complète pour construire des systèmes distribués Akka.NET de production avec .NET 10.
