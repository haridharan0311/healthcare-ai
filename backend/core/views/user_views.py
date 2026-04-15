from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        profile = getattr(user, 'profile', None)
        
        return Response({
            'username': user.username,
            'email': user.email,
            'role': profile.role if profile else 'UNKNOWN',
            'clinic_id': profile.clinic.id if profile and profile.clinic else None,
            'clinic_name': profile.clinic.clinic_name if profile and profile.clinic else 'All Clinics'
        })
