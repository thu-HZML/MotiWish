from django.contrib.auth.models import AbstractUser
from django.db import models

from apps.common.models import TimeStampedModel


class User(AbstractUser, TimeStampedModel):
    email = models.EmailField(unique=True, verbose_name="邮箱")
    nickname = models.CharField(max_length=50, blank=True, verbose_name="昵称")
    timezone = models.CharField(max_length=50, default="Asia/Shanghai", verbose_name="时区")
    onboarding_completed = models.BooleanField(default=False, verbose_name="是否完成引导")

    REQUIRED_FIELDS = ["email"]

    class Meta:
        verbose_name = "用户"
        verbose_name_plural = "用户"

    def __str__(self):
        return self.nickname or self.username
