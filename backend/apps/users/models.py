from django.contrib.auth.models import AbstractUser
from django.db import models

from apps.common.models import TimeStampedModel


class User(AbstractUser, TimeStampedModel):
    class Gender(models.TextChoices):
        MALE = "male", "男"
        FEMALE = "female", "女"
        UNKNOWN = "unknown", "未知"

    class Occupation(models.TextChoices):
        EMPLOYEE = "employee", "上班族"
        STUDENT = "student", "学生"
        TEACHER = "teacher", "教师"
        OTHER = "other", "其他"

    email = models.EmailField(unique=True, verbose_name="邮箱")
    nickname = models.CharField(max_length=50, blank=True, verbose_name="昵称")
    avatar = models.ImageField(upload_to="avatars/", blank=True, null=True, verbose_name="头像")
    gender = models.CharField(
        max_length=16,
        choices=Gender.choices,
        default=Gender.UNKNOWN,
        verbose_name="性别",
    )
    birth_date = models.DateField(blank=True, null=True, verbose_name="生日")
    occupation = models.CharField(
        max_length=16,
        choices=Occupation.choices,
        default=Occupation.OTHER,
        verbose_name="职业",
    )
    bio = models.CharField(max_length=100, blank=True, verbose_name="个人签名")
    timezone = models.CharField(max_length=50, default="Asia/Shanghai", verbose_name="时区")
    onboarding_completed = models.BooleanField(default=False, verbose_name="是否完成引导")

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

    def build_prompt_profile(self):
        return {
            "nickname": self.display_nickname,
            "gender": self.gender,
            "birth_date": self.birth_date.isoformat() if self.birth_date else None,
            "occupation": self.occupation,
            "bio": self.bio,
            "timezone": self.timezone,
            "avatar_present": bool(self.avatar),
            "default_avatar_group": self.default_avatar_group,
        }
