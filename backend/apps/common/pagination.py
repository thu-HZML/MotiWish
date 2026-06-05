from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class ApiEnvelopePageNumberPagination(PageNumberPagination):
    def get_paginated_response(self, data):
        return Response(
            {
                "success": True,
                "code": "OK",
                "message": "success",
                "data": {
                    "count": self.page.paginator.count,
                    "next": self.get_next_link(),
                    "previous": self.get_previous_link(),
                    "results": data,
                },
            }
        )

    def get_paginated_response_schema(self, schema):
        return {
            "type": "object",
            "required": ["success", "code", "message", "data"],
            "properties": {
                "success": {"type": "boolean"},
                "code": {"type": "string"},
                "message": {"type": "string"},
                "data": {
                    "type": "object",
                    "required": ["count", "next", "previous", "results"],
                    "properties": {
                        "count": {"type": "integer", "example": 123},
                        "next": {
                            "type": "string",
                            "nullable": True,
                            "format": "uri",
                            "example": "http://api.example.org/tasks/?page=2",
                        },
                        "previous": {
                            "type": "string",
                            "nullable": True,
                            "format": "uri",
                            "example": None,
                        },
                        "results": schema,
                    },
                },
            },
        }
