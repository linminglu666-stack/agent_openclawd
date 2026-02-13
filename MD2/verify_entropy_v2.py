import sys
import os
import time
import json
import urllib.request
import threading
import asyncio
from unittest.mock import MagicMock
import types

# Ensure code is in path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
sys.path.insert(0, os.path.join(os.path.abspath(os.path.dirname(__file__)), "code"))

# Mock utils module BEFORE importing service
mock_utils = types.ModuleType("utils")
mock_utils.validate_workflow_create = MagicMock(return_value=MagicMock(is_valid=True))
mock_utils.validate_schedule_create = MagicMock(return_value=MagicMock(is_valid=True))
mock_utils.validate_schedule_update = MagicMock(return_value=MagicMock(is_valid=True))
mock_utils.validate_run_trigger = MagicMock(return_value=MagicMock(is_valid=True))
mock_utils.validate_work_item_enqueue = MagicMock(return_value=MagicMock(is_valid=True))
mock_utils.validate_work_item_claim = MagicMock(return_value=MagicMock(is_valid=True))
mock_utils.validate_work_item_ack = MagicMock(return_value=MagicMock(is_valid=True))
mock_utils.validate_approval_decision = MagicMock(return_value=MagicMock(is_valid=True))
mock_utils.validate_system_control = MagicMock(return_value=MagicMock(is_valid=True))
mock_utils.get_logger = MagicMock(return_value=MagicMock())

# Register mocks
sys.modules["utils"] = mock_utils
sys.modules["code.utils"] = mock_utils
# Also utils.logger need to be mockable via from utils.logger import ...
mock_logger_mod = types.ModuleType("utils.logger")
mock_logger_mod.get_logger = MagicMock(return_value=MagicMock())
sys.modules["utils.logger"] = mock_logger_mod
sys.modules["code.utils.logger"] = mock_logger_mod

mock_serializer_mod = types.ModuleType("utils.serializer")
mock_serializer_class = MagicMock()
mock_serializer_class.to_json = MagicMock(side_effect=json.dumps)
mock_serializer_mod.Serializer = mock_serializer_class
sys.modules["utils.serializer"] = mock_serializer_mod
sys.modules["code.utils.serializer"] = mock_serializer_mod

# Import module to patch classes
import code.services.bff_service as bff_module
from code.services.bff_service import BffService

# Patch dependencies to avoid instantiation errors
async def async_mock(*args, **kwargs):
    return MagicMock()

async def async_token_mock(*args, **kwargs):
    return {"user": {"user_id": "test_user"}}

async def async_bool_mock(*args, **kwargs):
    return True

async def async_policy_mock(*args, **kwargs):
    return {"allowed": True}

mock_auth_provider = MagicMock()
mock_auth_provider.authenticate = MagicMock(side_effect=async_mock)
mock_auth_provider.validate_token = MagicMock(side_effect=async_token_mock)
bff_module.InMemoryAuthProvider = MagicMock(return_value=mock_auth_provider)

mock_authorizer = MagicMock()
mock_authorizer.add_role = MagicMock(side_effect=async_mock)
mock_authorizer.assign_role = MagicMock(side_effect=async_mock)
mock_authorizer.check_permission = MagicMock(side_effect=async_bool_mock)
bff_module.InMemoryAuthorizer = MagicMock(return_value=mock_authorizer)

mock_policy = MagicMock()
mock_policy.decide = MagicMock(side_effect=async_policy_mock)
bff_module.SimplePolicyEngine = MagicMock(return_value=mock_policy)

mock_redactor = MagicMock()
mock_redactor.redact = MagicMock(side_effect=lambda x: x)
bff_module.SimpleRedactor = MagicMock(return_value=mock_redactor)

bff_module.RiskScorer = MagicMock()
# Mock SystemManager if needed, but it is defined in the file so likely works if subprocess works.

# Set up environment
os.environ["OPENCLAW_BFF_PORT"] = "9999"

tmp_dir = os.path.join(os.getcwd(), "tmp_verify")
os.makedirs(tmp_dir, exist_ok=True)
os.environ["OPENCLAW_STATE_DIR"] = os.path.join(tmp_dir, "state")
os.environ["OPENCLAW_LOG_DIR"] = os.path.join(tmp_dir, "log")
os.environ["OPENCLAW_RUNTIME_DIR"] = os.path.join(tmp_dir, "run")

def run_server():
    print("Starting BFF Service...")
    svc = BffService()
    asyncio.run(svc.initialize())
    # Server runs in daemon thread. Keep main thread alive.
    try:
        while True:
            time.sleep(1)
    except Exception:
        pass

def test_endpoints():
    base_url = "http://localhost:9999/v1/governance/entropy"
    headers = {"Authorization": "Bearer test_token"}
    
    print("Waiting for server to start...")
    time.sleep(3) 
    
    # 1. Test Config
    print(f"\nTesting {base_url}/config...")
    try:
        req = urllib.request.Request(f"{base_url}/config", headers=headers)
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            print("Config Response OK")
            config = data.get("config", {})
            if "inbox_ttl_days" not in config:
                print("FAILED: inbox_ttl_days missing in config")
                os._exit(1)
            print(f"Config: {json.dumps(config, indent=2)}")
    except Exception as e:
        print(f"FAILED: config endpoint error: {e}")
        os._exit(1)

    # 2. Test Metrics
    print(f"\nTesting {base_url}/metrics...")
    try:
        req = urllib.request.Request(f"{base_url}/metrics", headers=headers)
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            print("Metrics Response OK")
            metrics = data.get("metrics", {})
            if "by_category" not in metrics:
                print("FAILED: by_category missing in metrics")
                os._exit(1)
            categories = metrics["by_category"]
            if "input" not in categories:
                print("FAILED: 'input' category missing")
                os._exit(1)
            print(f"Metrics: {json.dumps(metrics, indent=2)}")
    except Exception as e:
        print(f"FAILED: metrics endpoint error: {e}")
        os._exit(1)

    # 3. Test History
    print(f"\nTesting {base_url}/history...")
    try:
        req = urllib.request.Request(f"{base_url}/history", headers=headers)
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            print("History Response OK")
            history = data.get("history", [])
            if not isinstance(history, list):
                print("FAILED: history is not a list")
                os._exit(1)
            if len(history) == 0:
                 print("FAILED: history is empty (should have been auto-snapshotted)")
                 os._exit(1)
            print(f"History entries: {len(history)}")
            print(f"Latest history: {json.dumps(history[0], indent=2)}")
    except Exception as e:
        print(f"FAILED: history endpoint error: {e}")
        os._exit(1)

    print("\nSUCCESS: All endpoints verified.")
    os._exit(0)

if __name__ == "__main__":
    # Start server in a separate thread
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    
    test_endpoints()
