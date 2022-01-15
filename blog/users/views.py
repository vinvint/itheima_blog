from random import randint

from django.shortcuts import render
from django.views import View
from django.http.response import HttpResponseBadRequest, HttpResponse, JsonResponse
from libs.captcha.captcha import captcha
from django_redis import get_redis_connection

from libs.yuntongxun.sms import CCP
from utils.response_code import RETCODE
import logging
# Create your views here.

logger = logging.getLogger('')


class RegisterView(View):
    # get方式的请求
    def get(self, request):

        return render(request,'register.html')


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
