name: benchmark-dotnet
description: Expertise BenchmarkDotNet pour performance testing et optimisation .NET. Patterns production pour micro-benchmarks, memory profiling et performance analysis.
license: Complete terms in LICENSE.txt
---

# BenchmarkDotNet - Performance Testing & Optimization

## Vue d'ensemble

Skill spécialisé dans BenchmarkDotNet pour créer des benchmarks de performance production-ready, analyser les résultats et optimiser le code .NET 10.

**Mots-clés**: BenchmarkDotNet, performance testing, micro-benchmarks, memory profiling, optimization, .NET 10, performance analysis

## 🎯 Compétences Principales

### Benchmark Design
- **Micro-benchmarks**: Tests unitaires de performance précis
- **Macro-benchmarks**: Tests de scénarios réels
- **Memory Benchmarks**: Allocation et garbage collection
- **Concurrency Benchmarks**: Performance multi-threading

### Performance Analysis
- **Results Interpretation**: Analyse des métriques de performance
- **Statistical Analysis**: Significance testing et confidence intervals
- **Memory Profiling**: Allocation patterns et memory leaks
- **JIT Optimization**: Impact du JIT sur performance

### Optimization Strategies
- **Code Optimization**: Patterns pour code haute performance
- **Memory Optimization**: Réduction allocations et pooling
- **Algorithm Optimization**: Complexité et data structures
- **Platform Optimization**: .NET 10 specific optimizations

### CI/CD Integration
- **Automated Benchmarks**: Intégration dans pipelines CI/CD
- **Regression Detection**: Détection automatique de régressions
- **Performance Gates**: Gates de performance pour déploiement
- **Reporting**: Rapports de performance automatisés

## 🛠️ Patterns Production

### 1. Benchmark Setup de Base
```csharp
// BenchmarkDotNet configuration pour .NET 10
[MemoryDiagnoser]
[SimpleJob(RuntimeMoniker.Net80)]
[SimpleJob(RuntimeMoniker.NativeAot80)]
[SimpleJob(RuntimeMoniker.Net90)]
[SimpleJob(RuntimeMoniker.NativeAot90)]
[SimpleJob(RuntimeMoniker.Net100)]
[SimpleJob(RuntimeMoniker.NativeAot100)]
[GroupBenchmarksBy(BenchmarkLogicalGroupRule.ByCategory)]
[Categories("String Processing", "Collections", "LINQ", "Async", "Memory")]
[Orderer(SummaryOrderPolicy.FastestToSlowest, MethodOrderPolicy.Alphabetical)]
[Outliers(OutlierMode.RemoveUpper)]
[Column("Method", "Mean", "Error", "StdDev", "Median", "Ratio", "RatioSD", "Gen0", "Gen1", "Allocated")]
[HideColumns("Error", "StdDev", "RatioSD")]
public class PerformanceBenchmarks
{
    private const string TestString = "Hello, World! This is a test string for benchmarking purposes.";
    private readonly List<int> _testData = Enumerable.Range(1, 1000).ToList();
    private readonly int[] _testArray = Enumerable.Range(1, 1000).ToArray();
    
    [Benchmark(Baseline = true)]
    [Arguments(100)]
    [Arguments(1000)]
    [Arguments(10000)]
    public int StringLength_Linq(int count)
    {
        var result = 0;
        for (int i = 0; i < count; i++)
        {
            result += TestString.Length;
        }
        return result;
    }
    
    [Benchmark]
    [Arguments(100)]
    [Arguments(1000)]
    [Arguments(10000)]
    public int StringLength_Span(int count)
    {
        var result = 0;
        var span = TestString.AsSpan();
        for (int i = 0; i < count; i++)
        {
            result += span.Length;
        }
        return result;
    }
    
    [Benchmark]
    [Arguments(100)]
    [Arguments(1000)]
    [Arguments(10000)]
    public int StringLength_ReadOnlySpan(int count)
    {
        var result = 0;
        ReadOnlySpan<char> span = TestString;
        for (int i = 0; i < count; i++)
        {
            result += span.Length;
        }
        return result;
    }
}
```

