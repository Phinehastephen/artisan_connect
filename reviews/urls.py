from django.urls import path

from .views import (
    ReviewListCreateView,
    ReviewDetailView,
)


urlpatterns = [
    path(
        "review/create",
        ReviewListCreateView.as_view(),
        name="review-list-create",
    ),

    path(
        "edit/<int:pk>",
        ReviewDetailView.as_view(),
        name="review-detail",
    ),
]

# api/v1/reviews/review/create
# api/v1/reviews/edit/<int:pk>