from django.urls import path, include
from rest_framework_nested import routers

from blog.views import PostViewSet, ProfileViewSet, CommentViewSet


router = routers.DefaultRouter()
router.register("posts", PostViewSet, basename="posts")
router.register("profiles", ProfileViewSet, basename="profiles")

comments_router = routers.NestedDefaultRouter(router, "posts", lookup="post")
comments_router.register("comments", CommentViewSet, basename="post-comments")

# urlpatterns = [path("", include(router.urls))]
urlpatterns = router.urls + comments_router.urls


app_name = "blog"
