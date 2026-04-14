from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from ..utils.live_data_generator import _generator, start_live_data_generator, stop_live_data_generator

class LiveDataToggleView(APIView):
    """
    API endpoint to control the live data simulator.
    """
    def get(self, request):
        return Response(_generator.get_status())

    def post(self, request):
        action = request.data.get('action')
        interval = request.data.get('interval')
        
        try:
            if action == 'start':
                # Convert interval to int and validate
                if interval:
                    interval = int(interval)
                    if interval not in [5, 10, 30, 60, 90, 120]:
                        return Response({'error': 'Invalid interval'}, status=status.HTTP_400_BAD_REQUEST)
                
                # Start or update interval
                _generator.start(interval=interval)
                return Response(_generator.get_status())
            
            elif action == 'stop':
                _generator.stop()
                return Response(_generator.get_status())
            
            elif action == 'update_interval':
                if interval:
                    _generator.interval = int(interval)
                    return Response(_generator.get_status())
                return Response({'error': 'Interval required'}, status=status.HTTP_400_BAD_REQUEST)
                
            else:
                return Response({'error': 'Invalid action'}, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
