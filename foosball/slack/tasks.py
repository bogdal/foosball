import json
import random
import re

from celery import shared_task
import requests

from .models import SlackTeam


SLACK_POST_URL = 'https://slack.com/api/chat.postMessage'


@shared_task
def handle_slack_request(data):
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
    if data.get('command'):
        message['attachments'][0]['fields'] = [{
            'title': 'Players',
            'value': '@%s' % data['user_name']}]

    def get_players(items, link_names=True):
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
                'value': get_players(players, link_names=False)}]

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
