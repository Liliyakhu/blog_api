from rest_framework.routers import DefaultRouter
from django.urls import path, include

from blog.views import ProfileViewSet


router = DefaultRouter()
router.register("profiles", ProfileViewSet, basename="profile")

urlpatterns = [
    path("", include(router.urls)),
]

app_name = "blog"
