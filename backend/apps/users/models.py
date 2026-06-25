from datetime import timedelta

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone

from apps.common.models import TimeStampedModel


class User(AbstractUser, TimeStampedModel):
    MULTI_SELECT_UNSPECIFIED = "unspecified"

    class Gender(models.TextChoices):
        MALE = "male", "男"
        FEMALE = "female", "女"
        UNKNOWN = "unknown", "未知"

    class Occupation(models.TextChoices):
        STUDENT = "student", "学生"
        EMPLOYEE = "employee", "上班族"
        TEACHER = "teacher", "教师"
        FREELANCER = "freelancer", "自由职业"
        CREATOR = "creator", "创作者"
        JOB_SEEKER = "job_seeker", "求职中"
        HOMEMAKER = "homemaker", "居家/照护者"
        RETIRED = "retired", "退休"
        OTHER = "other", "其他"
        UNDISCLOSED = "undisclosed", "暂不填写"

    class EducationStage(models.TextChoices):
        MIDDLE_SCHOOL = "middle_school", "初中"
        HIGH_SCHOOL = "high_school", "高中"
        COLLEGE = "college", "本科/大专"
        GRADUATE = "graduate", "研究生"
        WORKING = "working", "已工作"
        OTHER = "other", "其他"
        UNDISCLOSED = "undisclosed", "暂不填写"

    class LanguagePreference(models.TextChoices):
        ZH_HANS = "zh-hans", "简体中文"
        EN = "en", "English"
        BILINGUAL = "bilingual", "中英双语"
        OTHER = "other", "其他"
        UNDISCLOSED = "undisclosed", "暂不填写"

    class GoalCategory(models.TextChoices):
        LEARNING = "learning", "学习提升"
        HEALTH = "health", "健康管理"
        HABIT = "habit", "习惯养成"
        PRODUCTIVITY = "productivity", "效率提升"
        CAREER = "career", "职业发展"
        EMOTION = "emotion", "情绪管理"
        LIFE = "life", "生活整理"
        FINANCE = "finance", "财务规划"
        RELATIONSHIP = "relationship", "人际关系"
        CREATIVITY = "creativity", "创作表达"
        UNSPECIFIED = "unspecified", "暂不填写"

    class FocusArea(models.TextChoices):
        EXAM = "exam", "考试/升学"
        LANGUAGE = "language", "语言学习"
        FITNESS = "fitness", "运动健身"
        SLEEP = "sleep", "睡眠作息"
        WORK = "work", "工作项目"
        READING = "reading", "阅读输入"
        WRITING = "writing", "写作输出"
        SOCIAL = "social", "社交经营"
        HOUSEHOLD = "household", "生活事务"
        MENTAL = "mental", "心理状态"
        UNSPECIFIED = "unspecified", "暂不填写"

    email = models.EmailField(unique=True, verbose_name="邮箱")
    nickname = models.CharField(max_length=50, blank=True, verbose_name="昵称")
    avatar = models.ImageField(upload_to="avatars/", blank=True, null=True, verbose_name="头像")
    gender = models.CharField(max_length=16, choices=Gender.choices, default=Gender.UNKNOWN, verbose_name="性别")
    birth_date = models.DateField(blank=True, null=True, verbose_name="生日")
    occupation = models.CharField(
        max_length=24,
        choices=Occupation.choices,
        default=Occupation.UNDISCLOSED,
        verbose_name="职业",
    )
    education_stage = models.CharField(
        max_length=24,
        choices=EducationStage.choices,
        default=EducationStage.UNDISCLOSED,
        verbose_name="教育阶段",
    )
    language_preference = models.CharField(
        max_length=24,
        choices=LanguagePreference.choices,
        default=LanguagePreference.ZH_HANS,
        verbose_name="语言偏好",
    )
    region = models.CharField(max_length=80, blank=True, verbose_name="所在地区")
    bio = models.CharField(max_length=100, blank=True, verbose_name="个人签名")
    timezone = models.CharField(max_length=50, default="Asia/Shanghai", verbose_name="时区")
    long_term_goals = models.JSONField(default=list, blank=True, verbose_name="长期目标类型")
    focus_areas = models.JSONField(default=list, blank=True, verbose_name="当前主要关注领域")
    onboarding_completed = models.BooleanField(default=False, verbose_name="是否完成引导")
    basic_profile_completed = models.BooleanField(default=False, verbose_name="基础资料是否完善")
    basic_profile_completion_score = models.PositiveSmallIntegerField(default=0, verbose_name="基础资料完善度")
    basic_profile_missing_fields = models.JSONField(default=list, blank=True, verbose_name="基础资料待补充字段")
    basic_profile_last_prompted_at = models.DateTimeField(null=True, blank=True, verbose_name="基础资料上次提醒时间")
    level = models.PositiveIntegerField(default=1, verbose_name="用户等级")
    experience = models.PositiveIntegerField(default=0, verbose_name="当前等级经验")
    total_experience = models.PositiveIntegerField(default=0, verbose_name="累计经验")

    REQUIRED_FIELDS = ["email"]

    class Meta:
        verbose_name = "用户"
        verbose_name_plural = "用户"

    def __str__(self):
        return self.display_nickname

    @property
    def display_nickname(self):
        return self.nickname or f"用户{self.username}"

    @property
    def default_avatar_group(self):
        return {
            self.Gender.MALE: "male-default-1",
            self.Gender.FEMALE: "female-default-1",
            self.Gender.UNKNOWN: "unknown-default-1",
        }.get(self.gender, "unknown-default-1")

    @property
    def next_level_experience(self):
        return self.level * 100

    @property
    def normalized_long_term_goals(self):
        return self.long_term_goals or [self.MULTI_SELECT_UNSPECIFIED]

    @property
    def normalized_focus_areas(self):
        return self.focus_areas or [self.MULTI_SELECT_UNSPECIFIED]

    def get_basic_profile_missing_fields(self):
        missing = []
        if not self.nickname.strip():
            missing.append("nickname")
        if self.gender == self.Gender.UNKNOWN:
            missing.append("gender")
        if self.occupation == self.Occupation.UNDISCLOSED:
            missing.append("occupation")
        if self.education_stage == self.EducationStage.UNDISCLOSED:
            missing.append("education_stage")
        if self.language_preference == self.LanguagePreference.UNDISCLOSED:
            missing.append("language_preference")
        if self.normalized_long_term_goals == [self.MULTI_SELECT_UNSPECIFIED]:
            missing.append("long_term_goals")
        if self.normalized_focus_areas == [self.MULTI_SELECT_UNSPECIFIED]:
            missing.append("focus_areas")
        if not self.timezone:
            missing.append("timezone")
        return missing

    def refresh_basic_profile_status(self):
        required_fields = 8
        missing = self.get_basic_profile_missing_fields()
        completed_count = required_fields - len(missing)
        self.basic_profile_missing_fields = missing
        self.basic_profile_completion_score = int(completed_count / required_fields * 100)
        self.basic_profile_completed = not missing
        self.onboarding_completed = self.basic_profile_completed

    def save(self, *args, **kwargs):
        self.refresh_basic_profile_status()
        super().save(*args, **kwargs)

    def mark_basic_profile_prompted(self):
        self.basic_profile_last_prompted_at = timezone.now()
        self.save(update_fields=["basic_profile_last_prompted_at", "updated_at"])

    def build_prompt_profile(self):
        stable_profile = getattr(self, "stable_profile", None)
        dynamic_profile = getattr(self, "dynamic_profile", None)
        return {
            "nickname": self.display_nickname,
            "gender": self.gender,
            "birth_date": self.birth_date.isoformat() if self.birth_date else None,
            "occupation": self.occupation,
            "education_stage": self.education_stage,
            "language_preference": self.language_preference,
            "region": self.region or None,
            "bio": self.bio,
            "timezone": self.timezone,
            "long_term_goals": self.normalized_long_term_goals,
            "focus_areas": self.normalized_focus_areas,
            "avatar_present": bool(self.avatar),
            "default_avatar_group": self.default_avatar_group,
            "basic_profile_completed": self.basic_profile_completed,
            "stable_profile_completed": stable_profile.is_completed if stable_profile else False,
            "dynamic_profile_available": dynamic_profile.has_meaningful_data if dynamic_profile else False,
        }


