from django.core.management.base import BaseCommand
from django.utils import timezone
from blog.models import Post
from blog.tasks import publish_scheduled_post


class Command(BaseCommand):
    help = "Retry failed scheduled posts"

    def handle(self, *args, **options):
        failed_posts = Post.objects.filter(status=Post.FAILED)
        count = 0

        for post in failed_posts:
            if post.scheduled_time and post.scheduled_time <= timezone.now():
                # Attempt to publish immediately
                task = publish_scheduled_post.delay(post.id)
                post.celery_task_id = task.id
                post.status = Post.SCHEDULED
                post.save()
                count += 1
                self.stdout.write(f"Retrying post {post.id}: {post.title}")

        self.stdout.write(
            self.style.SUCCESS(f"Successfully queued {count} failed posts for retry")
        )
