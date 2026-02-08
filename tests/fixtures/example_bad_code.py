# Fichier avec problèmes intentionnels pour tester le Quality Scorer
password = "hardcoded_secret_123"  # CRITICAL: Credentials hardcodées
def very_complex_function(x, y, z):
    # MEDIUM/HIGH: Fonction trop complexe
    if x > 0:
        if y > 0:
            if z > 0:
                for i in range(x):
                    if i % 2 == 0:
                        if i > 5:
                            while i < 20:
                                if i == 15:
                                    return i * y * z
                                i += 1
    return 0
try:
    some_operation()
except:  # MEDIUM: Bare except
    pass
eval("dangerous_code")  # HIGH: eval() dangereux