class EmailVerificationCode(TimeStampedModel):
    class Purpose(models.TextChoices):
        REGISTER = "register", "Register"
        PASSWORD_RESET = "password_reset", "Password reset"

    email = models.EmailField(db_index=True)
    purpose = models.CharField(max_length=32, choices=Purpose.choices)
    code_hash = models.CharField(max_length=128)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
    attempt_count = models.PositiveSmallIntegerField(default=0)
    sent_ip = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        verbose_name = "Email verification code"
        verbose_name_plural = "Email verification codes"
        indexes = [
            models.Index(fields=["email", "purpose", "created_at"]),
            models.Index(fields=["email", "purpose", "used_at"]),
        ]
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.email} {self.purpose} {self.created_at:%Y-%m-%d %H:%M:%S}"

    @property
    def is_used(self):
        return self.used_at is not None

    @property
    def is_expired(self):
        return timezone.now() >= self.expires_at


class StableProfile(TimeStampedModel):
    PROMPT_INTERVAL_DAYS = 3
    MULTI_SELECT_UNSPECIFIED = "unspecified"

    class SelfManagementChallenge(models.TextChoices):
        PROCRASTINATION = "procrastination", "拖延"
        DISTRACTION = "distraction", "注意力分散"
        PERFECTIONISM = "perfectionism", "完美主义"
        OVERPLANNING = "overplanning", "计划过载"
        CONSISTENCY = "consistency", "难以坚持"
        INTERRUPTION = "interruption", "频繁被打断"
        LOW_ENERGY = "low_energy", "精力不足"
        UNSPECIFIED = "unspecified", "暂不填写"

    class MotivationPreference(models.TextChoices):
        ACHIEVEMENT = "achievement", "成就驱动"
        COLLECTION = "collection", "收集驱动"
        SOCIAL = "social", "社交驱动"
        COMPETITION = "competition", "竞争驱动"
        NARRATIVE = "narrative", "成长叙事驱动"
        UNSPECIFIED = "unspecified", "暂不填写"

    class RewardPreference(models.TextChoices):
        INSTANT = "instant", "偏好即时奖励"
        BIG_LATER = "big_later", "偏好延迟大奖励"
        BALANCED = "balanced", "二者平衡"
        UNDISCLOSED = "undisclosed", "暂不填写"

    class ToleranceLevel(models.TextChoices):
        LOW = "low", "低"
        MEDIUM = "medium", "中"
        HIGH = "high", "高"
        UNDISCLOSED = "undisclosed", "暂不填写"

    class Chronotype(models.TextChoices):
        MORNING = "morning", "早型"
        NIGHT = "night", "晚型"
        FLEXIBLE = "flexible", "不固定"
        UNDISCLOSED = "undisclosed", "暂不填写"

    class EnergyPeakPeriod(models.TextChoices):
        MORNING = "morning", "上午"
        AFTERNOON = "afternoon", "下午"
        EVENING = "evening", "晚上"
        LATE_NIGHT = "late_night", "深夜"
        UNSPECIFIED = "unspecified", "暂不填写"

    class TaskGranularityPreference(models.TextChoices):
        SMALL = "small", "喜欢拆小任务"
        BALANCED = "balanced", "大小任务都可以"
        LARGE = "large", "偏好大块任务"
        UNDISCLOSED = "undisclosed", "暂不填写"

    class PlanningStylePreference(models.TextChoices):
        STRUCTURED = "structured", "严格计划"
        FLEXIBLE = "flexible", "弹性计划"
        MIXED = "mixed", "两者结合"
        UNDISCLOSED = "undisclosed", "暂不填写"

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="stable_profile", verbose_name="用户")
    self_management_challenges = models.JSONField(default=list, blank=True, verbose_name="自我管理难点")
    motivation_preferences = models.JSONField(default=list, blank=True, verbose_name="动机来源偏好")
    reward_preference = models.CharField(
        max_length=24,
        choices=RewardPreference.choices,
        default=RewardPreference.UNDISCLOSED,
        verbose_name="奖励偏好",
    )
    penalty_tolerance = models.CharField(
        max_length=24,
        choices=ToleranceLevel.choices,
        default=ToleranceLevel.UNDISCLOSED,
        verbose_name="惩罚接受度",
    )
    stress_sensitivity = models.CharField(
        max_length=24,
        choices=ToleranceLevel.choices,
        default=ToleranceLevel.UNDISCLOSED,
        verbose_name="压力敏感度",
    )
    self_discipline_score = models.PositiveSmallIntegerField(null=True, blank=True, verbose_name="自律自评分")
    chronotype = models.CharField(
        max_length=24,
        choices=Chronotype.choices,
        default=Chronotype.UNDISCLOSED,
        verbose_name="作息类型",
    )
    energy_peak_periods = models.JSONField(default=list, blank=True, verbose_name="精力高峰时段")
    task_granularity_preference = models.CharField(
        max_length=24,
        choices=TaskGranularityPreference.choices,
        default=TaskGranularityPreference.UNDISCLOSED,
        verbose_name="偏好任务粒度",
    )
    planning_style_preference = models.CharField(
        max_length=24,
        choices=PlanningStylePreference.choices,
        default=PlanningStylePreference.UNDISCLOSED,
        verbose_name="计划风格偏好",
    )
    is_completed = models.BooleanField(default=False, verbose_name="稳定画像是否完成")
    completion_score = models.PositiveSmallIntegerField(default=0, verbose_name="稳定画像完善度")
    missing_fields = models.JSONField(default=list, blank=True, verbose_name="稳定画像待补充字段")
    last_prompted_at = models.DateTimeField(null=True, blank=True, verbose_name="稳定画像上次提醒时间")
    questionnaire_completed_at = models.DateTimeField(null=True, blank=True, verbose_name="问卷完成时间")

    class Meta:
        verbose_name = "稳定画像"
        verbose_name_plural = "稳定画像"

    @property
    def normalized_self_management_challenges(self):
        return self.self_management_challenges or [self.MULTI_SELECT_UNSPECIFIED]

    @property
    def normalized_motivation_preferences(self):
        return self.motivation_preferences or [self.MULTI_SELECT_UNSPECIFIED]

    @property
    def normalized_energy_peak_periods(self):
        return self.energy_peak_periods or [self.MULTI_SELECT_UNSPECIFIED]

    def get_missing_fields(self):
        missing = []
        if self.normalized_self_management_challenges == [self.MULTI_SELECT_UNSPECIFIED]:
            missing.append("self_management_challenges")
        if self.normalized_motivation_preferences == [self.MULTI_SELECT_UNSPECIFIED]:
            missing.append("motivation_preferences")
        if self.reward_preference == self.RewardPreference.UNDISCLOSED:
            missing.append("reward_preference")
        if self.penalty_tolerance == self.ToleranceLevel.UNDISCLOSED:
            missing.append("penalty_tolerance")
        if self.stress_sensitivity == self.ToleranceLevel.UNDISCLOSED:
            missing.append("stress_sensitivity")
        if self.self_discipline_score is None:
            missing.append("self_discipline_score")
        if self.chronotype == self.Chronotype.UNDISCLOSED:
            missing.append("chronotype")
        if self.normalized_energy_peak_periods == [self.MULTI_SELECT_UNSPECIFIED]:
            missing.append("energy_peak_periods")
        if self.task_granularity_preference == self.TaskGranularityPreference.UNDISCLOSED:
            missing.append("task_granularity_preference")
        if self.planning_style_preference == self.PlanningStylePreference.UNDISCLOSED:
            missing.append("planning_style_preference")
        return missing

    def refresh_completion_status(self):
        total_fields = 10
        missing = self.get_missing_fields()
        self.missing_fields = missing
        self.completion_score = int((total_fields - len(missing)) / total_fields * 100)
        self.is_completed = not missing
        if self.is_completed and self.questionnaire_completed_at is None:
            self.questionnaire_completed_at = timezone.now()

    def save(self, *args, **kwargs):
        self.refresh_completion_status()
        super().save(*args, **kwargs)

    @property
    def should_prompt(self):
        if self.is_completed:
            return False
        if self.last_prompted_at is None:
            return True
        return timezone.now() >= self.last_prompted_at + timedelta(days=self.PROMPT_INTERVAL_DAYS)

    @property
    def next_prompt_at(self):
        if self.is_completed:
            return None
        if self.last_prompted_at is None:
            return timezone.now()
        return self.last_prompted_at + timedelta(days=self.PROMPT_INTERVAL_DAYS)

    def mark_prompted(self):
        self.last_prompted_at = timezone.now()
        self.save(update_fields=["last_prompted_at", "updated_at"])


