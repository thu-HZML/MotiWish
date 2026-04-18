from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is None and isinstance(exc, ValueError):
        return Response(
            {
                "success": False,
                "code": "VALIDATION_ERROR",
                "message": str(exc),
                "data": None,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )
    if response is None:
        return Response(
            {
                "success": False,
                "code": "INTERNAL_ERROR",
                "message": "服务器内部错误",
                "data": None,
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    detail = response.data
    message = detail.get("detail", detail) if isinstance(detail, dict) else detail
    response.data = {
        "success": False,
        "code": "REQUEST_ERROR",
        "message": message,
        "data": detail,
    }
    return response
