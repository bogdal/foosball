from django.conf.urls import include, url

from .home.urls import urlpatterns as home_urls
from .slack.urls import urlpatterns as slack_urls

urlpatterns = [
    url(r'^', include(home_urls, namespace='home')),
    url(r'^slack/', include(slack_urls, namespace='slack'))]
