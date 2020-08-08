from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.core.mail import send_mail
from django.views.generic import ListView
from django.shortcuts import render, get_object_or_404


from .models import Post, Comment
from .forms import EmailPostForm, CommentForm


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
    return render(request, 'blog/post/detail.html',
                  {'post': post,
                   'comments': comments,
                   'new_comment': new_comment,
                   'comment_form': comment_form})


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
