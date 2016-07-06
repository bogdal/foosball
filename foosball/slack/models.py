from django.db import models


class SlackTeam(models.Model):
    team_id = models.CharField(primary_key=True, max_length=255)
    access_token = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
