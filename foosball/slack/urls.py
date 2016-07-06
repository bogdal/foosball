from django.conf.urls import url

from .views import oauth_callback, slack


urlpatterns = [
    url(r'^$', slack),
    url(r'^oauth/$', oauth_callback, name='oauth')]
