import django_filters

from apps.listings.models import Listing


class ListingFilter(django_filters.FilterSet):
    city = django_filters.CharFilter(field_name="city", lookup_expr="iexact")
    state = django_filters.CharFilter(field_name="state", lookup_expr="iexact")
    min_bedrooms = django_filters.NumberFilter(field_name="bedrooms", lookup_expr="gte")
    max_price = django_filters.NumberFilter(field_name="price", lookup_expr="lte")
    listing_type = django_filters.CharFilter(field_name="listing_type", lookup_expr="iexact")

    class Meta:
        model = Listing
        fields = ["city", "state", "min_bedrooms", "max_price", "listing_type"]
