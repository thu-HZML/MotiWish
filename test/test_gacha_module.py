import pytest
import requests
import uuid
import datetime
import urllib3

# 忽略因为忽略 SSL 证书验证而产生的警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 使用 https 和 Nginx 端口
BASE_URL = "https://8.147.57.94/api/v1"

# 全局状态字典，用于在步骤间传递数据
STATE = {
    "pool_id": None,      # 卡池 ID
    "record_id": None     # 抽卡记录 ID
}

@pytest.fixture(scope="module")
def api():
    """初始化测试环境：注册新用户、登录并获取 Token，避开 SSL 证书与代理拦截"""
    session = requests.Session()
    session.verify = False
    session.trust_env = False
    session.proxies = {"http": None, "https": None}
    
    user_data = {
        "username": f"gacha_tester_{uuid.uuid4().hex[:8]}",
        "email": f"gacha_{uuid.uuid4().hex[:8]}@example.com",
        "password": "Password123!",
        "nickname": "抽卡欧皇"
    }
    
    # 注册并登录获取 Token
    reg_res = session.post(f"{BASE_URL}/users/auth/register/", json=user_data)
    assert reg_res.status_code in (200, 201), f"注册失败: {reg_res.text}"
    token = reg_res.json().get("data", {}).get("access")
    session.headers.update({"Authorization": f"Bearer {token}"})
    
    return session


class TestGachaModule:
    """ 专门测试 Gacha (抽卡系统) 的 6 个 API """

    # ================= 0. 准备工作：赚取抽卡金 =================

    def test_00_earn_money_for_gacha(self, api):
        """【前置赚取抽卡金】创建并结算一个高额奖励任务，获取 10000 块一级代币，确保可以随便抽"""
        # 1. 建立高额打工任务
        task_res = api.post(f"{BASE_URL}/tasks/tasks/", json={
            "title": "为了抽卡拼命打工",
            "task_type": "one_time",
            "recurrence": "none",
            "settlement_track": "regular",
            "progress_target": 100,
            "status": "active"
        })
        assert task_res.status_code == 201, "创建任务失败"
        tid = task_res.json()["data"]["id"]

        # 2. 定价发放 10000 块一级代币
        api.post(f"{BASE_URL}/tasks/tasks/{tid}/pricing/apply/", json={
            "reward_primary": 10000, 
            "penalty_primary": 0, 
            "pricing_payload": {}
        })

        # 3. 完成任务，钱入钱包
        today_str = datetime.date.today().strftime("%Y-%m-%d")
        comp_res = api.post(f"{BASE_URL}/tasks/tasks/{tid}/complete/", json={"occurrence_date": today_str, "progress": 100})
        assert comp_res.status_code == 200, "结算代币失败"

    # ================= 1. 卡池列表与详情 =================

    def test_01_get_pools_list(self, api):
        """GET /api/v1/gacha/pools/ - 获取卡池列表"""
        res = api.get(f"{BASE_URL}/gacha/pools/")
        assert res.status_code == 200, f"获取卡池列表失败: {res.text}"
        
        # 支持分页数据的包装格式提取
        results = res.json().get("data", {}).get("results", []) or res.json().get("results", [])
        
        # 容错处理
        if not results:
            pytest.skip("⚠️ 无法测试：数据库当前卡池列表为空，请在后台添加配置好的卡池数据")
            
        # 提取第一个活跃卡池作为抽卡对象
        if isinstance(results[0], dict) and "data" in results[0]:
            STATE["pool_id"] = results[0]["data"][0]["id"]
        else:
            STATE["pool_id"] = results[0]["id"]
            
        assert STATE["pool_id"] is not None

    def test_02_get_single_pool(self, api):
        """GET /api/v1/gacha/pools/{id}/ - 获取单个卡池"""
        pid = STATE.get("pool_id")
        if not pid: pytest.skip("未获取到活跃卡池")
        
        res = api.get(f"{BASE_URL}/gacha/pools/{pid}/")
        assert res.status_code == 200, f"获取单个卡池失败: {res.text}"
        assert "common_rate" in res.json().get("data", {})

    def test_03_get_pool_state(self, api):
        """GET /api/v1/gacha/pools/{id}/state/ - 查看当前卡池保底状态"""
        pid = STATE.get("pool_id")
        if not pid: pytest.skip("未获取到活跃卡池")
        
        res = api.get(f"{BASE_URL}/gacha/pools/{pid}/state/")
        assert res.status_code == 200, f"获取卡池保底状态失败: {res.text}"
        
        data = res.json().get("data", {})
        # 验证返回了保底数据字段（在还未抽卡前，累计次数应都为初始零值）
        assert "total_draws" in data
        assert "draws_since_legendary" in data

    # ================= 2. 抽卡行为测试 =================

    def test_04_draw_gacha(self, api):
        """POST /api/v1/gacha/pools/{id}/draw/ - 执行抽卡"""
        pid = STATE.get("pool_id")
        if not pid: pytest.skip("未获取到活跃卡池")
        
        # 扣除刚才任务赚取的一级金币，执行一发单抽
        res = api.post(f"{BASE_URL}/gacha/pools/{pid}/draw/", json={"times": 1})
        
        if res.status_code == 502:
            pytest.fail("【后端 Bug】执行单抽时后端服务崩溃（502 Bad Gateway）")
            
        assert res.status_code == 200, f"执行单抽失败: {res.text}"
        
        # 获取返回的抽卡记录并提取记录 ID
        data_list = res.json().get("data", [])
        assert len(data_list) == 1, "未返回抽卡成功的单次数据"
        STATE["record_id"] = data_list[0]["id"]
        
        # 断言出货数据结构完整（校验返回了奖励级别和扣费数值）
        assert "cost_primary" in data_list[0]
        assert "reward_tier" in data_list[0]

    # ================= 3. 抽卡记录查询 =================

    def test_05_get_records_list(self, api):
        """GET /api/v1/gacha/records/ - 获取抽卡记录"""
        res = api.get(f"{BASE_URL}/gacha/records/")
        assert res.status_code == 200, f"获取抽卡记录失败: {res.text}"
        
        if STATE.get("record_id"):
            results = res.json().get("data", {}).get("results", []) or res.json().get("results", [])
            # 列表必须至少存在刚才抽出的那一条记录
            assert len(results) >= 1

    def test_06_get_single_record(self, api):
        """GET /api/v1/gacha/records/{id}/ - 获取单条抽卡记录"""
        rid = STATE.get("record_id")
        if not rid: pytest.skip("前面步骤未能成功获取抽卡记录 ID")
        
        res = api.get(f"{BASE_URL}/gacha/records/{rid}/")
        assert res.status_code == 200, f"获取单条记录失败: {res.text}"
        
        data = res.json().get("data", {})
        assert data["id"] == rid
        assert "reward_tier" in data  # 如 "common", "rare", "epic", "legendary"