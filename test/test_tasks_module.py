import pytest
import requests
import uuid
import datetime

BASE_URL = "http://8.147.57.94/api/v1"

STATE = {
    "task_id": None
}

@pytest.fixture(scope="module")
def api():
    session = requests.Session()
    user_data = {
        "username": f"task_tester_{uuid.uuid4().hex[:8]}",
        "email": f"task_{uuid.uuid4().hex[:8]}@example.com",
        "password": "Password123!",
        "nickname": "任务测试员"
    }
    reg_res = session.post(f"{BASE_URL}/users/auth/register/", json=user_data)
    assert reg_res.status_code in (200, 201)
    
    token = reg_res.json().get("data", {}).get("access")
    session.headers.update({"Authorization": f"Bearer {token}"})
    return session


class TestTasksModule:

    def test_01_pricing_meta(self, api):
        res = api.get(f"{BASE_URL}/tasks/tasks/pricing/meta/")
        assert res.status_code == 200
        data = res.json().get("data", {})
        assert "settlement_tracks" in data

    def test_02_pricing_preview(self, api):
        payload = {
            "task_type": "one_time",
            "recurrence": "none",
            "settlement_track": "exploration",
            "difficulty_level": "high",
            "estimated_focus_minutes": 180,
            "tags": ["research", "coding"]
        }
        res = api.post(f"{BASE_URL}/tasks/tasks/pricing/preview/", json=payload)
        assert res.status_code == 200

    def test_03_create_task(self, api):
        payload = {
            "title": "背单词 30 分钟 (自动化)",
            "task_type": "daily",
            "recurrence": "daily",
            "settlement_track": "regular",
            "difficulty_level": "medium",
            "metric_key": "study_minutes",
            "target_value": 30,
            "progress_target": 100,
            "status": "active"
        }
        res = api.post(f"{BASE_URL}/tasks/tasks/", json=payload)
        assert res.status_code == 201
        STATE["task_id"] = res.json()["data"]["id"]

    def test_04_get_task_list(self, api):
        res = api.get(f"{BASE_URL}/tasks/tasks/")
        assert res.status_code == 200
        # 【修复】适配分页可能在 data.results 下，或者直接在 data 下的情况
        data = res.json().get("data", {})
        results = data.get("results", []) if isinstance(data, dict) else data
        assert len(results) >= 1, "任务列表中未获取到刚创建的任务"

    def test_05_get_single_task(self, api):
        tid = STATE["task_id"]
        res = api.get(f"{BASE_URL}/tasks/tasks/{tid}/")
        assert res.status_code == 200
        assert res.json()["data"]["title"] == "背单词 30 分钟 (自动化)"

    def test_06_patch_task(self, api):
        tid = STATE["task_id"]
        payload = {"description": "这是被 PATCH 更新后的描述"}
        res = api.patch(f"{BASE_URL}/tasks/tasks/{tid}/", json=payload)
        assert res.status_code == 200
        # 【修复】读取 data 下的 description
        assert res.json()["data"]["description"] == payload["description"]

    def test_07_put_task(self, api):
        tid = STATE["task_id"]
        payload = {
            "title": "全量更新后的任务标题",
            "description": "全量更新",
            "task_type": "one_time",
            "recurrence": "none",
            "settlement_track": "regular",
            "difficulty_level": "high",
            "progress_target": 100,
            "status": "active"
        }
        res = api.put(f"{BASE_URL}/tasks/tasks/{tid}/", json=payload)
        assert res.status_code == 200
        # 【修复】读取 data 下的 title
        assert res.json()["data"]["title"] == payload["title"]

    def test_08_pricing_request(self, api):
        """【已知Bug】此接口目前会报 502 Bad Gateway，测试可能会失败，等待后端修复"""
        tid = STATE["task_id"]
        payload = {
            "title": "待AI定价的任务",
            "task_type": "one_time",
            "recurrence": "none",
            "settlement_track": "exploration",
            "difficulty_level": "high",
            "progress_target": 100,
            "status": "active"
        }
        res = api.post(f"{BASE_URL}/tasks/tasks/{tid}/pricing/request/", json=payload)
        # 如果依然报 502，可以在终端看到红色报错
        assert res.status_code == 200, f"发起AI定价请求失败(502表示后端崩溃): {res.text}"

    def test_09_pricing_apply(self, api):
        tid = STATE["task_id"]
        payload = {
            "reward_primary": 120,
            "penalty_primary": 25,
            "pricing_payload": {"model": "gpt-4-turbo"}
        }
        res = api.post(f"{BASE_URL}/tasks/tasks/{tid}/pricing/apply/", json=payload)
        assert res.status_code == 200
        assert res.json()["data"]["reward_primary"] == 120

    def test_10_complete_task(self, api):
        tid = STATE["task_id"]
        today_str = datetime.date.today().strftime("%Y-%m-%d")
        payload = {"occurrence_date": today_str, "progress": 100}
        res = api.post(f"{BASE_URL}/tasks/tasks/{tid}/complete/", json=payload)
        assert res.status_code == 200
        assert res.json()["data"]["status"] == "completed"

    def test_11_delete_task(self, api):
        tid = STATE["task_id"]
        res = api.delete(f"{BASE_URL}/tasks/tasks/{tid}/")
        assert res.status_code == 204