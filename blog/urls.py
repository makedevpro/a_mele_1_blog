from django.urls import path

from . import views
from .feeds import LatesPostsFeed

app_name = 'blog'

urlpatterns = [
    # post views
    path('', views.PostListView.as_view(), name='post_list_cbv'),
    path('function-views/', views.post_list, name='post_list'),
    path('<int:year>/<int:month>/<int:day>/<slug:post>/',
         views.post_detail, name='post_detail'),
    path('<int:post_id>/share/', views.post_share, name='post_share'),
    path('tag/<slug:tag_slug>/', views.post_list, name='post_list_by_tag'),
    path('feed/', LatesPostsFeed(), name='post_feed'),
    path('search/', views.post_search_simple, name='post_search'),
    path('search-rank/', views.post_search_rank, name='post_search_rank'),
    path('search-weight/', views.post_search_weight, name='post_search_weight'),
    path('search-trigram-similarity/', views.post_search_trigram_similarity,
         name='post_search_trigram_similarity'),
]