### 2. Memory Allocation Benchmarks
```csharp
[MemoryDiagnoser]
[SimpleJob(RuntimeMoniker.Net100)]
[Group("Memory Allocation")]
public class MemoryAllocationBenchmarks
{
    private readonly List<string> _strings = new();
    
    [Benchmark(Baseline = true)]
    public void StringConcatenation_Plus()
    {
        string result = "";
        for (int i = 0; i < 100; i++)
        {
            result += "Item " + i + ", ";
        }
    }
    
    [Benchmark]
    public void StringConcatenation_StringBuilder()
    {
        var sb = new StringBuilder();
        for (int i = 0; i < 100; i++)
        {
            sb.Append("Item ").Append(i).Append(", ");
        }
        var result = sb.ToString();
    }
    
    [Benchmark]
    public void StringConcatenation_Span()
    {
        Span<char> buffer = stackalloc char[1000];
        var position = 0;
        for (int i = 0; i < 100; i++)
        {
            var item = $"Item {i}, ";
            item.AsSpan().CopyTo(buffer[position..]);
            position += item.Length;
        }
        var result = buffer[..position].ToString();
    }
    
    [Benchmark]
    public void ListAdd_Regular()
    {
        var list = new List<string>();
        for (int i = 0; i < 1000; i++)
        {
            list.Add($"Item {i}");
        }
    }
    
    [Benchmark]
    public void ListAdd_Capacity()
    {
        var list = new List<string>(1000);
        for (int i = 0; i < 1000; i++)
        {
            list.Add($"Item {i}");
        }
    }
    
    [Benchmark]
    public void ArrayFill_Regular()
    {
        var array = new string[1000];
        for (int i = 0; i < 1000; i++)
        {
            array[i] = $"Item {i}";
        }
    }
    
    [Benchmark]
    public void ArrayFill_Span()
    {
        var array = new string[1000];
        var span = array.AsSpan();
        for (int i = 0; i < span.Length; i++)
        {
            span[i] = $"Item {i}";
        }
    }
}
```

### 3. Collection Performance Benchmarks
```csharp
[MemoryDiagnoser]
[SimpleJob(RuntimeMoniker.Net100)]
[Group("Collections")]
public class CollectionBenchmarks
{
    private readonly int[] _source = Enumerable.Range(1, 10000).ToArray();
    
    [Benchmark(Baseline = true)]
    public int[] Filter_Array_Linq()
    {
        return _source.Where(x => x % 2 == 0).ToArray();
    }
    
    [Benchmark]
    public int[] Filter_Array_Span()
    {
        var result = new List<int>();
        var span = _source.AsSpan();
        
        for (int i = 0; i < span.Length; i++)
        {
            if (span[i] % 2 == 0)
            {
                result.Add(span[i]);
            }
        }
        
        return result.ToArray();
    }
    
    [Benchmark]
    public int[] Filter_Array_MemoryPool()
    {
        using var pool = MemoryPool<int>.Shared;
        var buffer = pool.Rent(_source.Length);
        var count = 0;
        
        var span = _source.AsSpan();
        for (int i = 0; i < span.Length; i++)
        {
            if (span[i] % 2 == 0)
            {
                buffer.Span[count++] = span[i];
            }
        }
        
        var result = buffer.Span[..count].ToArray();
        return result;
    }
    
    [Benchmark]
    public int Sum_Array_ForEach()
    {
        var sum = 0;
        foreach (var item in _source)
        {
            sum += item;
        }
        return sum;
    }
    
    [Benchmark]
    public int Sum_Array_Span()
    {
        var sum = 0;
        var span = _source.AsSpan();
        for (int i = 0; i < span.Length; i++)
        {
            sum += span[i];
        }
        return sum;
    }
    
    [Benchmark]
    public int Sum_Array_Linq()
    {
        return _source.Sum();
    }
    
    [Benchmark]
    public int Sum_Array_Parallel()
    {
        return _source.AsParallel().Sum();
    }
}
```

