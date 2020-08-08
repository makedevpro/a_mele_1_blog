from django.contrib.postgres.search import SearchVector, SearchQuery, \
    SearchRank, TrigramSimilarity
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.core.mail import send_mail
from django.db.models import Count
from django.views.generic import ListView
from django.shortcuts import render, get_object_or_404

from taggit.models import Tag

from .models import Post, Comment
from .forms import EmailPostForm, CommentForm, SearchForm


def post_list(request, tag_slug=None):
    """ Выводим все опубликованные статьи. """
    object_list = Post.published.all()
    tag = None
    if tag_slug:
        tag = get_object_or_404(Tag, slug=tag_slug)
        object_list = object_list.filter(tags__in=[tag])

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
                                                   'posts': posts,
                                                   'tag': tag})


def post_detail(request, year, month, day, post):
    """ Выводим подробную информацию о статье. """
    post = get_object_or_404(Post, slug=post, status='published',
                             publish__year=year, publish__month=month,
                             publish__day=day)
    # Список активных комментариев для данной статьи
    comments = Comment.objects.filter(active=True)
    new_comment = None

    # Добавил по причине "local variable 'comment_form'
    # referenced before assignment"
    comment_form = CommentForm()
    if request.method == 'POST':
        # Пользователь отправил комментарий.
        comment_form = CommentForm(data=request.POST)
        if comment_form.is_valid():
            # Создаем комментарий, но пока не сохраняем в базе данных.
            new_comment = comment_form.save(commit=False)
            # Привязываем комментарий к текущей статье
            new_comment.post = post
            # Сохраняем комментарий в базе данных
            new_comment.save()
        else:
            comment_form = CommentForm()

    # Формирование списка похожих статей
    # Метод QuerySet’а values_list() воз-
    # вращает кортежи со значениями заданного поля. Мы указали flat=True,
    # чтобы получить «плоский» список вида [1, 2, 3, ...]
    post_tags_ids = post.tags.values_list('id', flat=True)
    # использует функцию агрегации Count для формирования вычисляемого
    # поля same_tags, которое содержит определенное количество совпадаю-
    # щих тегов;
    similar_posts = Post.published.filter(tags__in=post_tags_ids)\
                                  .exclude(id=post.id)
    similar_posts = similar_posts.annotate(same_tags=Count('tags'))\
                                 .order_by('-same_tags', '-publish')[:4]
    # Django-taggit также включает менеджер similar_objects(), который мож-
    # но использовать для поиска подобных объектов. Ознакомиться с полным опи-
    # санием менеджеров django-taggit вы можете на странице
    # https://django-taggit.readthedocs.io/en/latest/api.html.
    return render(request, 'blog/post/detail.html',
                  {'post': post,
                   'comments': comments,
                   'new_comment': new_comment,
                   'comment_form': comment_form,
                   'similar_posts': similar_posts})


class PostListView(ListView):
    # queryset вместо model, чтобы использовать свой менеджер published
    queryset = Post.published.all()
    context_object_name = 'posts'  # иначе будет object_list
    paginate_by = 3  # ListView передает в контекст page_obj
    template_name = 'blog/post/list_cbv.html'


def post_share(request, post_id):
    # Получение статьи по идентификатору.
    post = get_object_or_404(Post, id=post_id, status='published')
    sent = False  # Отправлено ли сообщение, передаем в контекст
    if request.method == 'POST':
        # Форма была отправлена на сохранение.
        form = EmailPostForm(request.POST)
        if form.is_valid():
            # Все поля формы прошли валидацию.
            cd = form.cleaned_data
            # ... Отрпавка электронной почты.
            post_url = request.build_absolute_uri(post.get_absolute_url())
            subject = f'{cd["name"]} ({cd["email"]}) recommends you reading ' \
                f'"{post.title}"'
            message = f'Read "{post.title}" at {post_url}\n\n{cd["name"]}\'s ' \
                f'comments: {cd["comments"]}'
            send_mail(subject, message, 'admin@localhost', [cd["to"]])
            sent = True
    else:
        form = EmailPostForm()
    return render(request, 'blog/post/share.html', {'post': post,
                                                    'form': form,
                                                    'sent': sent})


