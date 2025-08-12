from celery import shared_task
from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist
from blog.models import Post
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def publish_scheduled_post(self, post_id):
    """
    Celery task to publish a scheduled post
    """
    try:
        post = Post.objects.get(id=post_id)

        # Verify post should be published
        if not post.should_be_published():
            logger.warning(f"Post {post_id} is not ready to be published")
            return f"Post {post_id} is not ready for publishing"

        # Update post status
        post.status = Post.PUBLISHED
        post.published_at = timezone.now()
        post.celery_task_id = None  # Clear task ID since it's completed
        post.save()

        logger.info(f"Successfully published post {post_id}: {post.title}")

        # Optional: Send notifications, update analytics, etc.
        # send_post_published_notification.delay(post_id)

        return f"Post '{post.title}' published successfully"

    except ObjectDoesNotExist:
        logger.error(f"Post {post_id} not found")
        raise

    except Exception as exc:
        logger.error(f"Error publishing post {post_id}: {str(exc)}")

        # Retry with exponential backoff
        try:
            post = Post.objects.get(id=post_id)
            if self.request.retries < self.max_retries:
                raise self.retry(countdown=60 * (2**self.request.retries))
            else:
                # Mark as failed after max retries
                post.status = Post.FAILED
                post.celery_task_id = None
                post.save()
                logger.error(
                    f"Failed to publish post {post_id} after {self.max_retries} retries"
                )
        except ObjectDoesNotExist:
            pass

        raise exc


@shared_task
def cleanup_failed_scheduled_posts():
    """
    Periodic task to clean up posts that failed to publish
    """
    failed_posts = Post.objects.filter(
        status=Post.SCHEDULED,
        scheduled_time__lt=timezone.now() - timezone.timedelta(hours=1),
    )

    count = 0
    for post in failed_posts:
        post.status = Post.FAILED
        post.celery_task_id = None
        post.save()
        count += 1
        logger.warning(f"Marked post {post.id} as failed due to missed schedule")

    return f"Cleaned up {count} failed scheduled posts"
