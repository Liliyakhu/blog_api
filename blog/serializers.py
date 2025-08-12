from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.utils import timezone
from blog.models import Post, Comment, Profile, Follow, Like

User = get_user_model()


class UserBasicSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "email", "first_name", "last_name")

    def get_profile_image(self, obj):
        request = self.context.get("request")
        if hasattr(obj, "profile") and obj.profile.profile_image:
            if request:
                return request.build_absolute_uri(obj.profile.profile_image.url)
            return obj.profile.profile_image.url
        return None


class ProfileSerializer(serializers.ModelSerializer):
    user = UserBasicSerializer(read_only=True)
    followers_count = serializers.SerializerMethodField()
    following_count = serializers.SerializerMethodField()
    posts_count = serializers.SerializerMethodField()
    is_following = serializers.SerializerMethodField()

    class Meta:
        model = Profile
        fields = [
            "id",
            "user",
            "profile_image",
            "bio",
            "location",
            "birth_date",
            "created_at",
            "followers_count",
            "following_count",
            "posts_count",
            "is_following",
        ]
        read_only_fields = ["id", "created_at", "user"]

    def get_followers_count(self, obj):
        return obj.user.followers.count()

    def get_following_count(self, obj):
        return obj.user.following.count()

    def get_posts_count(self, obj):
        return obj.user.posts.count()

    def get_is_following(self, obj):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            return Follow.objects.filter(
                follower=request.user, following=obj.user
            ).exists()
        return False

    def validate(self, data):
        """Custom validation for profile data"""
        if "birth_date" in data and data["birth_date"]:
            from django.utils import timezone

            if data["birth_date"] > timezone.now().date():
                raise serializers.ValidationError(
                    {"birth_date": "Birth date cannot be in the future"}
                )
        return data


class CommentSerializer(serializers.ModelSerializer):
    author = UserBasicSerializer(read_only=True)
    replies = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = [
            "id",
            "author",
            "content",
            "created_at",
            "updated_at",
            "parent",
            "replies",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "author"]

    def get_replies(self, obj):
        # Only include replies if they exist and we're not too deep
        if hasattr(obj, "replies") and obj.replies.exists():
            # Limit nesting depth to avoid performance issues
            depth = self.context.get("depth", 0)
            if depth < 2:  # Max 2 levels of nesting
                context = self.context.copy()
                context["depth"] = depth + 1
                serializer = CommentSerializer(
                    obj.replies.all(), many=True, context=context
                )
                return serializer.data
        return []


class PostSerializer(serializers.ModelSerializer):
    author = UserBasicSerializer(read_only=True)
    likes_count = serializers.SerializerMethodField()
    comments_count = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = [
            "id",
            "author",
            "title",
            "content",
            "status",
            "created_at",
            "updated_at",
            "scheduled_time",
            "published_at",
            "tags",
            "celery_task_id",
            "likes_count",
            "comments_count",
            "is_liked",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
            "author",
            "published_at",
            "celery_task_id",
        ]

    def validate_scheduled_time(self, value):
        """Validate scheduled time is in the future"""
        if value and value <= timezone.now():
            raise serializers.ValidationError("Scheduled time must be in the future.")
        return value

    def validate(self, data):
        """Validate post data"""
        status = data.get(
            "status", self.instance.status if self.instance else Post.DRAFT
        )
        scheduled_time = data.get("scheduled_time")

        if status == Post.SCHEDULED and not scheduled_time:
            raise serializers.ValidationError(
                "Scheduled time is required for scheduled posts."
            )

        if status != Post.SCHEDULED and scheduled_time:
            raise serializers.ValidationError(
                "Scheduled time should only be set for scheduled posts."
            )

        return data

    def get_likes_count(self, obj):
        return obj.likes.count()

    def get_comments_count(self, obj):
        return obj.comments.count()

    def get_is_liked(self, obj):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            return Like.objects.filter(user=request.user, post=obj).exists()


class SchedulePostSerializer(serializers.Serializer):
    """Serializer for scheduling existing posts"""

    scheduled_time = serializers.DateTimeField()

    def validate_scheduled_time(self, value):
        if value <= timezone.now():
            raise serializers.ValidationError("Scheduled time must be in the future.")
        return value


class PostDetailSerializer(PostSerializer):
    comments = CommentSerializer(many=True, read_only=True)

    class Meta(PostSerializer.Meta):
        fields = PostSerializer.Meta.fields + ["comments"]


class FollowerSerializer(serializers.ModelSerializer):
    follower = UserBasicSerializer(read_only=True)

    class Meta:
        model = Follow
        fields = ("follower", "created_at")


class FollowingSerializer(serializers.ModelSerializer):
    following = UserBasicSerializer(read_only=True)

    class Meta:
        model = Follow
        fields = ("following", "created_at")


class LikeSerializer(serializers.ModelSerializer):
    """Serializer for Like model"""

    user = UserBasicSerializer(read_only=True)
    post_title = serializers.CharField(source="post.title", read_only=True)

    class Meta:
        model = Like
        fields = ["id", "user", "post", "post_title", "created_at"]
        read_only_fields = ["id", "user", "created_at"]