def post_search(request):
    form = SearchForm()
    query = None
    results = []
    if 'query' in request.GET:
        form = SearchForm(request.GET)
        if form.is_valid():
            query = form.cleaned_data['query']
            # Мы можем повысить значимость некоторых векторов, чтобы
            # совпадения по ним считались более релевантными, чем по
            # остальным. Например, можно на- строить поиск так, чтобы статьи с
            # совпадениями в заголовке были в большем приоритете перед статьями
            # с совпадениями в содержимом.
            # search_vector = SearchVector('title', 'body')
            search_vector = SearchVector('title', weight='A') + \
                            SearchVector('body', weight='B')
            search_query = SearchQuery(query)
            results = Post.objects.annotate(
                # search=search_vector,
                # rank=SearchRank(search_vector, search_query))\
                # ПОиск с помощью триграмм
                similarity=TrigramSimilarity('title', query))\
                .filter(similarity__gte=0.3).order_by('-similarity')
                # .filter(rank__gte=0.3).order_by('-rank')
                # .filter(search=search_query).order_by('-rank')
    return render(request, 'blog/post/search.html', {'form': form,
                                                     'query': query,
                                                     'results': results})


def post_search_simple(request):
    """ Поиск """
    form = SearchForm()
    query = None
    results = []
    if 'query' in request.GET:
        form = SearchForm(request.GET)
        if form.is_valid():
            query = form.cleaned_data['query']
            results = Post.objects.annotate(
                search=SearchVector('title', 'body'),)\
                .filter(search=query)
    return render(request, 'blog/post/search.html', {'form': form,
                                                     'query': query,
                                                     'results': results})


def post_search_rank(request):
    """ Стемминг и ранжирование результатов """
    form = SearchForm()
    query = None
    results = []
    if 'query' in request.GET:
        form = SearchForm(request.GET)
        if form.is_valid():
            query = form.cleaned_data['query']
            search_vector = SearchVector('title', 'body')
            search_query = SearchQuery(query)
            results = Post.objects.annotate(
                search=search_vector,
                rank=SearchRank(search_vector, search_query))\
                .filter(search=search_query).order_by('-rank')
    return render(request, 'blog/post/search.html', {'form': form,
                                                     'query': query,
                                                     'results': results})


def post_search_weight(request):
    form = SearchForm()
    query = None
    results = []
    if 'query' in request.GET:
        form = SearchForm(request.GET)
        if form.is_valid():
            query = form.cleaned_data['query']
            # Мы можем повысить значимость некоторых векторов, чтобы
            # совпадения по ним считались более релевантными, чем по
            # остальным. Например, можно на- строить поиск так, чтобы статьи с
            # совпадениями в заголовке были в большем приоритете перед статьями
            # с совпадениями в содержимом.
            search_vector = SearchVector('title', weight='A') + \
                            SearchVector('body', weight='B')
            search_query = SearchQuery(query)
            results = Post.objects.annotate(
                search=search_vector,
                rank=SearchRank(search_vector, search_query))\
                .filter(rank__gte=0.3).order_by('-rank')
            # В этом примере мы применяем векторы по полям title и body с
            # разным ве- сом. По умолчанию используются веса D, C, B и A,
            # которые соответствуют числам 0.1, 0.2, 0.4 и 1. Мы применили
            # вес 1.0 для вектора по полю title и 0.4 – для век- тора по полю
            # body. В конце отбрасываем статьи с низким рангом и показываем
            # только те, чей ранг выше 0.3.
    return render(request, 'blog/post/search.html', {'form': form,
                                                     'query': query,
                                                     'results': results})


def post_search_trigram_similarity(request):
    form = SearchForm()
    query = None
    results = []
    if 'query' in request.GET:
        form = SearchForm(request.GET)
        if form.is_valid():
            query = form.cleaned_data['query']
            results = Post.objects.annotate(
                similarity=TrigramSimilarity('title', query))\
                .filter(similarity__gte=0.3).order_by('-similarity')
    return render(request, 'blog/post/search.html', {'form': form,
                                                     'query': query,
                                                     'results': results})
