name: net-developer
description: Agent IA spécialisé pour le développement .NET avec expertise en C#, ASP.NET Core, Entity Framework, et écosystème Microsoft. Fournit des outils pour créer, tester, déployer et maintenir des applications .NET modernes.
license: Complete terms in LICENSE.txt
---

# Développeur .NET Spécialisé

## Vue d'ensemble

Agent IA expert dans l'écosystème .NET pour développer des applications robustes, scalables et maintenables. Couvre tous les aspects du développement .NET moderne.

**Mots-clés**: .NET, C#, ASP.NET Core, Entity Framework, Azure, Visual Studio, développement web, API REST, microservices, testing, déploiement

## Compétences Principales

### 🎯 Frameworks et Technologies

#### Core .NET
- **.NET 8/9**: Dernières fonctionnalités et améliorations de performance
- **C# 12**: Nouvelles fonctionnalités du langage (primary constructors, collection expressions)
- **ASP.NET Core**: Développement web et API REST
- **Entity Framework Core**: ORM moderne pour l'accès aux données
- **Blazor**: Framework web UI avec C#

#### Architecture et Patterns
- **Microservices**: Architecture basée sur des services indépendants
- **Clean Architecture**: Séparation des responsabilités
- **Domain-Driven Design (DDD)**: Modélisation métier
- **CQRS**: Command Query Responsibility Segregation
- **Repository Pattern**: Abstraction de l'accès aux données

#### Testing et Qualité
- **xUnit**: Framework de testing unitaire
- **Moq**: Framework de mocking
- **FluentAssertions**: Assertions fluides
- **SpecFlow**: Testing BDD
- **Selenium**: Testing E2E pour applications web

### 🛠️ Outils et Environnement

#### Développement
- **Visual Studio 2022**: IDE principal
- **Visual Studio Code**: Éditeur léger
- **Rider**: IDE JetBrains
- **.NET CLI**: Outils en ligne de commande

#### Base de Données
- **SQL Server**: Base de données principale Microsoft
- **PostgreSQL**: Alternative open source
- **SQLite**: Base de données légère pour développement
- **Redis**: Cache et messagerie

#### Cloud et DevOps
- **Azure**: Platform cloud Microsoft
- **Docker**: Conteneurisation
- **GitHub Actions**: CI/CD
- **Azure DevOps**: Pipeline de déploiement

---

# Processus de Développement

## 🚀 Workflow de Projet .NET

### Phase 1: Analyse et Planification

#### 1.1 Comprendre les Besoins Métier
- Analyser les requirements fonctionnels
- Identifier les contraintes techniques
- Définir l'architecture cible
- Planifier la structure du projet

#### 1.2 Choix Techniques
- **Framework**: .NET 8/9 selon requirements
- **Architecture**: Monolith vs Microservices
- **Base de données**: SQL Server vs PostgreSQL
- **Hébergement**: Azure App Service vs Containers

### Phase 2: Initialisation du Projet

#### 2.1 Création du Projet
Utiliser les scripts helper pour créer la structure de base :
```bash
python scripts/create_project.py --name "MyApp" --type webapi --framework net8.0
```

#### 2.2 Configuration Initiale
- Configurer les settings d'application
- Mettre en place la base de données
- Configurer le logging et monitoring
- Initialiser Git et les workflows CI/CD

### Phase 3: Développement

#### 3.1 Architecture en Couches
```
src/
├── MyApp.Domain/           # Entités et logique métier
├── MyApp.Application/      # Services applicatifs
├── MyApp.Infrastructure/   # Accès aux données, services externes
├── MyApp.API/             # Contrôleurs API
└── MyApp.Tests/           # Tests unitaires et intégration
```

#### 3.2 Développement des Fonctionnalités
- Implémenter les entités domaine
- Créer les services applicatifs
- Développer les contrôleurs API
- Ajouter les tests unitaires

### Phase 4: Testing et Qualité

#### 4.1 Tests Unitaires
- Tester la logique métier
- Mock des dépendances externes
- Couverture de code > 80%

#### 4.2 Tests d'Intégration
- Tester les endpoints API
- Valider l'accès aux données
- Tester les workflows complets

#### 4.3 Tests E2E
- Tests automatisés avec Selenium
- Scénarios utilisateur complets
- Testing cross-browser

### Phase 5: Déploiement

#### 5.1 Build et Packaging
- Compilation en mode Release
- Optimisation des performances
- Création des packages Docker

#### 5.2 Déploiement
- Déploiement sur Azure App Service
- Configuration des variables d'environnement
- Monitoring et logging

---

# Scripts Utilitaires

## 📁 Scripts Disponibles

### `scripts/create_project.py`
Crée un nouveau projet .NET avec la structure recommandée :
```bash
python scripts/create_project.py --help
```

**Options:**
- `--name`: Nom du projet
- `--type`: Type (webapi, blazor, console, classlib)
- `--framework`: Version .NET (net8.0, net9.0)
- `--database`: Base de données (sqlserver, postgresql, sqlite)

