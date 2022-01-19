from random import randint

import django_redis
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, redirect
from django.urls import reverse
from django.views import View
from django.http.response import HttpResponseBadRequest, HttpResponse, JsonResponse
from libs.captcha.captcha import captcha
from django_redis import get_redis_connection
from home.models import ArticleCtegory, Article

from libs.yuntongxun.sms import CCP
from utils.response_code import RETCODE
import logging
import re
from users.models import User
from django.db import DatabaseError
# Create your views here.

logger = logging.getLogger('')


class RegisterView(View):
    # get方式的请求
    def get(self, request):

        return render(request,'register.html')

    def post(self, request):
        '''
        1.接收数据
        2.验证数据
            2.1参数是否齐全
            2.2手机号格式是否正确
            2.3密码是否符合格式
            2.4密码和确认密码是否一致
            2.5短信验证码是否和redis中一致
        3.保存信息
        4.返回响应，跳转至指定页面
        '''
        # 1.接收数据
        mobile = request.POST.get('mobile')
        password = request.POST.get('password')
        password2 = request.POST.get('password2')
        sms_code = request.POST.get('sms_code')
        # 2.验证数据
        #     2.1参数是否齐全
        if not all([mobile, password, password2, sms_code]):
            return HttpResponseBadRequest('缺少必要参数')
        #     2.2手机号格式是否正确
        if not re.match(r'^1[3-9]\d{9}$', mobile):
            return HttpResponseBadRequest('手机号不符合规则')
        #     2.3密码是否符合格式
        if not re.match(r'^[0-9A-Za-z]{8,20}$', password):
            return HttpResponseBadRequest('请输入8-20位密码，密码为数字、字母')
        #     2.4密码和确认密码是否一致
        if password != password2:
            return HttpResponseBadRequest('密码不一致')
        #     2.5短信验证码是否和redis中一致
        redis_conn = get_redis_connection('default')
        redis_sms_code = redis_conn.get('sms:%s'%mobile)
        if redis_sms_code is None:
            return HttpResponseBadRequest('短信验证码已过期')
        # try:
        #     redis_conn.delete('sms:%s'%mobile)
        # except Exception as e:
        #     logger.error(e)
        if sms_code != redis_sms_code.decode():
            return HttpResponseBadRequest('验证码错误')
        # 3.保存信息
        # 使用系统自带的create_user()对密码加密
        try:
            user = User.objects.create_user(username=mobile,
                                            mobile=mobile,
                                            password=password)
        except DatabaseError as e:
            logger.error(e)
            return HttpResponseBadRequest('注册失败')
        # 将用户标识写入session，实现状态保持
        # 通过django自带的login实现
        login(request, user)

        # 4.返回响应，跳转至指定页面
        # redirect重定向
        # reverse通过namespace:name获取视图所对应的路由
        response = redirect(reverse('home:index'))
        # 设置cookie信息，以方便首页中用户信息的展示和判断
        response.set_cookie('is_login', True)
        response.set_cookie('username', user.username, max_age=7*24*3600)
        return response


class ImageCodeView(View):
    def get(self, request):
        """
        1.接受前端传递的uuid
        2.判断uuid是否获取到
        3.通过调用captcha生成图片验证码
        4.将图片内容保存至redis
            uuid作为key，图片内容作为value
            同时还要设置一个时效
        5。返回图片验证码
        """
        # 1.接受前端传递的uuid
        uuid = request.GET.get('uuid')
        # 2.判断uuid是否获取到
        if uuid is None:
            return HttpResponseBadRequest('没有图片验证码信息')
        # 3.通过调用captcha生成图片验证码
        text, image = captcha.generate_captcha()
        # 4.将图片内容保存至redis
        #   uuid作为key，图片内容作为value
        #   同时还要设置一个时效
        redis_conn = get_redis_connection('default')
        # seconds为过期秒数
        # 为uuid添加前缀
        # redis_conn.setex(key, seconds, value)
        redis_conn.setex('img:%s'%uuid, 300, text)
        # 5。返回图片验证码
        return HttpResponse(image, content_type='image/jpeg')


