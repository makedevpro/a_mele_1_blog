from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.views.generic import ListView
from django.shortcuts import render, get_object_or_404


from .models import Post


def post_list(request):
    """ Выводим все опубликованные статьи. """
    object_list = Post.published.all()
    paginator = Paginator(object_list, 3)  # По 3 статьи на каждой странице
    page = request.GET.get('page')
    try:
        posts = paginator.page(page)
    except PageNotAnInteger:
        # Если страница не является целым числом, возвращаем первую страницу.
        posts = paginator.page(1)
    except EmptyPage:
        # Если номер страницы больше, чем общее кол-во страниц,
        # возвращаем последнюю страницу.
        posts = paginator.page(paginator.num_pages)
    return render(request, 'blog/post/list.html', {'page': page,
                                                   'posts': posts})


def post_detail(request, year, month, day, post):
    """ Выводим подробную информацию о статье. """
    post = get_object_or_404(Post, slug=post, status='published',
                             publish__year=year, publish__month=month,
                             publish__day=day)
    return render(request, 'blog/post/detail.html', {'post': post})


class PostListView(ListView):
    # queryset вместо model, чтобы использовать свой менеджер published
    queryset = Post.published.all()
    context_object_name = 'posts'  # иначе будет object_list
    paginate_by = 3  # ListView передает в контекст page_obj
    template_name = 'blog/post/list_cbv.html'
