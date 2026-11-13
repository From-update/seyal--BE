from rest_framework import views, status, permissions
from rest_framework.response import Response
from .models import Page, Block, Database, DatabaseRow, DatabaseView
from .serializers import (
    PageSerializer, PageDetailSerializer, BlockSerializer,
    DatabaseSerializer, DatabaseRowSerializer, DatabaseViewSerializer
)
from workspaces.models import Workspace
from common.utils import get_fractional_position

class PageListCreateView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        workspace_id = request.query_params.get('workspace_id')
        if not workspace_id:
            return Response({'error': 'workspace_id query parameter required'}, status=status.HTTP_400_BAD_REQUEST)

        parent_id = request.query_params.get('parent_page_id')
        is_favorite = request.query_params.get('is_favorite')

        queryset = Page.objects.filter(workspace_id=workspace_id, is_archived=False)
        if parent_id == 'root':
            queryset = queryset.filter(parent_page__isnull=True)
        elif parent_id:
            queryset = queryset.filter(parent_page_id=parent_id)

        if is_favorite == 'true':
            queryset = queryset.filter(is_favorite=True)

        return Response(PageSerializer(queryset.order_by('-updated_at'), many=True).data)

    def post(self, request):
        workspace_id = request.data.get('workspace_id')
        workspace = Workspace.objects.filter(id=workspace_id).first()
        if not workspace:
            return Response({'error': 'Workspace not found'}, status=status.HTTP_404_NOT_FOUND)

        page = Page.objects.create(
            workspace=workspace,
            parent_page_id=request.data.get('parent_page_id'),
            title=request.data.get('title', 'Untitled'),
            icon=request.data.get('icon', '📄'),
            cover=request.data.get('cover', ''),
            created_by=request.user
        )

        # Create initial empty paragraph block
        Block.objects.create(
            page=page,
            type='paragraph',
            content={'text': ''},
            position=1.0
        )

        return Response(PageDetailSerializer(page).data, status=status.HTTP_201_CREATED)

class PageDetailView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        page = Page.objects.filter(id=pk).first()
        if not page:
            return Response({'error': 'Page not found'}, status=status.HTTP_404_NOT_FOUND)
        return Response(PageDetailSerializer(page).data)

    def patch(self, request, pk):
        page = Page.objects.filter(id=pk).first()
        if not page:
            return Response({'error': 'Page not found'}, status=status.HTTP_404_NOT_FOUND)

        serializer = PageSerializer(page, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, pk):
        page = Page.objects.filter(id=pk).first()
        if not page:
            return Response({'error': 'Page not found'}, status=status.HTTP_404_NOT_FOUND)
        page.is_archived = True
        page.save(update_fields=['is_archived'])
        return Response({'message': 'Page archived'})

class PageBlocksView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        blocks = Block.objects.filter(page_id=pk).order_by('position')
        return Response(BlockSerializer(blocks, many=True).data)

    def post(self, request, pk):
        page = Page.objects.filter(id=pk).first()
        if not page:
            return Response({'error': 'Page not found'}, status=status.HTTP_404_NOT_FOUND)

        prev_pos = request.data.get('prev_pos')
        next_pos = request.data.get('next_pos')
        if prev_pos is not None or next_pos is not None:
            position = get_fractional_position(prev_pos, next_pos)
        else:
            last_block = Block.objects.filter(page=page).order_by('-position').first()
            position = (last_block.position + 1.0) if last_block else 1.0

        block = Block.objects.create(
            page=page,
            parent_block_id=request.data.get('parent_block_id'),
            type=request.data.get('type', 'paragraph'),
            content=request.data.get('content', {}),
            position=position
        )
        return Response(BlockSerializer(block).data, status=status.HTTP_201_CREATED)

