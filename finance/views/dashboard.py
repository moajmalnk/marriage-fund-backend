from rest_framework import views, permissions, viewsets
from rest_framework.response import Response
from rest_framework.decorators import action
from django.db.models import Sum, Q, Prefetch, DecimalField, OuterRef, Subquery, Count
from django.db.models.functions import Coalesce
from django.utils import timezone
from finance.models import Payment, Notification
from users.models import User
from finance.serializers import NotificationSerializer

# --- CONFIGURATION ---
CONTRIBUTION_PER_MARRIAGE = 5000.0  # Amount per member per marriage

# Helper to calculate the TARGET FOR ONE PERSON (Total Members * 5000)
# Example: If 7 members, one person's target is 35,000
def calculate_individual_target():
    total_users = User.objects.count()
    admin_count = User.objects.filter(role='admin').count()
    non_admin_users = total_users - admin_count
    if non_admin_users <= 0:
        non_admin_users = 1
    return non_admin_users * CONTRIBUTION_PER_MARRIAGE

class DashboardStatsView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        today = timezone.now().date()

        # 1. Financials
        total_collected = Payment.objects.filter(transaction_type='COLLECT').aggregate(sum=Sum('amount'))['sum'] or 0
        total_disbursed = Payment.objects.filter(
            transaction_type='DISBURSE',
            date__lte=today 
        ).aggregate(sum=Sum('amount'))['sum'] or 0
        
        balance = total_collected - total_disbursed
        
        # 2. Demographics
        married_count = User.objects.filter(marital_status='Married').exclude(role='admin').count()
        unmarried_count = User.objects.filter(marital_status='Unmarried').exclude(role='admin').count()

        # 3. Team Rankings
        # Get the target for a SINGLE person (e.g., 35,000)
        individual_target = calculate_individual_target()
        
        # Subquery to get sum of payments for team members
        team_payments_subquery = Payment.objects.filter(
            user__responsible_member=OuterRef('pk'),
            transaction_type='COLLECT'
        ).values('user__responsible_member').annotate(
            total=Sum('amount')
        ).values('total')

        leaders = User.objects.filter(role='responsible_member').annotate(
            member_count=Count('assigned_members'),
            personal_paid=Coalesce(
                Sum('payments__amount', filter=Q(payments__transaction_type='COLLECT')), 
                0.0, 
                output_field=DecimalField()
            ),
            team_members_paid=Coalesce(
                Subquery(team_payments_subquery),
                0.0,
                output_field=DecimalField()
            )
        )

        team_rankings = []
        for leader in leaders:
            total_team_paid = float(leader.personal_paid) + float(leader.team_members_paid)
            total_members = leader.member_count + 1 # Leader + members
            
            # FIX: Team Target = (Team Members) * (Individual Target)
            # Example: 4 members * 35,000 = 140,000
            team_target = total_members * individual_target
            
            team_rankings.append({
                'leader_name': leader.get_full_name() or leader.username,
                'member_count': total_members,
                'total_paid': total_team_paid,
                'target': team_target, 
                'progress': (total_team_paid / team_target * 100) if team_target > 0 else 0
            })

        team_rankings.sort(key=lambda x: x['total_paid'], reverse=True)

        # 4. Announcements
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
            'system_target': float(individual_target),
            'announcements': announcement_data
        })

class TeamStructureView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        # Calculate the default target for one person (e.g., 35,000)
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
                # FIX: Use default_individual_target (35,000) if assigned is 0
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
            
            # FIX: Leader uses same default target logic
            leader_target = float(leader.assigned_monthly_amount) if leader.assigned_monthly_amount > 0 else default_individual_target
            
            # Sum up Leader Target + All Member Targets
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
        
        if not title or not message:
            return Response({'error': 'Title and message are required.'}, status=400)
            
        create_wedding_announcement(request.user, title, message)
        return Response({'status': 'Announcement sent to all members'})