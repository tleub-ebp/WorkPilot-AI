#!/usr/bin/env python3
"""
Test script for Analytics API endpoints.
"""

import requests
import json
import time

def test_analytics_api():
    """Test the analytics API endpoints."""
    base_url = "http://localhost:9000"
    
    print("🧪 Testing Analytics API...")
    
    # Test endpoints
    endpoints = [
        "/analytics/overview",
        "/analytics/builds",
        "/analytics/metrics/tokens",
        "/analytics/metrics/qa",
        "/analytics/metrics/agent-performance",
        "/analytics/metrics/errors",
        "/analytics/specs"
    ]
    
    results = {}
    
    for endpoint in endpoints:
        try:
            url = f"{base_url}{endpoint}"
            print(f"\n📡 Testing {endpoint}...")
            
            response = requests.get(url, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                results[endpoint] = {
                    "status": "✅ SUCCESS",
                    "status_code": response.status_code,
                    "data_keys": list(data.keys()) if isinstance(data, dict) else type(data).__name__
                }
                print(f"   ✅ {endpoint} - Status: {response.status_code}")
                print(f"   📊 Keys: {results[endpoint]['data_keys']}")
            else:
                results[endpoint] = {
                    "status": "❌ FAILED",
                    "status_code": response.status_code,
                    "error": response.text
                }
                print(f"   ❌ {endpoint} - Status: {response.status_code}")
                print(f"   🚨 Error: {response.text}")
                
        except requests.exceptions.RequestException as e:
            results[endpoint] = {
                "status": "❌ CONNECTION ERROR",
                "error": str(e)
            }
            print(f"   ❌ {endpoint} - Connection Error: {e}")
        except Exception as e:
            results[endpoint] = {
                "status": "❌ ERROR",
                "error": str(e)
            }
            print(f"   ❌ {endpoint} - Error: {e}")
    
    # Summary
    print(f"\n📊 Test Summary:")
    success_count = sum(1 for r in results.values() if "SUCCESS" in r["status"])
    total_count = len(results)
    
    print(f"   ✅ Successful: {success_count}/{total_count}")
    print(f"   ❌ Failed: {total_count - success_count}/{total_count}")
    
    if success_count == total_count:
        print(f"\n🎉 All Analytics API endpoints are working!")
    else:
        print(f"\n⚠️  Some endpoints failed. Check the backend logs.")
    
    return results

if __name__ == "__main__":
    test_analytics_api()
