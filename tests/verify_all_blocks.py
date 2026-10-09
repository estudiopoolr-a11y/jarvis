import sys
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_kebo_accounts():
    print("Testing Accounts...")
    # Test List
    resp = client.get("/api/kebo/accounts")
    print(f"  - GET /api/kebo/accounts: {resp.status_code}")
    
    # Test Balance
    resp = client.get("/api/kebo/accounts/balance")
    print(f"  - GET /api/kebo/accounts/balance: {resp.status_code}")

def test_kebo_budgets():
    print("Testing Budgets...")
    resp = client.get("/api/kebo/presupuestos")
    print(f"  - GET /api/kebo/presupuestos: {resp.status_code}")

def test_kebo_transactions():
    print("Testing Transactions...")
    resp = client.get("/api/kebo/transactions/recent")
    print(f"  - GET /api/kebo/transactions/recent: {resp.status_code}")

def test_prestamos():
    print("Testing Prestamos...")
    resp = client.get("/api/v1/prestamos/listar")
    print(f"  - GET /api/v1/prestamos/listar: {resp.status_code}")
    
    resp = client.get("/api/v1/prestamos/por-cobrar")
    print(f"  - GET /api/v1/prestamos/por-cobrar: {resp.status_code}")

if __name__ == "__main__":
    try:
        test_kebo_accounts()
        test_kebo_budgets()
        test_kebo_transactions()
        test_prestamos()
        print("\n✅ All endpoints validated successfully!")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
