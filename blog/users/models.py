from django.db import models
from django.contrib.auth.models import AbstractUser
# Create your models here.


class User(AbstractUser):

    # 手机号
    mobile = models.CharField(max_length=11, unique=True, blank=False)
    # 头像信息
    # ImageField自动保存图片文件（默认保存在工程文件中），并记录图片路径
    avatar = models.ImageField(upload_to='avatar/%Y%m%d/', blank=True)
    # 简介信息
    user_desc = models.CharField(max_length=200, blank=True)
    # 修改（登录等）认证字段为手机号（默认为username）
    USERNAME_FIELD = 'mobile'

    # 新增超级管理员时必须输入的字段
    REQUIRED_FIELDS = ['username', 'email']

    class Meta:
        db_table = 'tb_users' # 设置表名
        verbose_name = '用户管理' # admin后台管理
        verbose_name_plural = verbose_name # admin后台显示

    def __str__(self):
        return self.mobile