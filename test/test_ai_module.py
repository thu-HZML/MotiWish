import pytest
import requests
import uuid
import urllib3

# 忽略因为忽略 SSL 证书验证而产生的警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE_URL = "https://8.147.57.94/api/v1"

# 全局状态字典
STATE = {
    "job_id": None
}

@pytest.fixture(scope="module")
def api():
    """初始化测试环境：注册新用户、登录并获取 Token"""
    session = requests.Session()
    
    # 忽略 SSL 证书与本地代理拦截
    session.verify = False
    session.trust_env = False
    session.proxies = {"http": None, "https": None}
    
    user_data = {
        "username": f"ai_tester_{uuid.uuid4().hex[:8]}",
        "email": f"ai_{uuid.uuid4().hex[:8]}@example.com",
        "password": "Password123!"
    }
    
    # 注册
    reg_res = session.post(f"{BASE_URL}/users/auth/register/", json=user_data)
    assert reg_res.status_code in (200, 201), f"预备步骤失败: {reg_res.text}"
    token = reg_res.json().get("data", {}).get("access")
    session.headers.update({"Authorization": f"Bearer {token}"})
    
    return session


class TestAIModule:
    """ 专门测试 AI 报告模块的 6 个 API """

    def test_01_create_job(self, api):
        """POST /api/v1/ai/report-jobs/ - 创建 AI 报告任务"""
        payload = {
            "report_type": "daily",
            "prompt_context": "这是一些提示词内容"
        }
        res = api.post(f"{BASE_URL}/ai/report-jobs/", json=payload)
        
        if res.status_code == 502:
            pytest.fail("【后端 Bug】创建 AI 任务时后端崩溃了 (502 Bad Gateway)")
            
        assert res.status_code == 201, f"创建 AI 任务失败: {res.text}"
        
        STATE["job_id"] = res.json().get("data", {}).get("id")
        assert STATE["job_id"] is not None

    def test_02_get_job_list(self, api):
        """GET /api/v1/ai/report-jobs/ - 获取 AI 报告任务列表"""
        res = api.get(f"{BASE_URL}/ai/report-jobs/")
        assert res.status_code == 200, f"获取列表失败: {res.text}"
        
        results = res.json().get("data", {}).get("results", []) or res.json().get("results", [])
        assert len(results) >= 1

    def test_03_get_single_job(self, api):
        """GET /api/v1/ai/report-jobs/{id}/ - 获取单个 AI 报告任务"""
        jid = STATE.get("job_id")
        if not jid: pytest.skip("前置创建步骤未成功，跳过")
        
        res = api.get(f"{BASE_URL}/ai/report-jobs/{jid}/")
        assert res.status_code == 200
        # 【修改点】断言可写字段 report_type，避开只读字段 summary
        assert res.json().get("data", {}).get("report_type") == "daily"

    def test_04_put_job(self, api):
        """PUT /api/v1/ai/report-jobs/{id}/ - 全量更新 AI 报告任务"""
        jid = STATE.get("job_id")
        if not jid: pytest.skip("前置创建步骤未成功，跳过")
        
        payload = {
            "report_type": "monthly",
            "prompt_context": "修改后的提示词"
        }
        res = api.put(f"{BASE_URL}/ai/report-jobs/{jid}/", json=payload)
        assert res.status_code == 200, f"全量修改失败: {res.text}"
        
        data = res.json().get("data", res.json())
        assert data["report_type"] == "monthly"

    def test_05_patch_job(self, api):
        """PATCH /api/v1/ai/report-jobs/{id}/ - 部分更新 AI 报告任务"""
        jid = STATE.get("job_id")
        if not jid: pytest.skip("前置创建步骤未成功，跳过")
        
        # 【修改点】修改可写字段 report_type (将其从 monthly 改回 daily)，避开只读字段 status
        payload = {
            "report_type": "daily"
        }
        res = api.patch(f"{BASE_URL}/ai/report-jobs/{jid}/", json=payload)
        assert res.status_code == 200, f"部分修改失败: {res.text}"
        
        data = res.json().get("data", res.json())
        assert data["report_type"] == "daily"

    def test_06_delete_job(self, api):
        """DELETE /api/v1/ai/report-jobs/{id}/ - 删除 AI 报告任务"""
        jid = STATE.get("job_id")
        if not jid: pytest.skip("前置创建步骤未成功，跳过")
        
        res = api.delete(f"{BASE_URL}/ai/report-jobs/{jid}/")
        assert res.status_code == 204, f"删除失败: {res.text}"
        
        check_res = api.get(f"{BASE_URL}/ai/report-jobs/{jid}/")
        assert check_res.status_code == 404, "记录被删除了但依然能查到"