class SmsCodeView(View):
    def get(self, request):
        '''
        1.接收参数
        2.参数验证
            2.1验证参数是否齐全
            2.2图片验证码的验证
                若图片验证码未过期，获取之后就可以删除图片验证码
        3.生成短信验证码
        4.保存短信验证码到redis
        5.发送短信
        6.返回响应
        '''
        # 1.接收参数
        mobile = request.GET.get('mobile')
        image_code = request.GET.get('image_code')
        uuid = request.GET.get('uuid')
        # 2.参数验证
        #     2.1验证参数是否齐全
        if not all([mobile, image_code, uuid]):
            return JsonResponse({'code':RETCODE.NECESSARYPARAMERR, 'errmsg':'缺少参数信息'})
        #     2.2图片验证码的验证
        #         若图片验证码未过期，获取之后就可以删除图片验证码
        redis_conn = get_redis_connection('default')
        redis_image_code = redis_conn.get('img:%s'%uuid)
        # 判断图片验证码是否存在
        if redis_image_code is None:
            return JsonResponse({'code':RETCODE.IMAGECODEERR, 'errmsg':'图片验证码已过期'})
        # 删除redis中的图片验证码
        try:
            redis_conn.delete('img:%s'%uuid)
        except Exception as e:
            logger.error(e)
        # 图片验证码比对
        if redis_image_code.decode().lower() != image_code.lower():
            return JsonResponse({'code':RETCODE.IMAGECODEERR, 'errmsg':'图片验证码错误'})
        # 3.生成6位短信验证码
        sms_code = '%06d'%randint(0,999999)
        # 为了后期比对方便，可以将短信验证码记录到日志中
        logger.info(sms_code)
        # 4.保存短信验证码到redis
        redis_conn.setex('sms:%s'%mobile, 300, sms_code)
        # 5.发送短信
        # 参数1：测试手机号
        # 参数2：您的验证码时{1}，请于{2}分钟内正确输入
        #       {1}短信验证码
        #       {2}短信验证码有效期
        # 参数3：短信模板ID
        CCP().send_template_sms(mobile, [sms_code,5], 1)
        # 6.返回响应
        return JsonResponse({'code':RETCODE.OK, 'errmsg':'短信发送成功'})


class LoginView(View):
    def get(self,request):

        return render(request, 'login.html')

    def post(self,request):
        '''
        1.接收参数
        2.参数验证
            2.1验证手机号是否符合规则
            2.2验证密码是否符合规则
        3.用户认证登录
        4.状态保持
        5.根据用户选择的是否记住登陆状态进行判断
        6.为首页显示设置一些cookie信息
        7.返回响应
        '''
        # 1.接收参数
        mobile = request.POST.get('mobile')
        password = request.POST.get('password')
        remember = request.POST.get('remember')
        # 2.参数验证
        #     2.1验证手机号是否符合规则
        if not re.match(r'^1[3-9]\d{9}$', mobile):
            return HttpResponseBadRequest('手机号不符合规则')
        #     2.2验证密码是否符合规则
        if not re.match(r'^[0-9a-zA-Z]{8,20}$', password):
            return HttpResponseBadRequest('密码不符合规则')
        # 3.用户认证登录
        # 采用系统自带认证方法进行认证
        # 用户名密码正确会返回user对象，错误会返回None
        # 默认的认证方法是针对于 username 字段进行用户名的判断
        # 而当前判断信息为 手机号，所以要修改user模型中的认证字段
        user = authenticate(mobile=mobile, password=password)
        if user is None:
            return HttpResponseBadRequest('用户名或密码错误')
        # 4.状态保持
        login(request, user)
        # 5.根据用户选择的是否记住登陆状态进行判断
        # 6.为首页显示设置一些cookie信息

        # 根据next参数进行页面跳转
        next_page = request.GET.get('next')
        if next_page:
            response = redirect(next_page)
        else:
            response = redirect(reverse('home:index'))
        # 不保持登陆状态
        if remember != 'on':
            # 设置过期时间为0，即关闭浏览器退出登录
            request.session.set_expiry(0)
            response.set_cookie('is_login',True)
            response.set_cookie('username', user.username, max_age=14*24*3600)
        # 保持登陆状态
        else:
            # 默认是记住两周
            request.session.set_expiry(None)
            response.set_cookie('is_login', True, max_age=14*24*3600)
            response.set_cookie('username', user.username, max_age=14*24*3600)
        # 7.返回响应
        return response


class LogoutView(View):

    def get(self,request):
        # 1.session数据删除
        logout(request)
        # 2.删除部分cookie数据
        response = redirect(reverse('home:index'))
        response.set_cookie('is_login', "", 0)
        # response.delete_cookie('is_login')
        # 3.跳转至首页
        return response


