import requests
import urllib3

# 关闭安全警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

session = requests.Session()
session.verify = False
session.trust_env = False
session.proxies = {"http": None, "https": None}

url_health = "https://8.147.57.94/api/v1/common/health/"
url_register = "https://8.147.57.94/api/v1/users/auth/register/"

print("================= 第一步：测试 GET 健康检查 =================")
try:
    res1 = session.get(url_health, allow_redirects=False)
    print(f"状态码: {res1.status_code}")
    print(f"响应头: {res1.headers}")
    if res1.status_code in (301, 302):
        print(f"🚨 警告！发生了重定向，后端要把我们引向 -> {res1.headers.get('Location')}")
    else:
        print(f"返回内容: {res1.text[:200]}")
except Exception as e:
    print(f"请求失败: {e}")

print("\n================= 第二步：测试 POST 注册 =================")
try:
    res2 = session.post(url_register, json={"username": "debug123", "password": "123"})
    print(f"最终实际请求的 URL: {res2.url}")
    print(f"重定向历史: {res2.history}")
    print(f"状态码: {res2.status_code}")
    print("⬇️ 下面是返回的 HTML 具体内容 ⬇️")
    print(res2.text[:500]) # 打印前500个字符看看HTML里写了啥
except Exception as e:
    print(f"请求失败: {e}")