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
  - to follow - 
http://localhost:8000/api/blog/follows/follow/ -> 
paster { "user_id": 2 } in Content -> Post
  - to unfollow - http://localhost:8000/api/blog/follows/unfollow/ ->
paster { "user_id": 2 } in Content -> Post ).
- Users are able to view the list of users they are following and the list of users following them 
(
  - following - http://localhost:8000/api/blog/follows/following/
  - followers - http://localhost:8000/api/blog/follows/followers/).

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
- Users should be able to like and unlike posts. 
- Users should be able to view the list of posts they have liked. 
-  Users should be able to add comments to posts and view comments on posts.

### Schedule Post creation using Celery (Optional):
Add possibility to schedule Post creation (you can select the time to create the Post before creating of it).

### API Permissions:
Only authenticated users should be able to perform actions such as creating posts, liking posts, and following/unfollowing users.
Users should only be able to update and delete their own posts and comments.
Users should only be able to update and delete their own profile.

### API Documentation:
The API should be well-documented with clear instructions on how to use each endpoint.
The documentation should include sample API requests and responses for different endpoints.

### Technical Requirements:
Use Django and Django REST framework to build the API.
Use token-based authentication for user authentication.
Use appropriate serializers for data validation and representation.
Use appropriate views and viewsets for handling CRUD operations on models.
Use appropriate URL routing for different API endpoints.
Use appropriate permissions and authentication classes to implement API permissions.
Follow best practices for RESTful API design and documentation.
