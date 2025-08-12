import os
import uuid
import bleach
from django.core.exceptions import ValidationError
from django.db import models
from django.conf import settings
from django.utils.text import slugify
from django.utils import timezone
from datetime import datetime, timedelta


def profile_image_file_path(instance, filename):
    _, extension = os.path.splitext(filename)
    filename = f"{slugify(instance.user.email)}-{uuid.uuid4()}{extension}"
    return os.path.join("uploads/profiles/", filename)


def validate_image_size(image):
    """Validate image file size (max 5MB)"""
    if image.size > 5 * 1024 * 1024:
        raise ValidationError("Image file too large ( > 5MB )")


def validate_future_date(value):
    """Validate that date is in the future but not too far"""
    now = timezone.now()
    if value <= now:
        raise ValidationError("Scheduled time must be in the future.")

    # Don't allow scheduling more than 1 year in advance
    max_future = now + timedelta(days=365)
    if value > max_future:
        raise ValidationError("Cannot schedule more than 1 year in advance.")


class Profile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    profile_image = models.ImageField(
        upload_to=profile_image_file_path,
        blank=True,
        null=True,
        validators=[validate_image_size],
    )
    bio = models.TextField(blank=True, max_length=500)
    location = models.CharField(max_length=100, blank=True)
    birth_date = models.DateField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["-created_at"]),
            models.Index(fields=["user"]),
        ]

    def __str__(self):
        return f"{self.user.email}'s profile"

    def clean(self):
        """Custom validation"""
        if self.birth_date and self.birth_date > timezone.now().date():
            raise ValidationError("Birth date cannot be in the future")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class Post(models.Model):
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    PUBLISHED = "published"
    FAILED = "failed"

    STATUS_CHOICES = [
        (DRAFT, "Draft"),
        (SCHEDULED, "Scheduled"),
        (PUBLISHED, "Published"),
        (FAILED, "Failed"),
    ]

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="posts"
    )
    title = models.CharField(max_length=200)
    content = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=DRAFT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    scheduled_time = models.DateTimeField(
        blank=True, null=True, validators=[validate_future_date]
    )
    published_at = models.DateTimeField(blank=True, null=True)
    tags = models.CharField(
        max_length=200, blank=True, help_text="Comma separated list of tags"
    )
    celery_task_id = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["-created_at"]),
            models.Index(fields=["author"]),
            models.Index(fields=["status"]),
            models.Index(fields=["tags"]),
            models.Index(fields=["scheduled_time"]),
        ]

    def __str__(self):
        return f"{self.title} - {self.status}"

    @property
    def comment_count(self):
        return self.comments.count()

    def can_be_scheduled(self):
        """Check if post can be scheduled"""
        return self.status in [self.DRAFT, self.FAILED]

    def is_scheduled(self):
        """Check if post is scheduled"""
        return self.status == self.SCHEDULED and self.scheduled_time

    def should_be_published(self):
        """Check if scheduled post should be published now"""
        if not self.is_scheduled():
            return False
        return timezone.now() >= self.scheduled_time


class Comment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="comments"
    )
    content = models.TextField(max_length=1000)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    parent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.CASCADE, related_name="replies"
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["-created_at"]),
        ]

    def __str__(self):
        return f"Comment by {self.author.email} on {self.post.title}"


class Follow(models.Model):
    """User following system"""

    follower = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="following"
    )
    following = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="followers"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("follower", "following")
        indexes = [
            models.Index(fields=["follower"]),
            models.Index(fields=["following"]),
        ]

    def clean(self):
        if self.follower == self.following:
            raise ValidationError("Users cannot follow themselves")


class Like(models.Model):
    """Post likes system"""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="likes"
    )
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="likes")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "post")
        indexes = [
            models.Index(fields=["post"]),
        ]
