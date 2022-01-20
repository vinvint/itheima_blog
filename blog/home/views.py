from django.core.paginator import Paginator, EmptyPage
from django.http import HttpResponseNotFound
from django.shortcuts import render
from django.views import View
from home.models import ArticleCtegory, Article
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


class DetailView(View):
    def get(self, request):
        '''
        1.接收文章id
        2.文章数据查询
        3.查询分类数据
        4.组织模板数据
        '''
        # 1.接收文章id
        id = request.GET.get('id')
        # 2.文章数据查询
        try:
            article = Article.objects.get(id=id)
        except Article.DoesNotExist:
            pass
        # 3.查询分类数据
        categories = ArticleCtegory.objects.all()
        # 4.组织模板数据
        context = {
            'categories': categories,
            'category': article.category,
            'article': article
        }
        return render(request, 'detail.html', context)