### 4. Async Performance Benchmarks
```csharp
[MemoryDiagnoser]
[SimpleJob(RuntimeMoniker.Net100)]
[Group("Async Operations")]
public class AsyncBenchmarks
{
    private readonly HttpClient _httpClient = new();
    private readonly string _testUrl = "https://httpbin.org/get";
    
    [Benchmark(Baseline = true)]
    public async Task<string> HttpClient_Single()
    {
        var response = await _httpClient.GetAsync(_testUrl);
        return await response.Content.ReadAsStringAsync();
    }
    
    [Benchmark]
    public async Task<string[]> HttpClient_Sequential()
    {
        var tasks = new Task<string>[10];
        for (int i = 0; i < 10; i++)
        {
            var response = await _httpClient.GetAsync(_testUrl);
            tasks[i] = response.Content.ReadAsStringAsync();
        }
        
        var results = new string[10];
        for (int i = 0; i < 10; i++)
        {
            results[i] = await tasks[i];
        }
        
        return results;
    }
    
    [Benchmark]
    public async Task<string[]> HttpClient_Parallel()
    {
        var tasks = new Task<string>[10];
        for (int i = 0; i < 10; i++)
        {
            tasks[i] = GetSingleResponse();
        }
        
        return await Task.WhenAll(tasks);
    }
    
    private async Task<string> GetSingleResponse()
    {
        var response = await _httpClient.GetAsync(_testUrl);
        return await response.Content.ReadAsStringAsync();
    }
    
    [Benchmark]
    public async Task<int> TaskWhenAll_Simple()
    {
        var tasks = new Task<int>[100];
        for (int i = 0; i < 100; i++)
        {
            tasks[i] = Task.FromResult(i);
        }
        
        var results = await Task.WhenAll(tasks);
        return results.Sum();
    }
    
    [Benchmark]
    public async Task<int> TaskWhenAll_ValueTask()
    {
        var tasks = new ValueTask<int>[100];
        for (int i = 0; i < 100; i++)
        {
            tasks[i] = new ValueTask<int>(i);
        }
        
        var results = new int[100];
        for (int i = 0; i < 100; i++)
        {
            results[i] = await tasks[i];
        }
        
        return results.Sum();
    }
}
```

### 5. Custom Benchmark Attributes
```csharp
// Attributs personnalisés pour benchmarks spécifiques
public class PerformanceRegressionAttribute : Attribute
{
    public double MaxRegressionRatio { get; set; } = 1.05; // 5% max regression
    public string BaselineCommit { get; set; } = "main";
}

public class MemoryLimitAttribute : Attribute
{
    public long MaxBytes { get; set; }
    public string Description { get; set; }
}

[MemoryLimit(MaxBytes = 1024, Description = "Should not allocate more than 1KB")]
[PerformanceRegression(MaxRegressionRatio = 1.02)]
public class OptimizedBenchmarks
{
    [Benchmark]
    public void ProcessData_Optimized()
    {
        // Implementation optimized
    }
    
    [Benchmark]
    public void ProcessData_Unoptimized()
    {
        // Implementation unoptimized for comparison
    }
}
```

