"""
End-to-end API tests covering the graded core: tenant isolation and
(explicitly) the data the settlement service relies on.

Run with:  python manage.py test api
"""
import base64
import json

from django.contrib.auth.models import User
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Expense, ExpenseSplit, Group, Membership


def auth(user):
    refresh = RefreshToken.for_user(user)
    return {'HTTP_AUTHORIZATION': f'Bearer {refresh.access_token}'}


class Base(APITestCase):
    def setUp(self):
        self.alice = User.objects.create_user('alice', 'a@x.com', 'password123')
        self.bob = User.objects.create_user('bob', 'b@x.com', 'password123')
        self.mallory = User.objects.create_user('mallory', 'm@x.com', 'password123')
        self.group = Group.objects.create(name='Trip', created_by=self.alice)
        Membership.objects.create(group=self.group, user=self.alice)
        Membership.objects.create(group=self.group, user=self.bob)


class TokenClaimTests(APITestCase):
    """Both auth endpoints must issue tokens carrying the username claim
    the UI displays; otherwise the logged-in user is invisible."""

    @staticmethod
    def token_claims(access_token):
        payload = access_token.split('.')[1]
        payload += '=' * (-len(payload) % 4)
        return json.loads(base64.urlsafe_b64decode(payload))

    def test_register_token_contains_username(self):
        res = self.client.post(
            '/api/auth/register/',
            {'username': 'alice', 'email': 'a@x.com', 'password': 'password123'},
            format='json',
        )
        self.assertEqual(res.status_code, 201)
        self.assertEqual(self.token_claims(res.json()['access'])['username'], 'alice')

    def test_login_token_contains_username(self):
        User.objects.create_user('bob', 'b@x.com', 'password123')
        res = self.client.post(
            '/api/auth/login/',
            {'username': 'bob', 'password': 'password123'},
            format='json',
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(self.token_claims(res.json()['access'])['username'], 'bob')


class TenantIsolationTests(Base):
    def test_non_member_cannot_view_group(self):
        res = self.client.get(f'/api/groups/{self.group.id}/', **auth(self.mallory))
        self.assertEqual(res.status_code, 404)

    def test_non_member_cannot_add_expense(self):
        res = self.client.post(
            f'/api/groups/{self.group.id}/',
            {'description': 'hack', 'amount_cents': 100},
            format='json', **auth(self.mallory),
        )
        self.assertIn(res.status_code, (403, 404))
        self.assertEqual(Expense.objects.count(), 0)

    def test_non_member_cannot_see_group_in_list(self):
        res = self.client.get('/api/groups/', **auth(self.mallory))
        self.assertEqual([g['id'] for g in res.json()], [])

    def test_member_sees_group(self):
        res = self.client.get('/api/groups/', **auth(self.alice))
        self.assertEqual([g['id'] for g in res.json()], [self.group.id])

    def test_unauthenticated_rejected(self):
        res = self.client.get('/api/groups/')
        self.assertEqual(res.status_code, 401)

    def test_settlement_data_requires_membership_plus_internal_token(self):
        import hashlib
        from django.conf import settings
        internal = hashlib.sha256(
            (settings.SECRET_KEY + ':settlement-service').encode()
        ).hexdigest()

        # Mallory's JWT + valid internal token -> still 404 (not a member).
        h = auth(self.mallory)
        h['HTTP_X_INTERNAL_TOKEN'] = internal
        res = self.client.get(f'/api/groups/{self.group.id}/settlement-data/', **h)
        self.assertEqual(res.status_code, 404)

        # Member JWT + valid internal token -> 200 with balances.
        h = auth(self.alice)
        h['HTTP_X_INTERNAL_TOKEN'] = internal
        res = self.client.get(f'/api/groups/{self.group.id}/settlement-data/', **h)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.json()['members']), 2)

        # Member JWT but WRONG internal token -> 403 (service not trusted).
        h = auth(self.alice)
        h['HTTP_X_INTERNAL_TOKEN'] = 'wrong'
        res = self.client.get(f'/api/groups/{self.group.id}/settlement-data/', **h)
        self.assertEqual(res.status_code, 403)


