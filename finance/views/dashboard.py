from rest_framework import views, permissions, viewsets
from rest_framework.response import Response
from rest_framework.decorators import action
from django.db.models import Sum, Q, Prefetch, DecimalField, OuterRef, Subquery, Count, F
from django.db.models.functions import Coalesce
from django.utils import timezone
from finance.models import Payment, Notification
from users.models import User
from finance.serializers import NotificationSerializer

# --- CONFIGURATION ---
CONTRIBUTION_PER_MARRIAGE = 5000.0

def calculate_system_target():
    non_admin_users = User.objects.exclude(role='admin').count()
    if non_admin_users <= 1:
        return 0.0
    one_person_target = (non_admin_users - 1) * CONTRIBUTION_PER_MARRIAGE
    return one_person_target * non_admin_users

def calculate_individual_target():
    non_admin_users = User.objects.exclude(role='admin').count()
    if non_admin_users <= 1:
        return 0.0
    return (non_admin_users - 1) * CONTRIBUTION_PER_MARRIAGE

class DashboardStatsView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        today = timezone.now().date()

        # 1. Financials
        total_collected = Payment.objects.filter(transaction_type='COLLECT').aggregate(sum=Sum('amount'))['sum'] or 0
        total_disbursed = Payment.objects.filter(transaction_type='DISBURSE').aggregate(sum=Sum('amount'))['sum'] or 0
        balance = total_collected - total_disbursed
        
        # 2. Demographics
        married_count = User.objects.filter(marital_status='Married').exclude(role='admin').count()
        unmarried_count = User.objects.filter(marital_status='Unmarried').exclude(role='admin').count()

        # 3. Target
        system_target = calculate_system_target()
        individual_target = calculate_individual_target()
        
        # 4. Team Rankings (ROBUST PYTHON CALCULATION)
        # We perform aggregation in Python to ensure 100% accuracy in separating 
        # Leader payments from Downline payments, avoiding the double-counting bug.
        
        leaders = User.objects.filter(role='responsible_member')
        
        # Fetch all relevant payments in one optimized query
        all_payments = Payment.objects.filter(
            transaction_type='COLLECT'
        ).select_related('user')

        # Initialize data structure
        leader_stats = {}
        for leader in leaders:
            leader_stats[leader.id] = {
                'leader': leader,
                'personal_paid': 0.0,
                'team_members_paid': 0.0,
                'member_count': 0
            }

        # Calculate Member Counts (Excluding self-assignment)
        member_counts = User.objects.filter(
            responsible_member__isnull=False
        ).exclude(
            id=F('responsible_member__id') # Exclude leader self-assignment from count
        ).values('responsible_member').annotate(count=Count('id'))

        for entry in member_counts:
            lid = entry['responsible_member']
            if lid in leader_stats:
                leader_stats[lid]['member_count'] = entry['count']

        # Process Payments (The Fix)
        for payment in all_payments:
            amt = float(payment.amount)
            user_id = payment.user.id
            resp_id = payment.user.responsible_member_id

            # A. Is this the Leader's personal payment?
            if user_id in leader_stats:
                leader_stats[user_id]['personal_paid'] += amt
            
            # B. Is this a Team Member's payment?
            # Logic: Valid Responsible Member AND Payer is NOT the Responsible Member
            if resp_id and resp_id in leader_stats:
                if user_id != resp_id: # PREVENTS DOUBLE COUNTING
                    leader_stats[resp_id]['team_members_paid'] += amt

        # Build Final Response List
        team_rankings = []
        for lid, stats in leader_stats.items():
            leader = stats['leader']
            
            total_team_paid = stats['personal_paid'] + stats['team_members_paid']
            
            # Total Members = 1 (Leader) + Downline Count
            total_members_count = stats['member_count'] + 1
            
            # Team Target
            team_target = total_members_count * individual_target
            
            team_rankings.append({
                'leader_name': leader.get_full_name() or leader.username,
                'member_count': total_members_count,
                'total_paid': total_team_paid,
                'target': team_target, 
                'progress': (total_team_paid / team_target * 100) if team_target > 0 else 0
            })

        team_rankings.sort(key=lambda x: x['total_paid'], reverse=True)

        # 5. Announcements
        recent_announcements = Notification.objects.filter(
            user=request.user,
            notification_type__in=['WEDDING', 'ANNOUNCEMENT']
        ).order_by('-created_at')[:5]

        announcement_data = NotificationSerializer(recent_announcements, many=True).data

        return Response({
            'financials': {
                'balance': float(balance),
                'collected': float(total_collected),
                'disbursed': float(total_disbursed)
            },
            'demographics': {
                'married': married_count,
                'unmarried': unmarried_count
            },
            'teams': team_rankings,
            'system_target': float(system_target),
            'announcements': announcement_data
        })