class BlockBatchUpdateView(views.APIView):
    """
    Batch update/reorder blocks in a page efficiently.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        blocks_data = request.data.get('blocks', [])
        page = Page.objects.filter(id=pk).first()
        if not page:
            return Response({'error': 'Page not found'}, status=status.HTTP_404_NOT_FOUND)

        updated_blocks = []
        for item in blocks_data:
            block_id = item.get('id')
            if not block_id:
                # Create block
                block = Block.objects.create(
                    page=page,
                    type=item.get('type', 'paragraph'),
                    content=item.get('content', {}),
                    position=item.get('position', 1.0)
                )
                updated_blocks.append(block)
            else:
                block = Block.objects.filter(id=block_id, page=page).first()
                if block:
                    if 'type' in item:
                        block.type = item['type']
                    if 'content' in item:
                        block.content = item['content']
                    if 'position' in item:
                        block.position = item['position']
                    block.save()
                    updated_blocks.append(block)

        return Response(BlockSerializer(updated_blocks, many=True).data)

class BlockDetailView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, pk):
        block = Block.objects.filter(id=pk).first()
        if not block:
            return Response({'error': 'Block not found'}, status=status.HTTP_404_NOT_FOUND)

        serializer = BlockSerializer(block, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, pk):
        block = Block.objects.filter(id=pk).first()
        if not block:
            return Response({'error': 'Block not found'}, status=status.HTTP_404_NOT_FOUND)
        block.delete()
        return Response({'message': 'Block deleted'})

class DatabaseListCreateView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        workspace_id = request.query_params.get('workspace_id')
        if not workspace_id:
            return Response({'error': 'workspace_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        databases = Database.objects.filter(workspace_id=workspace_id).prefetch_related('views')
        return Response(DatabaseSerializer(databases, many=True).data)

    def post(self, request):
        workspace_id = request.data.get('workspace_id')
        workspace = Workspace.objects.filter(id=workspace_id).first()
        if not workspace:
            return Response({'error': 'Workspace not found'}, status=status.HTTP_404_NOT_FOUND)

        default_schema = [
            {"id": "name", "name": "Name", "type": "title"},
            {"id": "status", "name": "Status", "type": "select", "options": ["Not Started", "In Progress", "Done"]},
            {"id": "priority", "name": "Priority", "type": "select", "options": ["Low", "Medium", "High"]},
            {"id": "assignee", "name": "Assignee", "type": "person"},
            {"id": "due_date", "name": "Due Date", "type": "date"},
        ]

        database = Database.objects.create(
            workspace=workspace,
            page_id=request.data.get('page_id'),
            name=request.data.get('name', 'Tasks & Projects'),
            schema=request.data.get('schema', default_schema)
        )

        # Create Table and Board views
        DatabaseView.objects.create(database=database, name='Table View', type='table')
        DatabaseView.objects.create(database=database, name='Kanban Board', type='board', group_by='status')

        return Response(DatabaseSerializer(database).data, status=status.HTTP_201_CREATED)

class DatabaseDetailView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        database = Database.objects.filter(id=pk).prefetch_related('views', 'rows').first()
        if not database:
            return Response({'error': 'Database not found'}, status=status.HTTP_404_NOT_FOUND)
        return Response(DatabaseSerializer(database).data)

    def patch(self, request, pk):
        database = Database.objects.filter(id=pk).first()
        if not database:
            return Response({'error': 'Database not found'}, status=status.HTTP_404_NOT_FOUND)

        serializer = DatabaseSerializer(database, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, pk):
        database = Database.objects.filter(id=pk).first()
        if not database:
            return Response({'error': 'Database not found'}, status=status.HTTP_404_NOT_FOUND)
        database.delete()
        return Response({'message': 'Database deleted'})

class DatabaseRowsView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        rows = DatabaseRow.objects.filter(database_id=pk).order_by('-created_at')
        return Response(DatabaseRowSerializer(rows, many=True).data)

    def post(self, request, pk):
        database = Database.objects.filter(id=pk).first()
        if not database:
            return Response({'error': 'Database not found'}, status=status.HTTP_404_NOT_FOUND)

        row = DatabaseRow.objects.create(
            database=database,
            properties=request.data.get('properties', {}),
            created_by=request.user
        )
        return Response(DatabaseRowSerializer(row).data, status=status.HTTP_201_CREATED)

class DatabaseRowDetailView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, pk):
        row = DatabaseRow.objects.filter(id=pk).first()
        if not row:
            return Response({'error': 'Row not found'}, status=status.HTTP_404_NOT_FOUND)

        if 'properties' in request.data:
            row.properties.update(request.data['properties'])
            row.save()
        return Response(DatabaseRowSerializer(row).data)

    def delete(self, request, pk):
        row = DatabaseRow.objects.filter(id=pk).first()
        if not row:
            return Response({'error': 'Row not found'}, status=status.HTTP_404_NOT_FOUND)
        row.delete()
        return Response({'message': 'Row deleted'})

class DatabaseViewsView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        views_qs = DatabaseView.objects.filter(database_id=pk)
        return Response(DatabaseViewSerializer(views_qs, many=True).data)

    def post(self, request, pk):
        database = Database.objects.filter(id=pk).first()
        if not database:
            return Response({'error': 'Database not found'}, status=status.HTTP_404_NOT_FOUND)

        view = DatabaseView.objects.create(
            database=database,
            name=request.data.get('name', 'New View'),
            type=request.data.get('type', 'table'),
            filters=request.data.get('filters', []),
            sorts=request.data.get('sorts', []),
            group_by=request.data.get('group_by', '')
        )
        return Response(DatabaseViewSerializer(view).data, status=status.HTTP_201_CREATED)

