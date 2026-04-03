#!/usr/bin/env python3
"""
Script pour tuer les processus utilisant le port 8765 avant de démarrer le serveur.
Utilisé pour résoudre l'erreur: "une seule utilisation de chaque adresse de socket (protocole/adresse réseau/port) est habituellement autorisée"
"""

import socket
import subprocess
import sys
import time

import psutil


def find_processes_using_port(port):
    """Trouve tous les processus utilisant le port spécifié."""
    processes = []
    try:
        # Méthode 1: utiliser netstat
        result = subprocess.run(['netstat', '-ano'], capture_output=True, text=True)
        lines = result.stdout.split('\n')
        for line in lines:
            if f':{port}' in line and 'LISTENING' in line:
                parts = line.split()
                if len(parts) >= 5:
                    pid = parts[-1]
                    try:
                        process = psutil.Process(int(pid))
                        processes.append({
                            'pid': int(pid),
                            'name': process.name(),
                            'cmdline': ' '.join(process.cmdline())
                        })
                    except (psutil.NoSuchProcess, psutil.AccessDenied, ValueError):
                        processes.append({
                            'pid': int(pid),
                            'name': 'Unknown',
                            'cmdline': 'Unknown'
                        })
    except Exception as e:
        print(f"Erreur avec netstat: {e}")
    
    try:
        # Méthode 2: utiliser psutil directement
        for proc in psutil.process_iter(['pid', 'name', 'connections']):
            try:
                connections = proc.info['connections']
                if connections:
                    for conn in connections:
                        if conn.status == 'LISTEN' and conn.laddr.port == port:
                            processes.append({
                                'pid': proc.info['pid'],
                                'name': proc.info['name'],
                                'cmdline': ' '.join(proc.cmdline()) if proc.cmdline() else 'Unknown'
                            })
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
    except Exception as e:
        print(f"Erreur avec psutil: {e}")
    
    # Supprimer les doublons
    unique_processes = {}
    for proc in processes:
        pid = proc['pid']
        if pid not in unique_processes:
            unique_processes[pid] = proc
    
    return list(unique_processes.values())

def kill_process(pid):
    """Tue un processus par son PID."""
    try:
        process = psutil.Process(pid)
        print(f"Arrêt du processus {pid} ({process.name()})...")
        process.terminate()
        
        # Attendre un peu que le processus se termine
        time.sleep(2)
        
        # Si le processus est toujours en vie, le forcer
        if process.is_running():
            print(f"Le processus {pid} est toujours en vie, force de l'arrêt...")
            process.kill()
            time.sleep(1)
        
        return not process.is_running()
    except psutil.NoSuchProcess:
        print(f"Le processus {pid} n'existe plus.")
        return True
    except psutil.AccessDenied:
        print(f"Accès refusé pour tuer le processus {pid}. Essayez avec des privilèges administrateur.")
        return False
    except Exception as e:
        print(f"Erreur en tuant le processus {pid}: {e}")
        return False

def is_port_available(port):
    """Vérifie si le port est disponible."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('localhost', port))
            return True
    except OSError:
        return False

def main():
    port = 8765
    
    print(f"Vérification du port {port}...")
    
    if is_port_available(port):
        print(f"Le port {port} est déjà disponible.")
        return 0
    
    print(f"Le port {port} est occupé. Recherche des processus...")
    
    processes = find_processes_using_port(port)
    
    if not processes:
        print(f"Aucun processus trouvé utilisant le port {port}, mais le port est toujours occupé.")
        print("Le port peut être utilisé par un service système.")
        return 1
    
    print(f"\n{len(processes)} processus trouvé(s) utilisant le port {port}:")
    for proc in processes:
        print(f"  PID: {proc['pid']}, Nom: {proc['name']}, Commande: {proc['cmdline']}")
    
    print("\nArrêt des processus...")
    
    killed_count = 0
    for proc in processes:
        if kill_process(proc['pid']):
            killed_count += 1
            print(f"✓ Processus {proc['pid']} arrêté avec succès")
        else:
            print(f"✗ Échec de l'arrêt du processus {proc['pid']}")
    
    print(f"\n{killed_count}/{len(processes)} processus arrêté(s).")
    
    # Vérifier à nouveau si le port est disponible
    time.sleep(2)
    if is_port_available(port):
        print(f"✓ Le port {port} est maintenant disponible.")
        return 0
    else:
        print(f"✗ Le port {port} est toujours occupé.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