class TeamStructureView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        default_individual_target = calculate_individual_target()
        
        leaders = User.objects.filter(role='responsible_member').annotate(
            personal_paid=Coalesce(
                Sum('payments__amount', filter=Q(payments__transaction_type='COLLECT')), 
                0.0, 
                output_field=DecimalField()
            )
        ).prefetch_related(
            Prefetch('assigned_members', queryset=User.objects.annotate(
                member_paid=Coalesce(
                    Sum('payments__amount', filter=Q(payments__transaction_type='COLLECT')), 
                    0.0, 
                    output_field=DecimalField()
                )
            ))
        )

        structure = []

        for leader in leaders:
            leader_paid = float(leader.personal_paid)
            members_data = []
            team_members_paid_sum = 0.0

            for member in leader.assigned_members.all():
                # Avoid counting the leader as a member in the sub-list if self-assigned
                if member.id == leader.id:
                    continue

                member_target = float(member.assigned_monthly_amount) if member.assigned_monthly_amount > 0 else default_individual_target
                paid = float(member.member_paid)
                team_members_paid_sum += paid
                
                members_data.append({
                    'id': member.id,
                    'name': member.get_full_name() or member.username,
                    'username': member.username,
                    'marital_status': member.marital_status,
                    'total_paid': paid,
                    'target': member_target,
                    'progress': (paid / member_target * 100) if member_target > 0 else 0
                })

            total_team_paid = leader_paid + team_members_paid_sum
            leader_target = float(leader.assigned_monthly_amount) if leader.assigned_monthly_amount > 0 else default_individual_target
            total_team_target = leader_target + sum(m['target'] for m in members_data)
            
            structure.append({
                'responsible_member': {
                    'id': leader.id,
                    'name': leader.get_full_name() or leader.username,
                    'marital_status': leader.marital_status,
                },
                'leaderTotalPaid': leader_paid,
                'leaderTotalTarget': leader_target,
                'teamMembersTotalPaid': team_members_paid_sum,
                'teamTotalPaid': total_team_paid,
                'teamTotalTarget': total_team_target,
                'teamTotalToCollect': max(0, total_team_target - total_team_paid),
                'teamProgress': (total_team_paid / total_team_target * 100) if total_team_target > 0 else 0,
                'members': members_data
            })

        structure.sort(key=lambda x: x['teamTotalPaid'], reverse=True)
        return Response(structure)

class NotificationViewSet(viewsets.ModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user).order_by('-created_at')

    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        notification = self.get_object()
        notification.is_read = True
        notification.save()
        return Response({'status': 'marked as read'})

    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        return Response({'status': 'all marked as read'})
    
    @action(detail=False, methods=['post'])
    def announce(self, request):
        from finance.services import create_wedding_announcement
        if request.user.role != 'admin':
            return Response({'error': 'Authorized personnel only.'}, status=403)
        title = request.data.get('title')
        message = request.data.get('message')
        priority = request.data.get('priority', 'HIGH') 
        if not title or not message:
            return Response({'error': 'Title and message are required.'}, status=400)
        create_wedding_announcement(request.user, title, message, priority)
        return Response({'status': 'Announcement sent to all members'})