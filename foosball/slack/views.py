import json

try:
    from urllib.parse import urlencode
except ImportError:
    from urllib import urlencode

from django.conf import settings
from django.core.urlresolvers import reverse
from django.http import HttpResponse
from django.shortcuts import redirect
from django.views.decorators.csrf import csrf_exempt

import requests

from .models import SlackTeam
from. tasks import handle_slack_request

SLACK_AUTH_URL = 'https://slack.com/oauth/authorize'
SLACK_ACCESS_URL = 'https://slack.com/api/oauth.access'


def oauth_callback(request):
    code = request.GET.get('code')
    redirect_uri = request.build_absolute_uri(reverse('slack:oauth'))

    if not code:
        params = {
            'client_id': settings.SLACK_CLIENT_ID,
            'redirect_uri': redirect_uri,
            'scope': settings.SLACK_SCOPE}
        return redirect(SLACK_AUTH_URL + '?' + urlencode(params))

    params = {
        'client_id': settings.SLACK_CLIENT_ID,
        'client_secret': settings.SLACK_CLIENT_SECRET,
        'code': code,
        'redirect_uri': redirect_uri}
    response = requests.get(SLACK_ACCESS_URL, params=params)

    if not response.status_code == 200:
        return HttpResponse('Error')

    data = response.json()
    if not data['ok']:
        return HttpResponse(data['error'])

    team, created = SlackTeam.objects.get_or_create(
        team_id=data['team_id'], defaults={
            'access_token': data['access_token']})
    if not created:
        team.access_token = data['access_token']
        team.save()
    return redirect('/')


@csrf_exempt
def slack(request):
    data = json.loads(request.POST.get('payload', '{}')) or request.POST
    if data.get('token') == settings.SLACK_VERIFICATION_TOKEN:
        handle_slack_request.delay(data)
        return HttpResponse()
    return redirect('/')