### 6. Benchmark Results Analysis
```csharp
// Analyseur de résultats de benchmarks
public class BenchmarkResultAnalyzer
{
    public void AnalyzeResults(string resultsPath)
    {
        var results = LoadBenchmarkResults(resultsPath);
        
        // Analyze performance regressions
        var regressions = DetectRegressions(results);
        
        // Analyze memory allocations
        var memoryIssues = DetectMemoryIssues(results);
        
        // Generate report
        GenerateReport(regressions, memoryIssues);
    }
    
    private List<PerformanceRegression> DetectRegressions(BenchmarkResults results)
    {
        var regressions = new List<PerformanceRegression>();
        
        foreach (var benchmark in results.Benchmarks)
        {
            var baseline = benchmark.Results.FirstOrDefault(r => r.IsBaseline);
            var current = benchmark.Results.FirstOrDefault(r => !r.IsBaseline);
            
            if (baseline != null && current != null)
            {
                var ratio = current.Mean / baseline.Mean;
                
                if (ratio > 1.05) // 5% regression threshold
                {
                    regressions.Add(new PerformanceRegression
                    {
                        BenchmarkName = benchmark.Name,
                        BaselineMean = baseline.Mean,
                        CurrentMean = current.Mean,
                        RegressionRatio = ratio,
                        Significance = CalculateSignificance(baseline, current)
                    });
                }
            }
        }
        
        return regressions;
    }
    
    private List<MemoryIssue> DetectMemoryIssues(BenchmarkResults results)
    {
        var issues = new List<MemoryIssue>();
        
        foreach (var benchmark in results.Benchmarks)
        {
            var result = benchmark.Results.FirstOrDefault();
            
            if (result != null)
            {
                // Check for excessive allocations
                if (result.AllocatedBytes > 1024 * 1024) // 1MB threshold
                {
                    issues.Add(new MemoryIssue
                    {
                        BenchmarkName = benchmark.Name,
                        AllocatedBytes = result.AllocatedBytes,
                        Gen0Collections = result.Gen0Collections,
                        Gen1Collections = result.Gen1Collections,
                        IssueType = MemoryIssueType.ExcessiveAllocation
                    });
                }
                
                // Check for high GC pressure
                if (result.Gen0Collections > 1000)
                {
                    issues.Add(new MemoryIssue
                    {
                        BenchmarkName = benchmark.Name,
                        AllocatedBytes = result.AllocatedBytes,
                        Gen0Collections = result.Gen0Collections,
                        Gen1Collections = result.Gen1Collections,
                        IssueType = MemoryIssueType.HighGCPressure
                    });
                }
            }
        }
        
        return issues;
    }
    
    private double CalculateSignificance(BenchmarkResult baseline, BenchmarkResult current)
    {
        // Calculate statistical significance using t-test
        var pooledStdDev = Math.Sqrt(
            (Math.Pow(baseline.StdDev, 2) * (baseline.N - 1) + 
             Math.Pow(current.StdDev, 2) * (current.N - 1)) / 
            (baseline.N + current.N - 2));
        
        var tStatistic = (current.Mean - baseline.Mean) / 
                        (pooledStdDev * Math.Sqrt(1.0 / baseline.N + 1.0 / current.N));
        
        // Return p-value (simplified calculation)
        return 2 * (1 - NormalCDF(Math.Abs(tStatistic)));
    }
    
    private double NormalCDF(double x)
    {
        // Simplified normal CDF calculation
        return 0.5 * (1 + Erf(x / Math.Sqrt(2)));
    }
    
    private double Erf(double x)
    {
        // Approximation of error function
        var a1 = 0.254829592;
        var a2 = -0.284496736;
        var a3 = 1.421413741;
        var a4 = -1.453152027;
        var a5 = 1.061405429;
        var p = 0.3275911;
        
        var sign = x >= 0 ? 1 : -1;
        x = Math.Abs(x);
        
        var t = 1.0 / (1.0 + p * x);
        var y = 1.0 - (((((a5 * t + a4) * t) + a3) * t + a2) * t + a1) * t * Math.Exp(-x * x);
        
        return sign * y;
    }
    
    private void GenerateReport(List<PerformanceRegression> regressions, List<MemoryIssue> memoryIssues)
    {
        var report = new StringBuilder();
        report.AppendLine("# Performance Analysis Report");
        report.AppendLine($"Generated: {DateTime.UtcNow:yyyy-MM-dd HH:mm:ss} UTC");
        report.AppendLine();
        
        if (regressions.Any())
        {
            report.AppendLine("## Performance Regressions");
            report.AppendLine();
            
            foreach (var regression in regressions.OrderByDescending(r => r.RegressionRatio))
            {
                report.AppendLine($"### {regression.BenchmarkName}");
                report.AppendLine($"- **Regression Ratio**: {regression.RegressionRatio:P2}");
                report.AppendLine($"- **Baseline**: {regression.BaselineMean:F2} ns");
                report.AppendLine($"- **Current**: {regression.CurrentMean:F2} ns");
                report.AppendLine($"- **Significance**: {regression.Significance:P3}");
                report.AppendLine();
            }
        }
        
        if (memoryIssues.Any())
        {
            report.AppendLine("## Memory Issues");
            report.AppendLine();
            
            foreach (var issue in memoryIssues)
            {
                report.AppendLine($"### {issue.BenchmarkName}");
                report.AppendLine($"- **Issue Type**: {issue.IssueType}");
                report.AppendLine($"- **Allocated**: {issue.AllocatedBytes:N0} bytes");
                report.AppendLine($"- **Gen0 Collections**: {issue.Gen0Collections:N0}");
                report.AppendLine($"- **Gen1 Collections**: {issue.Gen1Collections:N0}");
                report.AppendLine();
            }
        }
        
        File.WriteAllText("performance-report.md", report.ToString());
    }
}
```

