from django.db import models
from django.utils import timezone
from users.models import User
# Create your models here.

class ArticleCtegory(models.Model):
    '''
    文章分类
    '''
    # 分类标题
    title = models.CharField(max_length=100, blank=True)
    # 分类创建时间
    created = models.DateField(default=timezone.now)

    def __str__(self):
        return self.title

    class Meta:
        # 修改表名
        db_table = 'tb_category'
        # 设置admin站点
        verbose_name = '类别管理'
        verbose_name_plural = verbose_name


class Article(models.Model):
    '''
    作者
    标题图
    标题
    栏目分类
    标签
    文章摘要
    文章正文
    文章浏览量
    文章评论量
    文章创建时间
    文章修改时间
    '''
    # 作者
    # 参数on_delete=CASCADE即User表中数据删除时，文章信息同步删除
    auther = models.ForeignKey(User, on_delete=models.CASCADE)
    # 标题图
    avatar = models.ImageField(upload_to='article/%Y%m%d/', blank=True)
    # 标题
    title = models.CharField(max_length=20, blank=True)
    # 栏目分类
    # null=True代表数据写入数据库时，该字段可以为空
    # blank=True代表form表单提交时该字段可以为空
    category = models.ForeignKey(ArticleCtegory, null=True, blank=True, on_delete=models.CASCADE, related_name='article')
    # 标签
    tags = models.CharField(max_length=20, blank=True)
    # 文章摘要
    sumary = models.CharField(max_length=200, null=False, blank=False)
    # 文章正文
    content = models.TextField()
    # 文章浏览量
    total_views = models.PositiveIntegerField(default=0)
    # 文章评论量
    comment_count = models.PositiveIntegerField(default=0)
    # 文章创建时间
    created = models.DateTimeField(default=timezone.now)
    # 文章修改时间
    updated = models.DateTimeField(auto_now=True)

    # 修改表名以及展示的配置信息
    class Meta:
        db_table = 'tb_article'
        # 排序方式
        ordering = ('-created',)
        verbose_name = '文章管理'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.title


class Comment(models.Model):
    '''
    评论内容
    评论的文章
    评论时间
    评论用户
    '''
    # 评论内容
    content = models.TextField()
    # 评论的文章
    article = models.ForeignKey(Article, on_delete=models.SET_NULL, null=True)
    # 评论时间
    created = models.DateTimeField(auto_now_add=True)
    # 评论用户
    user = models.ForeignKey(User, on_delete=models.SET, null=True)

    def __str__(self):
        return self.article.title

    class Meta:
        db_table = 'tb_comment'
        verbose_name = '评论管理'
        verbose_name_plural = verbose_name