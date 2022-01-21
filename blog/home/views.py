from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator, EmptyPage
from django.http import HttpResponseNotFound
from django.shortcuts import render, redirect
from django.views import View
from home.models import ArticleCtegory, Article, Comment
from django.urls import reverse
# Create your views here.


class IndexView(View):

    def get(self, request):
        '''
        1.获取所有分类信息
        2.接受用户点击的分类id
        3.数据查询
        4.获取分页参数
        5.根据分类信息查询文章数据
        6.创建分页器
        7.进行分页
        8.组织数据，传递给模板
        '''
        # 1.获取所有分类信息
        categories = ArticleCtegory.objects.all()
        # 2.接受用户点击的分类id
        # 如果没有传递该参数，默认值为1
        cat_id = request.GET.get('cat_id', 1)
        # 3.数据查询
        try:
            category = ArticleCtegory.objects.get(id=cat_id)
        except ArticleCtegory.DoesNotExist:
            return HttpResponseNotFound
        # 4.获取分页参数
        page_num = request.GET.get('page_num', 1)
        page_size = request.GET.get('page_size', 10)
        # 5.根据分类信息查询文章数据
        # filter返回满足条件的对象列表，若对象不存在，返回空列表
        # get返回一个对象，若对象不存在，会报错
        articles = Article.objects.filter(category=category)
        # 6.创建分页器
        paginator = Paginator(articles, per_page=page_size)
        # 7.进行分页
        try:
            page_article = paginator.page(page_num)
        except EmptyPage:
            return HttpResponseNotFound('empty page')
        # 总页数
        total_page = paginator.num_pages
        # 8.组织数据，传递给模板
        context = {
            'categories': categories,
            'category': category,
            'page_article': page_article,
            'page_size': page_size,
            'total_page': total_page,
            'page_num': page_num
        }
        return render(request, 'index.html', context)


class DetailView(LoginRequiredMixin, View):
    def get(self, request):
        '''
        1.接收文章id
        2.文章数据查询
        3.查询分类数据
        4.查询浏览量最高的10篇文章
        5.获取分页请求参数
        6.根据文章信息查询评论数据
        7.创建分页器
        8.分页处理
        9.组织模板数据
        '''
        # 1.接收文章id
        id = request.GET.get('id')
        # 2.文章数据查询
        try:
            article = Article.objects.get(id=id)
        except Article.DoesNotExist:
            return render(request, '404.html')
        else:
            # 若查询到某文章，则文章浏览量加1
            article.total_views += 1
            article.save()
        # 3.查询分类数据
        categories = ArticleCtegory.objects.all()
        # 4.查询浏览量最高的10篇文章
        # 按浏览量降序排序
        hot_articles = Article.objects.order_by('-total_views')[:9]
        # 5.获取分页请求参数
        page_size = request.GET.get('page_size', 10)
        page_num = request.GET.get('page_num', 1)
        # 6.根据文章信息查询评论数据
        comments = Comment.objects.filter(article=article).order_by('-created')
        total_count = comments.count()
        # 7.创建分页器
        paginator = Paginator(comments, page_size)
        # 8.分页处理
        try:
            page_comment = paginator.page(page_num)
        except EmptyPage:
            return HttpResponseNotFound('empty page')
        # 总页数
        total_page = paginator.num_pages
        # 9.组织模板数据
        context = {
            'categories': categories,
            'category': article.category,
            'article': article,
            'hot_articles': hot_articles,
            'total_count': total_count,
            'comments': page_comment,
            'page_size': page_size,
            'total_page': total_page,
            'page_num': page_num
        }
        return render(request, 'detail.html', context)

    def post(self, request):
        '''
        1.接受用户信息
        2.判断用户是否登录
        3.登录用户接收form数据
            3.1接收评论数据
            3.2验证文章是否存在
            3.3保存评论数据
            3.4修改文章评论数量
        4.未登录用户跳转至登陆页面
        '''
        # 1.接受用户信息
        user = request.user
        # 2.判断用户是否登录
        if user and user.is_authenticated:
            # 3.登录用户接收评论数据
            #     3.1接收评论数据
            id = request.POST.get('id')
            content = request.POST.get('content')
            #     3.2验证文章是否存在
            try:
                article = Article.objects.get(id=id)
            except Article.DoesNotExist:
                return HttpResponseNotFound('没有此文章')
            #     3.3保存评论数据
            Comment.objects.create(
                content=content,
                article=article,
                user=user
            )
            #     3.4修改文章评论数量
            article.comment_count += 1
            article.save()

            # 刷新当前页面
            path = reverse('home:detail') + '?id={}'.format(article.id)
            return redirect(path)
        # 4.未登录用户跳转至登陆页面
        else:
            return redirect(reverse('users:login'))