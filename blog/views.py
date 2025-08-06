from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import NotFound, PermissionDenied
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.db.models import Q
from django.contrib.auth import get_user_model

User = get_user_model()

from blog.models import Post, Comment, Profile, Follow, Like
from blog.serializers import (
    PostSerializer,
    PostDetailSerializer,
    CommentSerializer,
    ProfileSerializer, FollowerSerializer, FollowingSerializer
)


class ProfileViewSet(viewsets.ModelViewSet):
    serializer_class = ProfileSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        queryset = Profile.objects.select_related("user").prefetch_related(
            "user__followers",
            "user__following",
            "user__posts"
        )

        # Search functionality
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(user__email__icontains=search) |
                Q(user__first_name__icontains=search) |
                Q(user__last_name__icontains=search) |
                Q(bio__icontains=search)
            )

        return queryset

    def get_object(self):
        """Override to allow accessing profile by user ID or profile ID"""
        lookup_value = self.kwargs.get("pk")
        try:
            if lookup_value =="me" and self.request.user.is_authenticated:
                return self.request.user.profile
            return Profile.objects.select_related("user").get(
                Q(id=lookup_value) | Q(user__id=lookup_value)
            )
        except (Profile.DoesNotExist, ValueError):
            raise NotFound("Profile not found")

    @action(detail=True, methods=["get"], permission_classes=[permissions.IsAuthenticated])
    def followers(self, request, pk=None):
        """List all users who are following this profile's user."""
        profile = self.get_object()
        followers = Follow.objects.filter(following=profile.user)
        serializer = FollowerSerializer(followers, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["get"], permission_classes=[permissions.IsAuthenticated])
    def following(self, request, pk=None):
        """List all users that this profile's user is following."""
        profile = self.get_object()
        following = Follow.objects.filter(follower=profile.user)
        serializer = FollowingSerializer(following, many=True)
        return Response(serializer.data)

    def update(self, request, *args, **kwargs):
        profile = self.get_object()
        if profile.user != request.user:
            raise PermissionDenied("You can only update your own profile")
        return super().update(request, *args, **kwargs)

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated])
    def follow(self, request, pk=None):
        """Follow/unfollow a user"""
        profile = self.get_object()
        if profile.user == request.user:
            return Response(
                {"error": "You cannot follow yourself"},
                status=status.HTTP_400_BAD_REQUEST
            )

        follow_obj, created = Follow.objects.get_or_create(
            follower=request.user,
            following=profile.user
        )

        if not created:
            follow_obj.delete()
            return Response({"message": "Unfollowed successfully"})

        return Response({"message": "Followed successfully"})


class PostViewSet(viewsets.ModelViewSet):
    serializer_class = PostSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        queryset = (
            Post.objects.select_related("author", "author__profile")
            .prefetch_related("likes", "comments__author", "comments__author__profile")
        )

        # Filter by author
        author_id = self.request.query_params.get("author")
        if author_id:
            queryset = queryset.filter(author_id=author_id)

        # Filter by tags
        tag = self.request.query_params.get("tag")
        if tag:
            queryset = queryset.filter(tags__icontains=tag)

        return queryset.filter(is_published=True)

    def get_serializer_class(self):
        if self.action == "retrieve":
            return PostDetailSerializer
        return PostSerializer

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def update(self, request, *args, **kwargs):
        post = self.get_object()
        if post.author != request.user:
            raise PermissionDenied("You can only update your own posts")
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        post = self.get_object()
        if post.author != request.user:
            raise PermissionDenied("You can only delete your own posts")
        return super().destroy(request, *args, **kwargs)

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated])
    def like(self, request, pk=None):
        """Like/unlike a post"""
        post = self.get_object()
        like_obj, created = Like.objects.get_or_create(
            post=post,
            user=request.user
        )

        if not created:
            like_obj.delete()
            return Response({"message": "Post unliked"})

        return Response({"message": "Post liked"})

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def feed(self, request):
        """Get posts from users that the current user follows"""
        following_users = request.user.following.values_list('following_id', flat=True)
        posts = (Post.objects
                 .filter(Q(author__in=following_users) | Q(author=request.user))
                 .select_related("author", "author__profile")
                 .prefetch_related("likes", "comments")
                 .filter(is_published=True))

        page = self.paginate_queryset(posts)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(posts, many=True)
        return Response(serializer.data)


class CommentViewSet(viewsets.ModelViewSet):
    serializer_class = CommentSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        post_pk = self.kwargs.get("post_pk")
        post = get_object_or_404(Post, pk=post_pk)
        return Comment.objects.filter(post=post).select_related("author")

    def perform_create(self, serializer):
        post_pk = self.kwargs.get("post_pk")
        post = get_object_or_404(Post, pk=post_pk)
        serializer.save(author=self.request.user, post=post)

    def update(self, request, *args, **kwargs):
        comment = self.get_object()
        if comment.author != request.user:
            raise PermissionDenied("You can only update your own comments")
        return super().update(request, *args, **kwargs)
