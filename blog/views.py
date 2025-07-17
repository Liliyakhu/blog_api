from rest_framework import viewsets, permissions, filters, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.decorators import action
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils import timezone

from blog.models import Profile, Follow, Post
from blog.serializers import (
    ProfileSerializer,
    FollowSerializer,
    UserPublicSerializer,
    PostSerializer,
)


User = get_user_model()


class ProfileViewSet(viewsets.ModelViewSet):
    queryset = Profile.objects.select_related("user").all()
    serializer_class = ProfileSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [filters.SearchFilter]
    search_fields = ["user__email", "bio", "location"]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def perform_update(self, serializer):
        if self.request.user != serializer.instance.user:
            raise PermissionDenied("You can only update your own profile.")
        serializer.save()

    def get_queryset(self):
        if self.request.user.is_authenticated:
            return Profile.objects.all()
        return Profile.objects.none()


class FollowViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def list(self, request):
        queryset = Follow.objects.filter(follower=request.user)
        serializer = FollowSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["post"], url_path="follow")
    def follow_user(self, request):
        user_id = request.data.get("user_id")
        try:
            target = User.objects.get(id=user_id)
            if target == request.user:
                return Response({"detail": "You cannot follow yourself."}, status=400)
            Follow.objects.get_or_create(follower=request.user, following=target)
            return Response({"detail": f"You are now following {target.email}."})
        except User.DoesNotExist:
            return Response({"detail": "User not found."}, status=404)

    @action(detail=False, methods=["post"], url_path="unfollow")
    def unfollow_user(self, request):
        user_id = request.data.get("user_id")
        try:
            target = User.objects.get(id=user_id)
            deleted, _ = Follow.objects.filter(
                follower=request.user, following=target
            ).delete()
            if deleted:
                return Response({"detail": f"You unfollowed {target.email}."})
            return Response({"detail": "You are not following this user."}, status=400)
        except User.DoesNotExist:
            return Response({"detail": "User not found."}, status=404)

    @action(detail=False, methods=["get"], url_path="followers")
    def list_followers(self, request):
        followers = request.user.followers.select_related("follower")
        data = [UserPublicSerializer(f.follower).data for f in followers]
        return Response(data)

    @action(detail=False, methods=["get"], url_path="following")
    def list_following(self, request):
        following = request.user.following.select_related("following")
        data = [UserPublicSerializer(f.following).data for f in following]
        return Response(data)


class PostViewSet(viewsets.ModelViewSet):
    queryset = Post.objects.filter(is_published=True).order_by("-created_at")
    serializer_class = PostSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [filters.SearchFilter]
    search_fields = ["content"]  # supports simple keyword/hashtag search

    def perform_create(self, serializer):
        scheduled_time = serializer.validated_data.get("scheduled_time")
        if scheduled_time and scheduled_time > timezone.now():
            serializer.save(author=self.request.user, is_published=False)
            # Optional: trigger Celery task
        else:
            serializer.save(author=self.request.user, is_published=True)

    def get_queryset(self):
        if self.request.user.is_authenticated:
            following_ids = self.request.user.following.values_list(
                "following_id", flat=True
            )
            return Post.objects.filter(
                Q(author=self.request.user) | Q(author__in=following_ids),
                is_published=True,
            ).order_by("-created_at")
        return Post.objects.filter(is_published=True).order_by("-created_at")

    @action(detail=False, methods=["get"], url_path="by-hashtag/(?P<tag>\w+)")
    def by_hashtag(self, request, tag=None):
        posts = Post.objects.filter(content__icontains=f"#{tag}", is_published=True)
        serializer = self.get_serializer(posts, many=True)
        return Response(serializer.data)
