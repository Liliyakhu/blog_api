from rest_framework import viewsets, permissions, filters
from rest_framework.exceptions import PermissionDenied

from .models import Profile
from .serializers import ProfileSerializer


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
