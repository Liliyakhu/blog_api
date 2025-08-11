from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import NotFound, PermissionDenied
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.db.models import Q, Count, Prefetch
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from rest_framework.exceptions import ValidationError as DRFValidationError
from drf_spectacular.utils import extend_schema
from drf_spectacular.utils import OpenApiParameter
from blog.models import Post, Comment, Profile, Follow, Like
from blog.serializers import (
    PostSerializer,
    PostDetailSerializer,
    CommentSerializer,
    ProfileSerializer,
    FollowerSerializer,
    FollowingSerializer,
)


User = get_user_model()


class ProfileViewSet(viewsets.ModelViewSet):
    serializer_class = ProfileSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        queryset = Profile.objects.select_related("user").prefetch_related(
            "user__followers", "user__following", "user__posts"
        )

        # Search functionality
        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                Q(user__email__icontains=search)
                | Q(user__first_name__icontains=search)
                | Q(user__last_name__icontains=search)
                | Q(bio__icontains=search)
            )

        return queryset

    def get_object(self):
        """Override to allow accessing profile by user ID or profile ID"""
        lookup_value = self.kwargs.get("pk")
        try:
            if lookup_value == "me" and self.request.user.is_authenticated:
                return self.request.user.profile
            return Profile.objects.select_related("user").get(
                Q(id=lookup_value) | Q(user__id=lookup_value)
            )
        except (Profile.DoesNotExist, ValueError):
            raise NotFound("Profile not found")

    @action(
        detail=True, methods=["get"], permission_classes=[permissions.IsAuthenticated]
    )
    def followers(self, request, pk=None):
        """List all users who are following this profile's user."""
        profile = self.get_object()
        followers = Follow.objects.filter(following=profile.user)
        serializer = FollowerSerializer(followers, many=True)
        return Response(serializer.data)

    @action(
        detail=True, methods=["get"], permission_classes=[permissions.IsAuthenticated]
    )
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

    @action(
        detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated]
    )
    def follow(self, request, pk=None):
        """Follow/unfollow a user"""
        profile = self.get_object()
        if profile.user == request.user:
            return Response(
                {"error": "You cannot follow yourself"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        follow_obj, created = Follow.objects.get_or_create(
            follower=request.user, following=profile.user
        )

        if not created:
            follow_obj.delete()
            return Response({"message": "Unfollowed successfully"})

        return Response({"message": "Followed successfully"})

    @extend_schema(
        parameters=[
            OpenApiParameter(
                "search",
                type={"type": "string"},
                description="Wide search by email or first name or last name or bio (ex. ?bio=programmer)",
            )
        ]
    )
    def list(self, request, *args, **kwargs):
        """Get list of buses."""
        return super().list(request, *args, **kwargs)


class PostViewSet(viewsets.ModelViewSet):
    serializer_class = PostSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    @staticmethod
    def _params_to_ints(query_string):
        """Converts a string to int"""
        return int(query_string)

    def get_queryset(self):
        queryset = (
            Post.objects.select_related("author", "author__profile")
            .prefetch_related(
                Prefetch("likes", queryset=Like.objects.select_related("user")),
                Prefetch("comments", queryset=Comment.objects.select_related("author")),
            )
            .annotate(
                likes_count=Count("likes", distinct=True),
                comments_count=Count("comments", distinct=True),
            )
        )

        # Filter by author
        author_id = self.request.query_params.get("author")
        if author_id:
            author_id = self._params_to_ints(author_id)
            queryset = queryset.filter(author__id=author_id)

        # Filter by tags
        tag = self.request.query_params.get("tag")
        if tag:
            queryset = queryset.filter(tags__icontains=tag)

        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search)
                | Q(content__icontains=search)
                | Q(tags__icontains=search)
            )

        return queryset.filter(is_published=True)

    def get_serializer_class(self):
        if self.action == "retrieve":
            return PostDetailSerializer
        return PostSerializer

    def perform_create(self, serializer):
        try:
            serializer.save(author=self.request.user)
        except IntegrityError as e:
            raise DRFValidationError("Error creating post. Please try again.")

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

    @action(
        detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated]
    )
    def like(self, request, pk=None):
        """Like/unlike a post"""
        post = self.get_object()
        like_obj, created = Like.objects.get_or_create(post=post, user=request.user)

        if not created:
            like_obj.delete()
            return Response(
                {
                    "message": "Post unliked",
                    "is_liked": False,
                    "likes_count": post.likes.count(),
                }
            )

        return Response(
            {
                "message": "Post liked",
                "is_liked": True,
                "likes_count": post.likes.count(),
            }
        )

    @action(
        detail=False, methods=["get"], permission_classes=[permissions.IsAuthenticated]
    )
    def feed(self, request):
        """Get posts from users that the current user follows"""
        following_users = request.user.following.values_list("following_id", flat=True)
        posts = (
            Post.objects.filter(Q(author__in=following_users) | Q(author=request.user))
            .select_related("author", "author__profile")
            .prefetch_related("likes", "comments")
            .annotate(
                likes_count=Count("likes", distinct=True),
                comments_count=Count("comments", distinct=True),
            )
            .filter(is_published=True)
        ).order_by("-created_at")

        page = self.paginate_queryset(posts)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(posts, many=True)
        return Response(serializer.data)

    @action(
        detail=False, methods=["get"], permission_classes=[permissions.IsAuthenticated]
    )
    def liked(self, request):
        """Get all posts liked by the current user"""
        liked_post_ids = Like.objects.filter(user=request.user).values_list(
            "post_id", flat=True
        )
        posts = (
            Post.objects.filter(id__in=liked_post_ids, is_published=True)
            .select_related("author", "author__profile")
            .prefetch_related("likes", "comments")
            .annotate(
                likes_count=Count("likes", distinct=True),
                comments_count=Count("comments", distinct=True),
            )
            .order_by("-created_at")
        )

        page = self.paginate_queryset(posts)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(posts, many=True)
        return Response(serializer.data)

    @extend_schema(
        parameters=[
            OpenApiParameter(
                "author",
                type={"type": "number"},
                description="Filter by author id (ex. ?author=1)",
            ),
            OpenApiParameter(
                "tag",
                type={"type": "string"},
                description="Filter by tag (ex. ?tag=me,you)",
            ),
            OpenApiParameter(
                "search",
                type={"type": "string"},
                description="Wide search by title or content or tag (ex. ?title=weather)",
            ),
        ]
    )
    def list(self, request, *args, **kwargs):
        """Get list of posts."""
        return super().list(request, *args, **kwargs)


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

        # Validate parent comment belongs to same post
        parent_id = self.request.data.get("parent")
        if parent_id:
            parent = get_object_or_404(Comment, id=parent_id, post=post)
            serializer.save(author=self.request.user, post=post, parent=parent)
        else:
            serializer.save(author=self.request.user, post=post)

    def update(self, request, *args, **kwargs):
        comment = self.get_object()
        if comment.author != request.user:
            raise PermissionDenied("You can only update your own comments")
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        comment = self.get_object()
        if comment.author != request.user:
            raise PermissionDenied("You can only delete your own comments")
        return super().destroy(request, *args, **kwargs)

    @action(
        detail=False, methods=["get"], permission_classes=[permissions.IsAuthenticated]
    )
    def my_comments(self, request):
        """Get all comments by the current user"""
        post_pk = self.kwargs.get("post_pk")
        post = get_object_or_404(Post, pk=post_pk)
        comments = (
            Comment.objects.filter(post=post, author=request.user)
            .select_related("author", "author__profile")
            .order_by("-created_at")
        )

        serializer = self.get_serializer(comments, many=True)
        return Response(serializer.data)