### 7. CI/CD Integration
```csharp
// Integration dans les pipelines CI/CD
public class BenchmarkCiValidator
{
    private readonly string _baselinePath;
    private readonly double _maxRegressionRatio;
    private readonly long _maxAllocationBytes;
    
    public BenchmarkCiValidator(string baselinePath, double maxRegressionRatio = 1.05, long maxAllocationBytes = 1024 * 1024)
    {
        _baselinePath = baselinePath;
        _maxRegressionRatio = maxRegressionRatio;
        _maxAllocationBytes = maxAllocationBytes;
    }
    
    public async Task<bool> ValidateBenchmarkResults(string currentResultsPath)
    {
        var baselineResults = LoadBenchmarkResults(_baselinePath);
        var currentResults = LoadBenchmarkResults(currentResultsPath);
        
        var hasRegressions = false;
        var hasMemoryIssues = false;
        
        foreach (var benchmark in currentResults.Benchmarks)
        {
            var baseline = baselineResults.Benchmarks.FirstOrDefault(b => b.Name == benchmark.Name);
            
            if (baseline != null)
            {
                var current = benchmark.Results.FirstOrDefault();
                var baselineResult = baseline.Results.FirstOrDefault();
                
                if (current != null && baselineResult != null)
                {
                    // Check performance regression
                    var ratio = current.Mean / baselineResult.Mean;
                    if (ratio > _maxRegressionRatio)
                    {
                        Console.WriteLine($"❌ Performance regression detected in {benchmark.Name}: {ratio:P2} regression");
                        hasRegressions = true;
                    }
                    
                    // Check memory allocation
                    if (current.AllocatedBytes > _maxAllocationBytes)
                    {
                        Console.WriteLine($"❌ Memory allocation too high in {benchmark.Name}: {current.AllocatedBytes:N0} bytes");
                        hasMemoryIssues = true;
                    }
                }
            }
        }
        
        if (hasRegressions || hasMemoryIssues)
        {
            Console.WriteLine("❌ Benchmark validation failed!");
            return false;
        }
        
        Console.WriteLine("✅ All benchmarks passed validation!");
        return true;
    }
    
    private BenchmarkResults LoadBenchmarkResults(string path)
    {
        // Load and parse BenchmarkDotNet results
        var json = File.ReadAllText(path);
        return JsonSerializer.Deserialize<BenchmarkResults>(json);
    }
}
```

