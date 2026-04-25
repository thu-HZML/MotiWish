from apps.users.models import User


def build_user_prompt_context(user: User) -> dict:
    return {
        "user_profile": user.build_prompt_profile(),
        "timezone": user.timezone,
    }


def build_goal_planner_prompt_input(*, user: User, goal: str) -> str:
    profile = user.build_prompt_profile()
    return (
        f"用户昵称: {profile['nickname']}\n"
        f"性别: {profile['gender']}\n"
        f"职业: {profile['occupation']}\n"
        f"签名: {profile['bio']}\n"
        f"时区: {profile['timezone']}\n"
        f"目标: {goal}\n"
        "请生成用于后续任务拆解的初始分析。"
    )
