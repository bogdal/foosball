import json
import random
import re

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

SLACK_AUTH_URL = 'https://slack.com/oauth/authorize'
SLACK_ACCESS_URL = 'https://slack.com/api/oauth.access'
SLACK_POST_URL = 'https://slack.com/api/chat.postMessage'


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
        color = '#3AA3E3'
        message = {
            'response_type': 'in_channel',
            'text': '<!here> Who wants to play :soccer:?',
            'attachments': [{
                'fallback': 'You are unable to play',
                'callback_id': 'foosball_game',
                'color': color,
                'attachment_type': 'default',
                'actions': [{
                    'name': 'Join / Leave',
                    'text': 'Join / Leave',
                    'type': 'button',
                    'value': 'add'}]}]}

        def get_players(items, link_names=False):
            display = '<@%s>' if link_names else '@%s'
            return ', '.join(map(lambda x: display % x, items))

        for action in data.get('actions', []):
            fields = data['original_message']['attachments'][0].get('fields')
            value = fields[0]['value'] if fields else ''
            players = re.findall('(?<=@)\w+', value)
            if action['value'] == 'add':
                if data['user']['name'] in players:
                    players.remove(data['user']['name'])
                else:
                    players.append(data['user']['name'])
                message['attachments'][0]['fields'] = [{
                    'title': 'Players' if players else '',
                    'value': get_players(players)}]

            if len(players) == 4:
                random.shuffle(players)
                team = SlackTeam.objects.get(team_id=data['team']['id'])
                new_message = {
                    'token': team.access_token,
                    'response_type': 'in_channel',
                    'channel': data['channel']['id'],
                    'attachments': json.dumps([{
                        'text': 'Alright, let\'s play :zap:',
                        'fields': [{
                            'title': 'Team 1',
                            'value': get_players(players[:2]),
                            'short': True}, {
                            'title': 'Team 2',
                            'value': get_players(players[2:]),
                            'short': True}],
                        'color': color}])}
                requests.post(SLACK_POST_URL, data=new_message)

                message = {
                    'response_type': 'in_channel',
                    'text': 'Team collected :+1:'}
        requests.post(data['response_url'], data=json.dumps(message))
        return HttpResponse()
    return redirect('/')
