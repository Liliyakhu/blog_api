# blog_api

## Description:
A RESTful API for a social media platform. 
The API allows users to create profiles, follow other users, 
create and retrieve posts, manage likes and comments, 
and perform basic social media actions.

## Requirements:

### User Registration and Authentication:
- Users are able to register with their email and password to create an account.
- Users are able to login with their credentials and receive a token for authentication.
- Users are able to logout and invalidate their token.

### User Profile:
- Users are able to create and update their profile, 
including profile picture, bio, and other details.
- Users are able to retrieve their own profile 
and view profiles of other users.
- Users are able to search for users by username or other criteria.

### Follow/Unfollow:
- Users are able to follow and unfollow other users 
(how to check: 
  - to follow - http://localhost:8000/api/blog/profiles/2/follow/ ->
  - to unfollow - http://localhost:8000/api/blog/profiles/2/follow/ ->
- Users are able to view the list of users they are following and the list of users following them 
(
  - following - http://localhost:8000/api/blog/profiles/2/following/
  - followers - http://localhost:8000/api/blog/profiles/2/followers/).

### Post Creation and Retrieval:
- Users are able to create new posts with text content and optional media attachments (e.g., images). (Adding images is optional task)
- Users are able to retrieve their own posts and posts of users they are following.
- Users should be able to retrieve posts by hashtags or other criteria.

Endpoint and Purpose: 
> GET /api/posts/ - Posts by self and followed users
> 
> POST /api/posts/ - Create a post (optionally with image)
> 
> GET /api/posts/by-hashtag/tag/ - Filter by hashtag
> 
> GET /api/posts/id/ - Retrieve post by ID

### Likes and Comments (Optional):
- Users are able to like and unlike posts. 
- Users are able to view the list of posts they have liked. 
-  Users are be able to add comments to posts and view comments on posts.

### Schedule Post creation using Celery (Optional):
Added possibility to schedule Post creation (you can select the time to create the Post before creating of it).

### API Permissions:
Only authenticated users are able to perform actions such as creating posts, liking posts, and following/unfollowing users.
Only users are able to update and delete their own posts and comments.
Only users are able to update and delete their own profile.

### API Documentation:
The API is documented with clear instructions on how to use each endpoint.
The documentation includes sample API requests and responses for different endpoints.

### Technical Requirements:
Django and Django REST framework to build the API.
Token-based authentication for user authentication.
Appropriate serializers for data validation and representation. 
Appropriate views and viewsets for handling CRUD operations on models.
Appropriate URL routing for different API endpoints.
Appropriate permissions and authentication classes to implement API permissions.
