from django.conf import settings
from django.db import models


class Group(models.Model):
    name = models.CharField(max_length=200)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='groups_created'
    )
    created_at = models.DateTimeField(auto_now_add=True)


class Membership(models.Model):
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='memberships')
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='memberships'
    )

    class Meta:
        unique_together = ('group', 'user')


class Expense(models.Model):
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='expenses')
    paid_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='expenses_paid'
    )
    description = models.CharField(max_length=300)
    # All money is stored as integer cents to avoid float rounding errors.
    amount_cents = models.PositiveBigIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)


class ExpenseSplit(models.Model):
    expense = models.ForeignKey(Expense, on_delete=models.CASCADE, related_name='splits')
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='splits'
    )
    amount_cents = models.PositiveBigIntegerField()

