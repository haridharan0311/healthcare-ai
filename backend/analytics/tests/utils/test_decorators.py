from django.test import TestCase
from django.core.cache import cache
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.test import APIRequestFactory
from analytics.utils.decorators import cache_api_response, monitor_performance, limit_queries

class MockView(APIView):
    @cache_api_response(timeout=10)
    def get(self, request):
        return Response({"data": "computed"})

class DecoratorsTestCase(TestCase):
    """Tests for optimization decorators."""

    def setUp(self):
        cache.clear()
        self.factory = APIRequestFactory()

    def test_cache_api_response_decorator(self):
        view = MockView.as_view()
        request = self.factory.get('/?q=1')
        
        # First call: MISS
        response1 = view(request)
        self.assertEqual(response1.status_code, 200)
        self.assertEqual(response1['X-Cache'], 'MISS')
        
        # Second call: HIT
        response2 = view(request)
        self.assertEqual(response2['X-Cache'], 'HIT')
        self.assertEqual(response2.data, {"data": "computed"})
        
        # Different params: MISS
        request_new = self.factory.get('/?q=2')
        response3 = view(request_new)
        self.assertEqual(response3['X-Cache'], 'MISS')

    def test_performance_monitor_header(self):
        @monitor_performance(threshold_ms=100)
        def timed_view(request):
            return Response({"ok": True})
            
        request = self.factory.get('/')
        res = timed_view(request)
        self.assertIn('X-Response-Time-Ms', res)

    def test_query_limit_header(self):
        @limit_queries(max_queries=10)
        def low_query_view(request):
            from analytics.models import Disease
            list(Disease.objects.all()) # 1 query
            return Response({"ok": True})
            
        request = self.factory.get('/')
        res = low_query_view(request)
        self.assertIn('X-DB-Queries', res)
        self.assertEqual(int(res['X-DB-Queries']), 1)