class ExpenseTests(Base):
    def test_equal_split_with_remainder(self):
        # 100 cents / 3 members -> 34 + 33 + 33, always sums exactly.
        Membership.objects.create(group=self.group, user=self.mallory)
        res = self.client.post(
            f'/api/groups/{self.group.id}/',
            {'description': 'Dinner', 'amount_cents': 100},
            format='json', **auth(self.alice),
        )
        self.assertEqual(res.status_code, 201)
        splits = sorted(
            ExpenseSplit.objects.values_list('user__username', 'amount_cents')
        )
        self.assertEqual(splits, [('alice', 34), ('bob', 33), ('mallory', 33)])

    def test_remainder_cents_rotate_between_expenses(self):
        # The user-visible invariant: leftover cents must not pile onto the
        # same member on every expense. 1000 + 500 split over 3 members is
        # exactly 500 each; the naive "first members absorb the remainder"
        # split drifts to shares of 500.01 / 500.00 / 499.99.
        Membership.objects.create(group=self.group, user=self.mallory)
        self.client.post(
            f'/api/groups/{self.group.id}/',
            {'description': 'A pays 1000', 'amount_cents': 100000},
            format='json', **auth(self.alice),
        )
        self.client.post(
            f'/api/groups/{self.group.id}/',
            {'description': 'B pays 500', 'amount_cents': 50000},
            format='json', **auth(self.bob),
        )
        res = self.client.get(f'/api/groups/{self.group.id}/', **auth(self.alice))
        balances = {b['username']: b['balance_cents'] for b in res.json()['balances']}
        self.assertEqual(
            balances, {'alice': 50000, 'bob': 0, 'mallory': -50000}
        )

    def test_explicit_split_must_sum_to_amount(self):
        res = self.client.post(
            f'/api/groups/{self.group.id}/',
            {'description': 'X', 'amount_cents': 100,
             'splits': [{'user_id': self.alice.id, 'amount_cents': 90}]},
            format='json', **auth(self.alice),
        )
        self.assertEqual(res.status_code, 400)

    def test_non_member_cannot_add_members(self):
        res = self.client.post(
            f'/api/groups/{self.group.id}/members/',
            {'username': 'mallory'}, format='json', **auth(self.mallory),
        )
        self.assertIn(res.status_code, (403, 404))
        self.assertEqual(self.group.memberships.count(), 2)

    def test_creator_can_add_member(self):
        res = self.client.post(
            f'/api/groups/{self.group.id}/members/',
            {'username': 'mallory'}, format='json', **auth(self.alice),
        )
        self.assertEqual(res.status_code, 201)
        self.assertEqual(self.group.memberships.count(), 3)

    def test_split_target_must_be_group_member(self):
        # Mallory is NOT a member here (only alice+bob are); even though the
        # request is authenticated as alice, splitting to mallory is rejected.
        res = self.client.post(
            f'/api/groups/{self.group.id}/',
            {'description': 'X', 'amount_cents': 100,
             'splits': [{'user_id': self.mallory.id, 'amount_cents': 100}]},
            format='json', **auth(self.alice),
        )
        self.assertEqual(res.status_code, 400)

    def test_paid_by_defaults_to_authenticated_user(self):
        # No paid_by in the payload -> the caller is the payer.
        res = self.client.post(
            f'/api/groups/{self.group.id}/',
            {'description': 'X', 'amount_cents': 100},
            format='json', **auth(self.bob),
        )
        self.assertEqual(res.status_code, 201)
        e = Expense.objects.first()
        self.assertEqual(e.paid_by, self.bob)

    def test_paid_by_can_be_another_member(self):
        # A member may record an expense paid by someone else IN the group
        # (Splitwise-style), e.g. "B paid 500" while A is logged in.
        res = self.client.post(
            f'/api/groups/{self.group.id}/',
            {'description': 'B paid this', 'amount_cents': 50000,
             'paid_by': 'bob'},
            format='json', **auth(self.alice),
        )
        self.assertEqual(res.status_code, 201)
        e = Expense.objects.first()
        self.assertEqual(e.paid_by, self.bob)

    def test_paid_by_must_be_a_member(self):
        # The payer resolves server-side to a member of this group; a
        # non-member (or unknown) username is rejected.
        res = self.client.post(
            f'/api/groups/{self.group.id}/',
            {'description': 'X', 'amount_cents': 100, 'paid_by': 'mallory'},
            format='json', **auth(self.alice),
        )
        self.assertEqual(res.status_code, 400)
        res = self.client.post(
            f'/api/groups/{self.group.id}/',
            {'description': 'X', 'amount_cents': 100, 'paid_by': 'ghost'},
            format='json', **auth(self.alice),
        )
        self.assertEqual(res.status_code, 400)
        self.assertEqual(Expense.objects.count(), 0)

    def test_balances_endpoint(self):
        # alice pays 100, split equally -> alice +50, bob -50
        self.client.post(
            f'/api/groups/{self.group.id}/',
            {'description': 'X', 'amount_cents': 100},
            format='json', **auth(self.alice),
        )
        res = self.client.get(f'/api/groups/{self.group.id}/', **auth(self.alice))
        balances = {b['username']: b['balance_cents'] for b in res.json()['balances']}
        self.assertEqual(balances, {'alice': 50, 'bob': -50})

    def test_group_detail_flags_creator(self):
        res = self.client.get(f'/api/groups/{self.group.id}/', **auth(self.alice))
        self.assertTrue(res.json()['is_creator'])
        self.assertEqual(res.json()['created_by'], 'alice')
        res = self.client.get(f'/api/groups/{self.group.id}/', **auth(self.bob))
        self.assertFalse(res.json()['is_creator'])

    def test_search_users(self):
        res = self.client.get('/api/users/?q=ali', **auth(self.bob))
        self.assertEqual([u['username'] for u in res.json()], ['alice'])

    def test_search_users_requires_auth(self):
        self.assertEqual(self.client.get('/api/users/?q=ali').status_code, 401)
