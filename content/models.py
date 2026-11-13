import uuid
from django.db import models
from django.conf import settings
from workspaces.models import Workspace

class Page(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name='pages')
    parent_page = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='subpages')
    title = models.CharField(max_length=255, default='Untitled')
    icon = models.CharField(max_length=64, blank=True, default='📄')
    cover = models.TextField(blank=True, default='')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='created_pages')
    is_archived = models.BooleanField(default=False)
    is_favorite = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.icon} {self.title}"

class Block(models.Model):
    BLOCK_TYPES = [
        ('paragraph', 'Paragraph'),
        ('heading1', 'Heading 1'),
        ('heading2', 'Heading 2'),
        ('heading3', 'Heading 3'),
        ('bullet_list', 'Bullet List'),
        ('numbered_list', 'Numbered List'),
        ('checklist', 'Checklist'),
        ('quote', 'Quote'),
        ('code', 'Code'),
        ('toggle', 'Toggle'),
        ('callout', 'Callout'),
        ('divider', 'Divider'),
        ('table', 'Table'),
        ('image', 'Image'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    page = models.ForeignKey(Page, on_delete=models.CASCADE, related_name='blocks')
    parent_block = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')
    type = models.CharField(max_length=30, choices=BLOCK_TYPES, default='paragraph')
    content = models.JSONField(default=dict, blank=True)
    position = models.FloatField(default=1.0, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['position', 'created_at']

    def __str__(self):
        return f"{self.type} block in {self.page_id} (pos: {self.position})"

class Database(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name='databases')
    page = models.ForeignKey(Page, on_delete=models.SET_NULL, null=True, blank=True, related_name='databases')
    name = models.CharField(max_length=150, default='New Database')
    # schema defines columns e.g.:
    # [{"id": "col_1", "name": "Name", "type": "title"}, {"id": "col_2", "name": "Status", "type": "select", "options": ["Not Started", "In Progress", "Done"]}]
    schema = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class DatabaseRow(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    database = models.ForeignKey(Database, on_delete=models.CASCADE, related_name='rows')
    # properties store column values by column id, e.g. {"col_1": "Item 1", "col_2": "In Progress"}
    properties = models.JSONField(default=dict, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

class DatabaseView(models.Model):
    VIEW_TYPES = [
        ('table', 'Table'),
        ('board', 'Board'),
        ('calendar', 'Calendar'),
        ('list', 'List'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    database = models.ForeignKey(Database, on_delete=models.CASCADE, related_name='views')
    name = models.CharField(max_length=100, default='Table View')
    type = models.CharField(max_length=20, choices=VIEW_TYPES, default='table')
    filters = models.JSONField(default=list, blank=True)
    sorts = models.JSONField(default=list, blank=True)
    group_by = models.CharField(max_length=100, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.database.name} - {self.name} ({self.type})"

