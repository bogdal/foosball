import json
import random
import re

try:
    from urllib.parse import urlencode
except ImportError:
    from urllib import urlencode

from django.conf import settings
from django.core.urlresolvers import reverse
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect
from django.views.decorators.csrf import csrf_exempt

import requests

from .models import SlackTeam

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
        message = {
            "response_type": "in_channel",
            "text": "<!here> Who wants to play :soccer:?",
            "attachments": [{
                "fallback": "You are unable to play",
                "callback_id": "foosball_game",
                "color": "#3AA3E3",
                "attachment_type": "default",
                "actions": [{
                    "name": "Add me",
                    "text": "Add me",
                    "type": "button",
                    "value": "add"}]}]}

        def get_players(items, link_names=True):
            display = '<@%s>' if link_names else '@%s'
            return ', '.join(map(lambda x: display % x, items))

        for action in data.get('actions', []):
            desc = data['original_message']['attachments'][0].get('text', '')
            players = re.findall('(?<=@)\w+', desc)
            if action['value'] == 'add':
                if data['user']['name'] not in players:
                    players.append(data['user']['name'])
                message['attachments'][0]['text'] = 'Players: %s' % (
                    get_players(players, link_names=False),)
            if len(players) == 4:
                random.shuffle(players)
                message = {
                    "response_type": "in_channel",
                    'text': "Let's play %s :vs: %s" % (
                        get_players(players[:2]),
                        get_players(players[2:]))}
        return JsonResponse(message)
    return redirect('/')
