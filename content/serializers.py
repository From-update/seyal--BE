from rest_framework import serializers
from .models import Page, Block, Database, DatabaseRow, DatabaseView
from accounts.serializers import UserSerializer

class BlockSerializer(serializers.ModelSerializer):
    class Meta:
        model = Block
        fields = ['id', 'page', 'parent_block', 'type', 'content', 'position', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

class PageSerializer(serializers.ModelSerializer):
    created_by = UserSerializer(read_only=True)
    subpages_count = serializers.SerializerMethodField()

    class Meta:
        model = Page
        fields = [
            'id', 'workspace', 'parent_page', 'title', 'icon', 'cover',
            'created_by', 'is_archived', 'is_favorite', 'subpages_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_by', 'created_at', 'updated_at']

    def get_subpages_count(self, obj):
        return obj.subpages.filter(is_archived=False).count()

class PageDetailSerializer(PageSerializer):
    blocks = serializers.SerializerMethodField()

    class Meta(PageSerializer.Meta):
        fields = PageSerializer.Meta.fields + ['blocks']

    def get_blocks(self, obj):
        return BlockSerializer(obj.blocks.all().order_by('position'), many=True).data

class DatabaseRowSerializer(serializers.ModelSerializer):
    created_by = UserSerializer(read_only=True)

    class Meta:
        model = DatabaseRow
        fields = ['id', 'database', 'properties', 'created_by', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_by', 'created_at', 'updated_at', 'database']

class DatabaseViewSerializer(serializers.ModelSerializer):
    class Meta:
        model = DatabaseView
        fields = ['id', 'database', 'name', 'type', 'filters', 'sorts', 'group_by', 'created_at']
        read_only_fields = ['id', 'created_at', 'database']

class DatabaseSerializer(serializers.ModelSerializer):
    views = DatabaseViewSerializer(many=True, read_only=True)
    rows_count = serializers.SerializerMethodField()

    class Meta:
        model = Database
        fields = ['id', 'workspace', 'page', 'name', 'schema', 'views', 'rows_count', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_rows_count(self, obj):
        return obj.rows.count()

