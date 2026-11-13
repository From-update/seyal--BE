from django.urls import path
from .views import (
    PageListCreateView, PageDetailView, PageBlocksView,
    BlockBatchUpdateView, BlockDetailView,
    DatabaseListCreateView, DatabaseDetailView,
    DatabaseRowsView, DatabaseRowDetailView,
    DatabaseViewsView
)

urlpatterns = [
    path('pages', PageListCreateView.as_view(), name='pages_list_create'),
    path('pages/<uuid:pk>', PageDetailView.as_view(), name='page_detail'),
    path('pages/<uuid:pk>/blocks', PageBlocksView.as_view(), name='page_blocks'),
    path('pages/<uuid:pk>/blocks/batch', BlockBatchUpdateView.as_view(), name='block_batch_update'),
    path('blocks/<uuid:pk>', BlockDetailView.as_view(), name='block_detail'),
    path('databases', DatabaseListCreateView.as_view(), name='databases_list_create'),
    path('databases/<uuid:pk>', DatabaseDetailView.as_view(), name='database_detail'),
    path('databases/<uuid:pk>/rows', DatabaseRowsView.as_view(), name='database_rows'),
    path('rows/<uuid:pk>', DatabaseRowDetailView.as_view(), name='database_row_detail'),
    path('databases/<uuid:pk>/views', DatabaseViewsView.as_view(), name='database_views'),
]

