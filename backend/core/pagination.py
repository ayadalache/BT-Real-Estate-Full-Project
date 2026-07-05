from collections import OrderedDict

from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class StandardResultsPagination(PageNumberPagination):
    """
    Page-number pagination wrapped in the standard response envelope,
    with a max page size cap to prevent clients from requesting huge,
    expensive result sets (a lightweight DoS protection).
    """

    page_size = 12
    page_size_query_param = "page_size"
    max_page_size = 50

    def get_paginated_response(self, data):
        return Response(
            OrderedDict(
                [
                    ("success", True),
                    ("message", "Success"),
                    (
                        "data",
                        OrderedDict(
                            [
                                ("count", self.page.paginator.count),
                                ("total_pages", self.page.paginator.num_pages),
                                ("current_page", self.page.number),
                                ("next", self.get_next_link()),
                                ("previous", self.get_previous_link()),
                                ("results", data),
                            ]
                        ),
                    ),
                    ("errors", None),
                ]
            )
        )