class DynamicProfile(TimeStampedModel):
    PROMPT_INTERVAL_DAYS = 7
    MULTI_SELECT_UNSPECIFIED = "unspecified"

    class StageTag(models.TextChoices):
        EXAM = "exam", "备考期"
        CRUNCH = "crunch", "项目冲刺期"
        HOLIDAY = "holiday", "假期"
        JOB_SEARCH = "job_search", "求职期"
        TRANSITION = "transition", "转型期"
        RECOVERY = "recovery", "恢复调整期"
        UNSPECIFIED = "unspecified", "暂不填写"

    class ThreeLevelState(models.TextChoices):
        LOW = "low", "低/较差"
        MEDIUM = "medium", "一般"
        HIGH = "high", "高/较好"
        UNDISCLOSED = "undisclosed", "暂不填写"

    class AvailableTimeLevel(models.TextChoices):
        LIMITED = "limited", "很少"
        NORMAL = "normal", "一般"
        AMPLE = "ample", "充足"
        UNDISCLOSED = "undisclosed", "暂不填写"

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="dynamic_profile", verbose_name="用户")
    current_stage_tags = models.JSONField(default=list, blank=True, verbose_name="当前阶段标签")
    stress_level = models.PositiveSmallIntegerField(null=True, blank=True, verbose_name="最近压力水平")
    sleep_quality = models.CharField(
        max_length=24,
        choices=ThreeLevelState.choices,
        default=ThreeLevelState.UNDISCLOSED,
        verbose_name="最近睡眠情况",
    )
    mood_state = models.CharField(
        max_length=24,
        choices=ThreeLevelState.choices,
        default=ThreeLevelState.UNDISCLOSED,
        verbose_name="最近情绪状态",
    )
    available_time_level = models.CharField(
        max_length=24,
        choices=AvailableTimeLevel.choices,
        default=AvailableTimeLevel.UNDISCLOSED,
        verbose_name="最近可支配时间",
    )
    current_top_goal = models.CharField(max_length=120, blank=True, verbose_name="当前最重要目标")
    current_main_blocker = models.CharField(max_length=255, blank=True, verbose_name="当前最大阻碍")
    weekly_time_budget_hours = models.PositiveSmallIntegerField(null=True, blank=True, verbose_name="本周可投入时长")
    last_prompted_at = models.DateTimeField(null=True, blank=True, verbose_name="动态状态上次提醒时间")

    class Meta:
        verbose_name = "动态状态画像"
        verbose_name_plural = "动态状态画像"

    @property
    def normalized_current_stage_tags(self):
        return self.current_stage_tags or [self.MULTI_SELECT_UNSPECIFIED]

    @property
    def has_meaningful_data(self):
        return any(
            [
                self.normalized_current_stage_tags != [self.MULTI_SELECT_UNSPECIFIED],
                self.stress_level is not None,
                self.sleep_quality != self.ThreeLevelState.UNDISCLOSED,
                self.mood_state != self.ThreeLevelState.UNDISCLOSED,
                self.available_time_level != self.AvailableTimeLevel.UNDISCLOSED,
                bool(self.current_top_goal.strip()),
                bool(self.current_main_blocker.strip()),
                self.weekly_time_budget_hours is not None,
            ]
        )

    @property
    def should_prompt(self):
        if self.last_prompted_at is None:
            return True
        return timezone.now() >= self.last_prompted_at + timedelta(days=self.PROMPT_INTERVAL_DAYS)

    @property
    def next_prompt_at(self):
        if self.last_prompted_at is None:
            return timezone.now()
        return self.last_prompted_at + timedelta(days=self.PROMPT_INTERVAL_DAYS)

    def mark_prompted(self):
        self.last_prompted_at = timezone.now()
        self.save(update_fields=["last_prompted_at", "updated_at"])
