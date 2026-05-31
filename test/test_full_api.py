
import pytest
import requests
import uuid
import urllib3  # 新增

# 禁用因为忽略证书校验而产生的控制台烦人警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE_URL = "https://8.147.57.94/api/v1"

STATE = {
    "access_token": None,
    "refresh_token": None,
    "task_id": None,
    "shop_item_id": None,
    "redemption_id": None
}

TEST_USER = {
    "username": f"user_{uuid.uuid4().hex[:8]}",
    "email": f"test_{uuid.uuid4().hex[:8]}@example.com",
    "password": "Password123!",
    "nickname": "自动化测试员"
}

@pytest.fixture(scope="session")
def api():
    session = requests.Session()
    session.verify = False  # 关键修复：全局关闭此 Session 的 SSL 证书验证！
    return session

class Test01CommonAndAuth:
    def test_health_check(self, api):
        assert api.get(f"{BASE_URL}/common/health/").status_code == 200

    def test_legal_documents(self, api):
        assert api.get(f"{BASE_URL}/common/legal-documents/").status_code == 200

    def test_register(self, api):
        res = api.post(f"{BASE_URL}/users/auth/register/", json=TEST_USER)
        assert res.status_code in (200, 201), f"注册失败: {res.text}"
        data = res.json().get("data", {})
        STATE["access_token"] = data.get("access")
        STATE["refresh_token"] = data.get("refresh")
        api.headers.update({"Authorization": f"Bearer {STATE['access_token']}"})

    def test_login(self, api):
        res = api.post(f"{BASE_URL}/users/auth/login/", json={
            "username": TEST_USER["username"],
            "password": TEST_USER["password"]
        })
        assert res.status_code == 200

    def test_token_refresh(self, api):
        res = api.post(f"{BASE_URL}/users/auth/refresh/", json={"refresh": STATE["refresh_token"]})
        assert res.status_code == 200, f"刷新Token失败: {res.text}"
        # 【修复点】兼容统一返回格式或原生返回格式
        resp_json = res.json()
        new_token = resp_json.get("data", {}).get("access") or resp_json.get("access")
        assert new_token is not None, "未能从响应中提取到新 access token"
        api.headers.update({"Authorization": f"Bearer {new_token}"})

class Test02Profile:
    def test_get_me(self, api):
        res = api.get(f"{BASE_URL}/users/me/")
        assert res.status_code == 200, f"获取个人信息失败: {res.text}"

    def test_patch_me(self, api):
        res = api.patch(f"{BASE_URL}/users/me/", json={"gender": "male", "bio": "自动化测试更新签名"})
        assert res.status_code == 200, f"更新个人信息失败: {res.text}"

    def test_profile_meta(self, api):
        res = api.get(f"{BASE_URL}/users/profile/meta/")
        assert res.status_code == 200

    def test_profile_prompts(self, api):
        res = api.get(f"{BASE_URL}/users/profile/prompts/")
        assert res.status_code == 200

    def test_profile_prompts_ack(self, api):
        res = api.post(f"{BASE_URL}/users/profile/prompts/ack/", json={"layer": "basic"})
        assert res.status_code == 200, f"Prompt ACK失败 (可能是502后端崩溃): {res.text}"

    def test_stable_profile(self, api):
        res_get = api.get(f"{BASE_URL}/users/profile/stable/")
        assert res_get.status_code == 200
        res_patch = api.patch(f"{BASE_URL}/users/profile/stable/", json={"reward_preference": "instant", "self_discipline_score": 8})
        assert res_patch.status_code == 200

    def test_dynamic_profile(self, api):
        res_get = api.get(f"{BASE_URL}/users/profile/dynamic/")
        assert res_get.status_code == 200
        res_patch = api.patch(f"{BASE_URL}/users/profile/dynamic/", json={"stress_level": 5, "sleep_quality": "medium"})
        assert res_patch.status_code == 200

class Test03Tasks:
    def test_task_pricing_meta(self, api):
        res = api.get(f"{BASE_URL}/tasks/tasks/pricing/meta/")
        assert res.status_code == 200, f"获取定价元信息失败: {res.text}"

    def test_task_crud(self, api):
        task_data = {
            "title": "自动化测试任务",
            "task_type": "one_time",
            "recurrence": "none",
            "settlement_track": "regular",
            "difficulty_level": "medium",
            "progress_target": 100,
            "status": "active"
        }
        res_create = api.post(f"{BASE_URL}/tasks/tasks/", json=task_data)
        assert res_create.status_code in (200, 201), f"创建任务失败(502表示后端崩溃): {res.text}"
        tid = res_create.json()["data"]["id"]
        
        assert api.get(f"{BASE_URL}/tasks/tasks/").status_code == 200
        assert api.get(f"{BASE_URL}/tasks/tasks/{tid}/").status_code == 200
        
        # 删除任务收尾
        api.delete(f"{BASE_URL}/tasks/tasks/{tid}/")

class Test04Wallet:
    def test_get_wallet(self, api):
        res = api.get(f"{BASE_URL}/wallet/")
        assert res.status_code == 200, f"获取钱包失败: {res.text}"

    def test_wallet_transactions(self, api):
        assert api.get(f"{BASE_URL}/wallet/transactions/").status_code == 200

    def test_debt_reset(self, api):
        assert api.post(f"{BASE_URL}/wallet/debt-reset/").status_code == 200

class Test05Shop:
    def test_shop_meta(self, api):
        assert api.get(f"{BASE_URL}/shop/items/meta/").status_code == 200

    def test_pricing_meta(self, api):
        res = api.get(f"{BASE_URL}/shop/items/pricing/meta/")
        assert res.status_code != 404, "404 错误：后端未注册该路由 /shop/items/pricing/meta/"
        assert res.status_code == 200

    def test_inventory(self, api):
        assert api.get(f"{BASE_URL}/shop/inventory/").status_code == 200

class Test06Gacha:
    def test_gacha_cycle(self, api):
        res_pools = api.get(f"{BASE_URL}/gacha/pools/")
        assert res_pools.status_code == 200, f"获取卡池列表失败: {res_pools.text}"

class Test07Reports:
    def test_dashboard(self, api):
        assert api.get(f"{BASE_URL}/reports/dashboard/").status_code == 200