### 8. GitHub Actions Integration
```yaml
# .github/workflows/benchmark.yml
name: Performance Benchmarks

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  benchmark:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
      with:
        fetch-depth: 0
    
    - name: Setup .NET
      uses: actions/setup-dotnet@v3
      with:
        dotnet-version: '10.0.x'
    
    - name: Restore dependencies
      run: dotnet restore
    
    - name: Build
      run: dotnet build --configuration Release --no-restore
    
    - name: Run benchmarks
      run: |
        dotnet run --project Benchmarks --configuration Release -- \
          --exporters json \
          --artifacts ./benchmark-results \
          --filter "*"
    
    - name: Upload benchmark results
      uses: actions/upload-artifact@v3
      with:
        name: benchmark-results
        path: benchmark-results/
    
    - name: Validate performance
      run: |
        dotnet run --project BenchmarkValidator -- \
          --baseline ./benchmark-results/baseline.json \
          --current ./benchmark-results/current.json
    
    - name: Comment PR with results
      if: github.event_name == 'pull_request'
      uses: actions/github-script@v6
      with:
        script: |
          const fs = require('fs');
          const results = JSON.parse(fs.readFileSync('./benchmark-results/current.json', 'utf8'));
          
          let comment = '# Benchmark Results\n\n';
          comment += '| Benchmark | Mean (ns) | Allocated (bytes) |\n';
          comment += '|----------|------------|------------------|\n';
          
          results.Benchmarks.forEach(benchmark => {
            const result = benchmark.Results[0];
            comment += `| ${benchmark.Name} | ${result.Mean.toFixed(2)} | ${result.AllocatedBytes} |\n`;
          });
          
          github.rest.issues.createComment({
            issue_number: context.issue.number,
            owner: context.repo.owner,
            repo: context.repo.repo,
            body: comment
          });
```

## 🚀 .NET 10 Performance Features

### Modern C# Performance Patterns
```csharp
// .NET 10 performance optimizations
public class PerformanceOptimizations
{
    // Span<T> pour zero-allocation
    public static bool ContainsDigit_Span(ReadOnlySpan<char> text)
    {
        for (int i = 0; i < text.Length; i++)
        {
            if (char.IsDigit(text[i]))
                return true;
        }
        return false;
    }
    
    // Pattern matching optimisé
    public static int ProcessValue(object value) => value switch
    {
        int i => i * 2,
        string s when int.TryParse(s, out var num) => num * 2,
        double d when d > 0 => (int)d * 2,
        _ => 0
    };
    
    // Value objects avec IEquatable<T>
    public readonly record struct Point(double X, double Y) : IEquatable<Point>
    {
        public double Distance => Math.Sqrt(X * X + Y * Y);
        
        public bool Equals(Point other) => 
            Math.Abs(X - other.X) < double.Epsilon && 
            Math.Abs(Y - other.Y) < double.Epsilon;
    }
    
    // Pooling pour réduction allocations
    private static readonly ObjectPool<StringBuilder> StringBuilderPool = 
        new DefaultObjectPool<StringBuilder>(
            new StringBuilderPooledObjectPolicy());
    
    public static string BuildStringEfficiently(IEnumerable<string> parts)
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
    
    // Memory-mapped files pour gros datasets
    public static void ProcessLargeFile(string filePath)
    {
        using var mmf = MemoryMappedFile.CreateFromFile(filePath);
        using var accessor = mmf.CreateViewAccessor(0, 0, MemoryMappedFileAccess.Read);
        
        var buffer = new byte[4096];
        for (long offset = 0; offset < accessor.Capacity; offset += buffer.Length)
        {
            var bytesToRead = Math.Min(buffer.Length, (int)(accessor.Capacity - offset));
            accessor.ReadArray(offset, buffer, 0, bytesToRead);
            
            // Process buffer
            ProcessBuffer(buffer.AsSpan(0, bytesToRead));
        }
    }
    
    private static void ProcessBuffer(ReadOnlySpan<byte> buffer)
    {
        // Process data efficiently
    }
}
```

