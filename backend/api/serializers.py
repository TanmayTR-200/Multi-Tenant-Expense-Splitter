from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import Expense, ExpenseSplit, Group


class UsernameTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Login tokens carry the username claim so the UI can show who is
    logged in without a second API round-trip."""

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['username'] = user.username
        return token


class RegisterSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(min_length=8, write_only=True)


class GroupSerializer(serializers.ModelSerializer):
    members = serializers.SerializerMethodField()
    your_balance_cents = serializers.SerializerMethodField()

    class Meta:
        model = Group
        fields = ['id', 'name', 'members', 'your_balance_cents', 'created_at']

    def get_members(self, obj):
        return [
            {'id': m.user_id, 'username': m.user.username}
            for m in obj.memberships.select_related('user')
        ]

    def get_your_balance_cents(self, obj):
        from .balance import group_net_for_user
        request = self.context.get('request')
        return group_net_for_user(request.user, obj)


class ExpenseSplitInputSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    amount_cents = serializers.IntegerField(min_value=0)


class ExpenseSerializer(serializers.ModelSerializer):
    splits = ExpenseSplitInputSerializer(many=True, required=False)

    class Meta:
        model = Expense
        fields = ['id', 'paid_by', 'description', 'amount_cents', 'created_at', 'splits']
        read_only_fields = ['id', 'paid_by', 'created_at']

    def validate(self, data):
        group = self.context['group']
        splits = data.get('splits') or []
        member_ids = set(group.memberships.values_list('user_id', flat=True))

        for s in splits:
            # TENANT CHECK: the split target must be a member of the group the
            # authenticated user is operating on. Never trust client IDs.
            if s['user_id'] not in member_ids:
                raise serializers.ValidationError(
                    f"user {s['user_id']} is not a member of this group"
                )
        if splits:
            total = sum(s['amount_cents'] for s in splits)
            if total != data['amount_cents']:
                raise serializers.ValidationError(
                    'split amounts must sum to the expense amount'
                )
        return data

    def create(self, validated_data):
        group = self.context['group']
        request = self.context['request']
        splits = validated_data.pop('splits', None)
        amount = validated_data['amount_cents']
        if not splits:
            # Default: split equally among all members. Remainder cents
            # can't divide evenly, so rotate WHICH members absorb them
            # from one expense to the next — otherwise the same (lowest
            # id) members overpay by a cent on every expense and the
            # bias accumulates, e.g. 1000 + 500 over 3 members would
            # drift to shares of 500.01 / 500.00 / 499.99 instead of
            # an exact 500 each.
            member_ids = sorted(group.memberships.values_list('user_id', flat=True))
            n = len(member_ids)
            base, rem = divmod(amount, n)
            offset = group.expenses.count() % n
            ordered = member_ids[offset:] + member_ids[:offset] if offset else member_ids
            splits = [
                {'user_id': uid, 'amount_cents': base + (1 if i < rem else 0)}
                for i, uid in enumerate(ordered)
            ]
        # The payer is always the authenticated user — never client-controlled.
        expense = Expense.objects.create(
            group=group, paid_by=request.user,
            description=validated_data['description'],
            amount_cents=amount,
        )
        ExpenseSplit.objects.bulk_create(
            [ExpenseSplit(expense=expense, **s) for s in splits]
        )
        return expense
