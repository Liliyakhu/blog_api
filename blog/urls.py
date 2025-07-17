from rest_framework.routers import DefaultRouter
from django.urls import path, include

from blog.views import ProfileViewSet, FollowViewSet, PostViewSet


router = DefaultRouter()
router.register("profiles", ProfileViewSet, basename="profile")
router.register("follows", FollowViewSet, basename="follows")
router.register("posts", PostViewSet, basename="posts")

urlpatterns = [
    path("", include(router.urls)),
    path("", include(router.urls)),
    path("", include(router.urls)),
]

app_name = "blog"
