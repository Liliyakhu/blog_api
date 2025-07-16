import os
import uuid

from django.contrib.auth import get_user_model
from django.db import models
from django.utils.text import slugify


User = get_user_model()


def profile_image_file_path(instance, filename):
    _, extension = os.path.splitext(filename)
    filename = f"{slugify(instance.user)}-{uuid.uuid4()}{extension}"

    return os.path.join("uploads/profiles/", filename)


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    profile_picture = models.ImageField(
        upload_to=profile_image_file_path, blank=True, null=True
    )
    bio = models.TextField(blank=True)
    location = models.CharField(max_length=100, blank=True)
    birth_date = models.DateField(null=True, blank=True)

    # def __str__(self):
    #     return f"{self.user.email} profile"

    def __str__(self):
        return f"{self.user.get_username()} profile"