### `scripts/add_entity.py`
Ajoute une nouvelle entité avec son repository et tests :
```bash
python scripts/add_entity.py --name "Product" --properties "string:Name,decimal:Price"
```

### `scripts/run_tests.py`
Exécute tous les tests avec génération de rapport :
```bash
python scripts/run_tests.py --coverage --report
```

### `scripts/deploy_azure.py**
Déploie l'application sur Azure :
```bash
python scripts/deploy_azure.py --resource-group "MyRG" --app-name "MyApp"
```

---

# Templates et Exemples

## 📋 Templates de Code

### API Controller
```csharp
[ApiController]
[Route("api/[controller]")]
public class ProductsController : ControllerBase
{
    private readonly IProductService _productService;
    
    public ProductsController(IProductService productService)
    {
        _productService = productService;
    }
    
    [HttpGet]
    public async Task<ActionResult<IEnumerable<ProductDto>>> GetProducts()
    {
        var products = await _productService.GetAllProductsAsync();
        return Ok(products);
    }
}
```

### Entity Framework Entity
```csharp
public class Product
{
    public int Id { get; set; }
    public string Name { get; set; } = string.Empty;
    public decimal Price { get; set; }
    public DateTime CreatedAt { get; set; }
    
    // Navigation properties
    public ICollection<OrderItem> OrderItems { get; set; } = new List<OrderItem>();
}
```

### Unit Test avec xUnit
```csharp
public class ProductServiceTests
{
    private readonly Mock<IProductRepository> _mockRepository;
    private readonly ProductService _service;
    
    public ProductServiceTests()
    {
        _mockRepository = new Mock<IProductRepository>();
        _service = new ProductService(_mockRepository.Object);
    }
    
    [Fact]
    public async Task GetProductById_ShouldReturnProduct_WhenProductExists()
    {
        // Arrange
        var productId = 1;
        var expectedProduct = new Product { Id = productId, Name = "Test Product" };
        _mockRepository.Setup(r => r.GetByIdAsync(productId))
                      .ReturnsAsync(expectedProduct);
        
        // Act
        var result = await _service.GetProductByIdAsync(productId);
        
        // Assert
        result.Should().NotBeNull();
        result.Name.Should().Be("Test Product");
    }
}
```

---

# Bonnes Pratiques

## 🎯 Guidelines de Développement

### Code Quality
- **Naming**: Suivre les conventions C# (PascalCase pour public, camelCase pour private)
- **SOLID**: Appliquer les principes SOLID
- **Async/Await**: Utiliser correctement l'asynchronisme
- **Exception Handling**: Gérer les exceptions de manière appropriée

### Performance
- **Entity Framework**: Utiliser AsNoTracking() pour les requêtes en lecture seule
- **Caching**: Implémenter le caching pour les données fréquemment accédées
- **Connection Pooling**: Configurer correctement le pooling de connexions
- **Lazy Loading**: Éviter le lazy loading dans les API

### Sécurité
- **Authentication**: Utiliser ASP.NET Core Identity
- **Authorization**: Implémenter des politiques d'autorisation
- **Input Validation**: Valider tous les entrées utilisateur
- **HTTPS**: Forcer HTTPS en production

### Monitoring
- **Logging**: Utiliser Serilog pour le logging structuré
- **Health Checks**: Implémenter des health checks
- **Application Insights**: Monitoring Azure
- **Error Tracking**: Intégrer un système de tracking d'erreurs

---

# Ressources Externes

## 📚 Documentation

### Documentation Officielle
- **Microsoft Learn**: Documentation complète .NET
- **ASP.NET Core Docs**: Guides et tutoriels
- **Entity Framework Docs**: Documentation ORM
- **Azure Docs**: Services cloud Microsoft

### Outils et Utilitaires
- **NuGet**: Package manager .NET
- **LINQPad**: Testing de requêtes LINQ
- **Postman**: Testing d'API REST
- **SQL Server Management Studio**: Gestion base de données

### Community
- **GitHub**: Projets open source .NET
- **Stack Overflow**: Support technique
- **Microsoft Q&A**: Questions/réponses officielles
- **Reddit r/dotnet**: Community discussions

---

# Utilisation du Skill

Pour utiliser ce skill dans Claude Code :

```bash
# Créer un nouveau projet API
"Utilise le skill net-developer pour créer une API REST .NET 8 pour la gestion des produits"

# Ajouter une entité
"Utilise le skill net-developer pour ajouter une entité Customer avec les propriétés Name, Email, Phone"

# Implémenter un test
"Utilise le skill net-developer pour écrire des tests unitaires pour le ProductService"

# Déployer sur Azure
"Utilise le skill net-developer pour déployer cette application sur Azure App Service"
```

Le skill fournit des instructions complètes, des scripts automatisés et des templates pour accélérer le développement .NET tout en maintenant les meilleures pratiques.
