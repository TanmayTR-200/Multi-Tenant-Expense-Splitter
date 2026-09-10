import hashlib
import hmac

from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.db import transaction
from rest_framework import permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from .balance import compute_user_balances
from .models import Group, Membership
from .serializers import ExpenseSerializer, GroupSerializer, RegisterSerializer


class LoginView(TokenObtainPairView):
    """JWT login (username + password -> access & refresh tokens)."""


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def register(request):
    ser = RegisterSerializer(data=request.data)
    ser.is_valid(raise_exception=True)
    data = ser.validated_data
    if User.objects.filter(username=data['username']).exists():
        return Response({'detail': 'username taken'}, status=400)
    user = User.objects.create_user(
        username=data['username'], email=data['email'], password=data['password']
    )
    refresh = RefreshToken.for_user(user)
    return Response(
        {'access': str(refresh.access_token), 'refresh': str(refresh)},
        status=status.HTTP_201_CREATED,
    )


def _user_groups(user):
    """TENANT ISOLATION: a user's groups are derived only from their
    Membership rows — a group id sent by the client can never widen this."""
    return Group.objects.filter(memberships__user=user)


@api_view(['GET', 'POST'])
@permission_classes([permissions.IsAuthenticated])
def groups(request):
    if request.method == 'GET':
        ser = GroupSerializer(_user_groups(request.user).distinct(), many=True,
                              context={'request': request})
        return Response(ser.data)

    name = (request.data.get('name') or '').strip()
    if not name:
        return Response({'detail': 'name is required'}, status=400)
    with transaction.atomic():
        group = Group.objects.create(name=name, created_by=request.user)
        Membership.objects.create(group=group, user=request.user)
    return Response(GroupSerializer(group, context={'request': request}).data, status=201)


def _get_group_or_403(request, group_id):
    """Only return the group if the *authenticated* user is a member."""
    group = _user_groups(request.user).filter(id=group_id).first()
    if group is None:
        return None
    return group


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def add_member(request, group_id):
    """Add an existing user to a group. Only the group creator may do this."""
    group = _get_group_or_403(request, group_id)
    if group is None:
        return Response({'detail': 'not found'}, status=404)
    if group.created_by_id != request.user.id:
        return Response({'detail': 'only the group creator can add members'}, status=403)

    username = (request.data.get('username') or '').strip()
    user = User.objects.filter(username=username).first()
    if user is None:
        return Response({'detail': 'no such user'}, status=400)
    membership, created = Membership.objects.get_or_create(group=group, user=user)
    if not created:
        return Response({'detail': 'already a member'}, status=400)
    return Response({'id': user.id, 'username': user.username}, status=201)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def search_users(request):
    """Look up registered users by username prefix (to add as members).
    Returns at most 10 matches; only active usernames are exposed."""
    q = (request.query_params.get('q') or '').strip()
    if not q:
        return Response([])
    users = User.objects.filter(username__istartswith=q, is_active=True)[:10]
    return Response([{'id': u.id, 'username': u.username} for u in users])


@api_view(['GET', 'POST'])
@permission_classes([permissions.IsAuthenticated])
def group_detail(request, group_id):
    group = _get_group_or_403(request, group_id)
    if group is None:
        return Response({'detail': 'not found'}, status=404)

    if request.method == 'GET':
        ser = GroupSerializer(group, context={'request': request})
        balances = compute_user_balances(group)
        members = {m.user_id: m.user.username for m in group.memberships.select_related('user')}
        expenses = [
            {
                'id': e.id,
                'description': e.description,
                'amount_cents': e.amount_cents,
                'paid_by': {'id': e.paid_by_id, 'username': e.paid_by.username},
                'splits': [
                    {'user_id': s.user_id, 'username': members.get(s.user_id, '?'),
                     'amount_cents': s.amount_cents}
                    for s in e.splits.all()
                ],
            }
            for e in group.expenses.select_related('paid_by').prefetch_related('splits')
        ]
        return Response({
            'id': group.id, 'name': group.name, 'members': ser.get_members(group),
            'your_balance_cents': ser.get_your_balance_cents(group),
            'is_creator': group.created_by_id == request.user.id,
            'created_by': group.created_by.username,
            'balances': [
                {'user_id': uid, 'username': members.get(uid, '?'), 'balance_cents': bal}
                for uid, bal in balances.items()
            ],
            'expenses': expenses,
        })

    # POST: add expense. paid_by is always the authenticated user.
    ser = ExpenseSerializer(data=request.data, context={'group': group, 'request': request})
    ser.is_valid(raise_exception=True)
    expense = ser.save()
    return Response({'id': expense.id}, status=201)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def internal_group_data(request, group_id):
    """Endpoint the settlement service calls: /api/groups/<id>/settlement-data/

    Double auth:
      1. X-Internal-Token identifies this call as coming from the settlement
         service (sha256 of SECRET_KEY-derived shared secret).
      2. The caller's normal JWT is still required, and membership is
         re-checked — the settlement service forwards the end user's token
         so tenant isolation is enforced even on internal routes.
    """
    token = request.headers.get('X-Internal-Token', '')
    if not token or not hmac.compare_digest(token, settings.INTERNAL_SERVICE_TOKEN):
        return Response({'detail': 'forbidden'}, status=403)

    # TENANT ISOLATION: only serve group data if the JWT-authenticated user
    # is a member of that group.
    group = _get_group_or_403(request, group_id)
    if group is None:
        return Response({'detail': 'not found'}, status=404)

    members = {m.user_id: m.user.username for m in group.memberships.select_related('user')}
    balances = compute_user_balances(group)
    return Response({
        'group_id': group.id,
        'name': group.name,
        'members': [
            {'user_id': uid, 'username': name, 'balance_cents': balances.get(uid, 0)}
            for uid, name in members.items()
        ],
    })
