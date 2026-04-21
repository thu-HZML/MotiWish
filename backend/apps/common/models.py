from django.db import models


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        abstract = True


class UserOwnedModel(TimeStampedModel):
    owner = models.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
        related_name="%(class)ss",
        verbose_name="所属用户",
    )

    class Meta:
        abstract = True


class LegalDocument(TimeStampedModel):
    class DocumentType(models.TextChoices):
        TERMS = "terms", "用户服务协议"
        PRIVACY = "privacy", "隐私政策"
        DATA_COLLECTION = "data_collection", "个人信息收集清单"
        CHILDREN = "children", "未成年人说明"

    document_type = models.CharField(max_length=32, choices=DocumentType.choices, verbose_name="文档类型")
    title = models.CharField(max_length=100, verbose_name="标题")
    version = models.CharField(max_length=32, verbose_name="版本号")
    summary = models.CharField(max_length=255, blank=True, verbose_name="摘要")
    content = models.TextField(verbose_name="正文")
    effective_at = models.DateTimeField(verbose_name="生效时间")
    is_active = models.BooleanField(default=True, verbose_name="是否启用")
    prompt_notes = models.JSONField(default=dict, blank=True, verbose_name="提示词补充信息")

    class Meta:
        verbose_name = "法律与政策文档"
        verbose_name_plural = "法律与政策文档"
        ordering = ("document_type", "-effective_at", "-id")

    def __str__(self):
        return f"{self.get_document_type_display()}-{self.version}"
