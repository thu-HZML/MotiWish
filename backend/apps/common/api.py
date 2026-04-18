from rest_framework import status
from rest_framework.response import Response


def api_response(*, data=None, message="success", code="OK", status_code=status.HTTP_200_OK):
    return Response(
        {
            "success": 200 <= status_code < 300,
            "code": code,
            "message": message,
            "data": data,
        },
        status=status_code,
    )


class ApiResponseMixin:
    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        if getattr(response, "data", None) is None:
            return response
        if isinstance(response.data, dict) and {"success", "code", "message", "data"}.issubset(response.data.keys()):
            return response
        if 200 <= response.status_code < 300:
            response.data = {
                "success": True,
                "code": "OK",
                "message": "success",
                "data": response.data,
            }
        return response
