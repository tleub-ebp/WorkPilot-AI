# Script PowerShell pour diagnostiquer et corriger la configuration Azure DevOps
# Trouve automatiquement où "MeCa Web" est configuré et propose la correction

Write-Host "=" -NoNewline -ForegroundColor Cyan
Write-Host ("=" * 69) -ForegroundColor Cyan
Write-Host "  DIAGNOSTIC AZURE DEVOPS - Recherche de 'MeCa Web'" -ForegroundColor Cyan
Write-Host ("=" * 70) -ForegroundColor Cyan
Write-Host ""

$foundIssues = @()

# 1. Chercher dans tous les fichiers .env
Write-Host "1. Recherche dans les fichiers .env..." -ForegroundColor Yellow
Write-Host ("-" * 70)

$envFiles = Get-ChildItem -Path . -Filter ".env" -Recurse -File -ErrorAction SilentlyContinue

if ($envFiles.Count -eq 0) {
    Write-Host "   Aucun fichier .env trouvé" -ForegroundColor Gray
} else {
    foreach ($file in $envFiles) {
        Write-Host "   Vérification: $($file.FullName)" -ForegroundColor Gray
        
        $content = Get-Content $file.FullName -ErrorAction SilentlyContinue
        $azureProjectLine = $content | Select-String -Pattern "^\s*AZURE_DEVOPS_PROJECT\s*=" -Raw
        
        if ($azureProjectLine) {
            Write-Host "     Trouvé: $azureProjectLine" -ForegroundColor White
            
            if ($azureProjectLine -match "MeCa\s*Web") {
                Write-Host "     ❌ PROBLÈME DÉTECTÉ!" -ForegroundColor Red
                $foundIssues += @{
                    File = $file.FullName
                    Line = $azureProjectLine
                    Type = ".env"
                }
            } elseif ($azureProjectLine -match "M[eé]Ca") {
                Write-Host "     ✅ Configuration correcte" -ForegroundColor Green
            } else {
                Write-Host "     ⚠️  Valeur inattendue" -ForegroundColor Yellow
            }
        }
    }
}
Write-Host ""

# 2. Vérifier les variables d'environnement système
Write-Host "2. Variables d'environnement système..." -ForegroundColor Yellow
Write-Host ("-" * 70)

$envVars = Get-ChildItem Env: | Where-Object Name -Like "*AZURE*"
if ($envVars.Count -eq 0) {
    Write-Host "   Aucune variable AZURE_* trouvée" -ForegroundColor Gray
} else {
    foreach ($var in $envVars) {
        $displayValue = $var.Value
        if ($var.Name -match "PAT|TOKEN") {
            $displayValue = if ($var.Value.Length -gt 10) { $var.Value.Substring(0, 10) + "..." } else { "***" }
        }
        Write-Host "   $($var.Name) = $displayValue" -ForegroundColor White
        
        if ($var.Name -eq "AZURE_DEVOPS_PROJECT" -and $var.Value -match "MeCa\s*Web") {
            Write-Host "     ❌ PROBLÈME DÉTECTÉ dans les variables système!" -ForegroundColor Red
            $foundIssues += @{
                Var = $var.Name
                Value = $var.Value
                Type = "EnvVar"
            }
        }
    }
}
Write-Host ""

# 3. Vérifier l'URL Git remote
Write-Host "3. URL Git remote..." -ForegroundColor Yellow
Write-Host ("-" * 70)

try {
    $gitRemote = git remote get-url origin 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "   $gitRemote" -ForegroundColor White
        
        if ($gitRemote -match "dev\.azure\.com/([^/]+)/([^/]+)/_git/(.+)") {
            $org = $matches[1]
            $project = [System.Web.HttpUtility]::UrlDecode($matches[2])
            $repo = [System.Web.HttpUtility]::UrlDecode($matches[3])
            
            Write-Host ""
            Write-Host "   Décomposition:" -ForegroundColor Gray
            Write-Host "     Organisation : $org" -ForegroundColor White
            Write-Host "     PROJET       : $project  ← Devrait être utilisé" -ForegroundColor Green
            Write-Host "     Repository   : $repo" -ForegroundColor White
        }
    } else {
        Write-Host "   ⚠️  Impossible de récupérer le remote Git" -ForegroundColor Yellow
    }
} catch {
    Write-Host "   ⚠️  Erreur: $_" -ForegroundColor Yellow
}
Write-Host ""

# 4. Résumé et actions
Write-Host ("=" * 70) -ForegroundColor Cyan
if ($foundIssues.Count -eq 0) {
    Write-Host "✅ Aucun problème détecté!" -ForegroundColor Green
    Write-Host ""
    Write-Host "La configuration semble correcte. Le problème vient peut-être:" -ForegroundColor Yellow
    Write-Host "1. Du cache de l'application (fermez complètement Auto-Claude)" -ForegroundColor Yellow
    Write-Host "2. D'un autre fichier .env dans un sous-dossier non scanné" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Essayez:" -ForegroundColor Cyan
    Write-Host "  1. Fermez complètement Auto-Claude" -ForegroundColor White
    Write-Host "  2. Redémarrez l'application" -ForegroundColor White
    Write-Host "  3. Réessayez l'import de work items" -ForegroundColor White
} else {
    Write-Host "❌ $($foundIssues.Count) problème(s) détecté(s)!" -ForegroundColor Red
    Write-Host ""
    
    foreach ($issue in $foundIssues) {
        if ($issue.Type -eq ".env") {
            Write-Host "Fichier: $($issue.File)" -ForegroundColor Red
            Write-Host "  Ligne actuelle: $($issue.Line)" -ForegroundColor Gray
            Write-Host "  Correction:     AZURE_DEVOPS_PROJECT=MéCa" -ForegroundColor Green
            Write-Host ""
            
            $response = Read-Host "  Corriger automatiquement ce fichier? (o/n)"
            if ($response -eq "o" -or $response -eq "O") {
                try {
                    $content = Get-Content $issue.File
                    $newContent = $content -replace "AZURE_DEVOPS_PROJECT\s*=\s*MeCa\s*Web", "AZURE_DEVOPS_PROJECT=MéCa"
                    $newContent | Set-Content $issue.File -Encoding UTF8
                    Write-Host "  ✅ Fichier corrigé!" -ForegroundColor Green
                } catch {
                    Write-Host "  ❌ Erreur lors de la correction: $_" -ForegroundColor Red
                }
            }
        } elseif ($issue.Type -eq "EnvVar") {
            Write-Host "Variable système: $($issue.Var) = $($issue.Value)" -ForegroundColor Red
            Write-Host "  Cette variable doit être supprimée ou corrigée manuellement." -ForegroundColor Yellow
            Write-Host "  Commande pour supprimer:" -ForegroundColor Gray
            Write-Host "    [Environment]::SetEnvironmentVariable('$($issue.Var)', `$null, 'User')" -ForegroundColor White
        }
    }
}

Write-Host ("=" * 70) -ForegroundColor Cyan
Write-Host ""

# Ajouter la référence System.Web pour UrlDecode
Add-Type -AssemblyName System.Web
