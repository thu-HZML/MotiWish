from rest_framework import serializers
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from drf_spectacular.utils import OpenApiExample, OpenApiParameter, extend_schema, inline_serializer

from apps.common.api import api_response
from apps.common.models import LegalDocument
from apps.common.openapi import api_envelope_serializer
from apps.common.serializers import LegalDocumentSerializer


class HealthCheckView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Common"],
        summary="健康检查",
        responses=api_envelope_serializer(
            "HealthCheckResponse",
            data_field=serializers.DictField(),
        ),
        examples=[
            OpenApiExample(
                "健康检查响应",
                value={
                    "success": True,
                    "code": "OK",
                    "message": "服务运行正常",
                    "data": {"service": "motiwish-backend", "status": "ok"},
                },
                response_only=True,
            )
        ],
    )
    def get(self, request):
        return api_response(
            data={"service": "motiwish-backend", "status": "ok"},
            message="服务运行正常",
        )


class ActiveLegalDocumentListView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Common"],
        summary="获取法律与隐私文档",
        parameters=[
            OpenApiParameter(
                name="document_type",
                type=str,
                location=OpenApiParameter.QUERY,
                required=False,
                description="可选值：terms / privacy / data_collection / children",
            )
        ],
        responses=api_envelope_serializer(
            "LegalDocumentsResponse",
            data_field=inline_serializer(
                name="LegalDocumentsPayload",
                fields={
                    "documents": LegalDocumentSerializer(many=True),
                    "description": serializers.ListField(child=serializers.CharField()),
                },
            ),
        ),
        examples=[
            OpenApiExample(
                "法律文档响应",
                value={
                    "success": True,
                    "code": "OK",
                    "message": "获取法律与隐私文档成功",
                    "data": {
                        "documents": [
                            {
                                "id": 1,
                                "document_type": "privacy",
                                "title": "MotiWish 隐私政策",
                                "version": "2026.04",
                                "summary": "说明个人信息处理与用户权利。",
                                "content": "我们会在提供任务、钱包与画像分析服务时处理必要的个人信息。",
                                "effective_at": "2026-04-21T00:00:00+08:00",
                                "prompt_notes": {
                                    "used_in_ai_prompt": ["gender", "occupation", "bio"],
                                    "required_fields": ["nickname", "gender"],
                                },
                                "updated_at": "2026-04-21T00:00:00+08:00",
                            }
                        ],
                        "description": [
                            "用户服务协议：说明产品使用规则、账号责任与服务边界。",
                            "隐私政策：说明个人信息处理目的、方式、保存期限与用户权利。",
                            "个人信息收集清单：说明收集字段、使用场景、是否必要。",
                            "未成年人说明：说明监护、使用限制与个人信息保护补充要求。",
                        ],
                    },
                },
                response_only=True,
            )
        ],
    )
    def get(self, request):
        queryset = LegalDocument.objects.filter(is_active=True)
        document_type = request.query_params.get("document_type")
        if document_type:
            queryset = queryset.filter(document_type=document_type)
        queryset = queryset.order_by("document_type", "-effective_at")
        serializer = LegalDocumentSerializer(queryset, many=True)
        return api_response(
            data={
                "documents": serializer.data,
                "description": [
                    "用户服务协议：说明产品使用规则、账号责任与服务边界。",
                    "隐私政策：说明个人信息处理目的、方式、保存期限与用户权利。",
                    "个人信息收集清单：说明收集字段、使用场景、是否必要。",
                    "未成年人说明：说明监护、使用限制与个人信息保护补充要求。",
                ],
            },
            message="获取法律与隐私文档成功",
        )
