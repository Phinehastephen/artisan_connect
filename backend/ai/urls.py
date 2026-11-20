from django.urls import path

from .views import SmartSearchView

urlpatterns = [
    path("search", SmartSearchView.as_view(), name="smart-search"),
]
# /api/v1/ai/search?q=<text>&location_type=current&latitude=<lat>&longitude=<lon>
# /api/v1/ai/search?q=<text>&location_type=saved&location_id=<id>
# /api/v1/ai/search