### Native AOT Optimizations
```csharp
// Optimizations pour Native AOT
[UnsafeAccessor(UnsafeAccessorKind.Field, Name = "_value")]
public static partial class UnsafeAccessors
{
    [UnsafeAccessor(UnsafeAccessorKind.Method, Name = "GetValue")]
    public static extern int GetValue(this SomeType obj);
}

// Code compatible avec Native AOT
public class NativeAotOptimizations
{
    // Éviter la réflexion avec Source Generators
    [GeneratedRegex(@"\d+")]
    private static partial Regex NumberRegex();
    
    public static bool ContainsNumber(string text)
    {
        return NumberRegex().IsMatch(text);
    }
    
    // Utiliser des delegates compilés
    private static readonly Func<string, bool> IsDigit = s => s.All(char.IsDigit);
    
    public static bool ValidateDigits(string input)
    {
        return IsDigit(input);
    }
    
    // Préférenc pour les types value
    public readonly struct ValidationResult
    {
        public readonly bool IsValid;
        public readonly string ErrorMessage;
        
        public ValidationResult(bool isValid, string errorMessage = "")
        {
            IsValid = isValid;
            ErrorMessage = errorMessage;
        }
    }
    
    // Éviter les allocations dans les chemins chauds
    public static ValidationResult ValidateInput(ReadOnlySpan<char> input)
    {
        if (input.IsEmpty)
            return new ValidationResult(false, "Input cannot be empty");
            
        if (input.Length > 100)
            return new ValidationResult(false, "Input too long");
            
        return new ValidationResult(true);
    }
}
```

## 📊 Performance Monitoring

### Custom Metrics Collection
```csharp
public class PerformanceMetrics
{
    private readonly IMetricsFactory _metricsFactory;
    private readonly Counter<int> _operationCounter;
    private readonly Histogram<double> _operationDuration;
    private readonly Gauge<int> _activeOperations;
    
    public PerformanceMetrics(IMetricsFactory metricsFactory)
    {
        _metricsFactory = metricsFactory;
        
        _operationCounter = _metricsFactory.CreateCounter<int>(
            "operations_total",
            "Total number of operations",
            new[] { "operation_type", "status" });
            
        _operationDuration = _metricsFactory.CreateHistogram<double>(
            "operation_duration_seconds",
            "Operation duration in seconds",
            new[] { "operation_type" });
            
        _activeOperations = _metricsFactory.CreateGauge<int>(
            "active_operations",
            "Number of currently active operations",
            new[] { "operation_type" });
    }
    
    public IDisposable MeasureOperation(string operationType)
    {
        _activeOperations.Add(1, new KeyValuePair<string, object>[]
        {
            new("operation_type", operationType)
        });
        
        return new OperationMeasurement(
            this,
            operationType,
            Stopwatch.StartNew());
    }
    
    private void RecordOperation(string operationType, bool success, TimeSpan duration)
    {
        _operationCounter.Add(1, new KeyValuePair<string, object>[]
        {
            new("operation_type", operationType),
            new("status", success ? "success" : "failure")
        });
        
        _operationDuration.Record(duration.TotalSeconds, new KeyValuePair<string, object>[]
        {
            new("operation_type", operationType)
        });
        
        _activeOperations.Add(-1, new KeyValuePair<string, object>[]
        {
            new("operation_type", operationType)
        });
    }
    
    private sealed class OperationMeasurement : IDisposable
    {
        private readonly PerformanceMetrics _metrics;
        private readonly string _operationType;
        private readonly Stopwatch _stopwatch;
        
        public OperationMeasurement(PerformanceMetrics metrics, string operationType, Stopwatch stopwatch)
        {
            _metrics = metrics;
            _operationType = operationType;
            _stopwatch = stopwatch;
        }
        
        public void Dispose()
        {
            _stopwatch.Stop();
            _metrics.RecordOperation(_operationType, true, _stopwatch.Elapsed);
        }
    }
}
```

## 🎯 Cas d'Usage

### API Performance Testing
- Benchmarks pour endpoints API
- Validation de performance sous charge
- Monitoring de latence

### Algorithm Optimization
- Comparaison d'algorithmes
- Complexité analysis
- Data structure performance

### Memory Management
- Allocation patterns analysis
- Garbage collection optimization
- Memory leak detection

## 📚 Anti-Patterns à Éviter

- **❌** Benchmarks sans warmup
- **❌** Tests avec données trop petites
- **❌** Ignorer le JIT warmup
- **❌** Pas de statistical significance testing
- **❌** Benchmarks sans baseline
- **❌** Tests sur machine de développement

Ce skill fournit une expertise complète pour créer et analyser des benchmarks de performance avec BenchmarkDotNet et .NET 10.