class ForgetPasswordView(View):

    def get(self, request):

        return render(request, 'forget_password.html')

    def post(self,request):
        '''
        1.接收数据
        2.验证数据
            2.1判断参数是否齐全
            2.2验证手机号是否符合规则
            2.3验证密码是否符合规则
            2.4验证密码和确认密码是否一致
            2.5判断短信验证码是否正确
        3.根据手机号进行用户信息查询
        4.如果手机号查询出用户信息则进行用户密码修改
        5.如果手机号未查询出用户信息则创建新用户
        6.进行页面跳转，跳转至登陆页面
        7.返回响应
        '''
        # 1.接收数据
        mobile = request.POST.get('mobile')
        password = request.POST.get('password')
        password2 = request.POST.get('password2')
        smscode = request.POST.get('sms_code')
        # 2.验证数据
        #     2.1判断参数是否齐全
        if not all([mobile, password, password2, smscode]):
            return HttpResponseBadRequest('参数不齐全')
        #     2.2验证手机号是否符合规则
        if not re.match(r'^1[3-9]\d{9}$', mobile):
            return HttpResponseBadRequest('手机号不符合格式')
        #     2.3验证密码是否符合规则
        if not re.match(r'^[0-9a-zA-Z]{8,20}$', password):
            return HttpResponseBadRequest('密码不符合规则')
        #     2.4验证密码和确认密码是否一致
        if password != password2:
            return HttpResponseBadRequest('密码不一致')
        #     2.5判断短信验证码是否正确
        redis_conn = get_redis_connection('default')
        redis_sms_code = redis_conn.get('sms:%s'%mobile)
        if redis_sms_code is None:
            return HttpResponseBadRequest('短信验证码已过期')
        if redis_sms_code.decode() != smscode:
            return HttpResponseBadRequest('短信验证码错误')
        # 3.根据手机号进行用户信息查询
        try:
            user = User.objects.get(mobile=mobile)
        except User.DoesNotExist:
        # 5.如果手机号未查询出用户信息则创建新用户
            try:
                User.objects.create_user(username=mobile,
                                         mobile=mobile,
                                         password=password)
            except Exception:
                return HttpResponseBadRequest('修改失败')
        else:
        # 4.如果手机号查询出用户信息则进行用户密码修改
            user.set_password(password)
            # 保存用户信息
            user.save()
        # 6.进行页面跳转，跳转至登陆页面
        response = redirect(reverse('users:login'))
        # 7.返回响应
        return response


# 继承LoginRequiredMixin类，访问该视图时，若用户未登录，则进行默认跳转
# 默认的跳转路由是：accounts/login/?next=xxx
# 在settings中修改系统默认跳转路由为/login/，则用户未登录时，访问登陆页面
# 此时在登录页面进行登录，会进入首页。
# 修改登录视图，实现默认进入首页，而在此情况下跳转至'个人中心'页面
class UserCenterView(LoginRequiredMixin, View):

    def get(self, request):
        # 获取登陆用户信息
        user = request.user
        # 组织获取用户的信息
        context = {
            'username': user.username,
            'mobile': user.mobile,
            'avatar': user.avatar.url if user.avatar else None,
            'user_desc': user.user_desc
        }
        return render(request, 'center.html', context)

    def post(self, request):
        '''
        1.接收参数
        2.将参数保存
        3.更新cookie中的username
        4.刷新当前页面（重定向）
        5.返回响应
        '''
        user = request.user
        # 1.接收参数
        username = request.POST.get('username', user.username)
        user_desc = request.POST.get('desc', user.user_desc)
        # 若用户修改头像，则会以文件的形式传递图片
        avatar = request.FILES.get('avatar')
        # 2.将参数保存
        try:
            user.username = username
            user.user_desc = user_desc
            if avatar:
                user.avatar = avatar
            user.save()
        except Exception as e:
            logger.error(e)
            return HttpResponseBadRequest('修改失败，请稍后再试')
        # 3.更新cookie中的username
        # 4.刷新当前页面（重定向）
        response = redirect(reverse('users:center'))
        response.set_cookie('username', user.username, max_age=14*24*3600)
        # 5.返回响应
        return response


class WriteBlogView(LoginRequiredMixin, View):
    def get(self, request):
        # 查询所有分类信息
        categories = ArticleCtegory.objects.all()
        context = {
            'categories':categories
        }
        return render(request, 'write_blog.html', context)

    def post(self, request):
        '''
        1.接收参数
        2.验证参数
        3.保存数据
        4.跳转至指定页面
        '''
        # 1.接收参数
        avatar = request.FILES.get('avatar')
        title = request.POST.get('title')
        category_id = request.POST.get('category')
        tags = request.POST.get('tags')
        summary = request.POST.get('sumary')
        content = request.POST.get('content')
        user = request.user
        # 2.验证参数
        # 2.1验证参数是否齐全
        if not all([avatar, title, category_id, tags, summary, content]):
            return HttpResponseBadRequest('参数不全')
        # 2.2判断分类id
        try:
            category = ArticleCtegory.objects.get(id=category_id)
        except ArticleCtegory.DoesNotExist:
            return HttpResponseBadRequest('没有此分类')
        # 3.保存数据
        try:
            article = Article.objects.create(
                auther=user,
                title=title,
                avatar=avatar,
                category=category,
                tags=tags,
                sumary=summary,
                content=content
            )
        except Exception as e:
            logger.error(e)
            return HttpResponseBadRequest('发布失败，请稍后再试')
        # 4.跳转至指定页面
        return redirect(reverse('home:index'))