from django.urls import path
from . import views

app_name = 'blog'

urlpatterns = [
    # post views
    path('', views.PostListView.as_view(), name='post_list_cbv'),
    path('function_views/', views.post_list, name='post_list'),
    path('<int:year>/<int:month>/<int:day>/<slug:post>/',
         views.post_detail, name='post_detail'),
    path('<int:post_id>/share/', views.post_share, name='post_share'),
    path('tag/<slug:tag_slug>/', views.post_list, name='post_list_by_tag')
]
