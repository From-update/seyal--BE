import uuid
from django.db import models
from django.conf import settings
from django.utils.text import slugify

class Organisation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True)
    logo_url = models.TextField(blank=True, default="")
    email = models.EmailField(blank=True, default="")
    phone = models.CharField(max_length=40, blank=True, default="")
    address = models.TextField(blank=True, default="")
    industry = models.CharField(max_length=100, blank=True, default="")
    registration_number = models.CharField(max_length=100, blank=True, default="")
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='owned_organisations')
    subscription_plan = models.CharField(max_length=50, default='free')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name) or "org"
            self.slug = f"{base_slug}-{str(uuid.uuid4())[:8]}"
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

class Workspace(models.Model):
    TYPE_CHOICES = [
        ('personal', 'Personal'),
        ('team', 'Team'),
        ('organization', 'Organization'),
    ]

    SUBDIVISION_CHOICES = [
        ('organisation', 'Organisation'),
        ('personal', 'Personal'),
        ('freelancer', 'Freelancer'),
        ('customize', 'Customize'),
    ]

    PLAN_CHOICES = [
        ('free', 'Free'),
        ('pro', 'Pro'),
        ('business', 'Business'),
        ('enterprise', 'Enterprise'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organisation = models.ForeignKey(Organisation, on_delete=models.CASCADE, null=True, blank=True, related_name='workspaces')
    subdivision = models.CharField(max_length=30, choices=SUBDIVISION_CHOICES, default='personal')
    name = models.CharField(max_length=150)
    slug = models.SlugField(max_length=160, db_index=True)
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='team')
    plan = models.CharField(max_length=20, choices=PLAN_CHOICES, default='free')
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='owned_workspaces')
    settings = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['owner'],
                condition=models.Q(type='personal'),
                name='unique_personal_workspace_per_owner'
            )
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name) or "workspace"
            self.slug = f"{base_slug}-{str(uuid.uuid4())[:8]}"
        # Sync subdivision based on type if default
        if self.type == 'personal' and self.subdivision == 'personal':
            self.subdivision = 'personal'
        elif self.type in ['team', 'organization'] and self.subdivision == 'personal':
            self.subdivision = 'organisation'
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.type})"

class Department(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name='departments')
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True, default="")
    parent = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='sub_departments')
    manager = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='managed_departments')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.workspace.name} -> {self.name}"

class WorkspaceMember(models.Model):
    ROLE_CHOICES = [
        # Enterprise Organisation Hierarchy
        ('org_superadmin', 'Organisation Super Admin (Owner)'),
        ('org_admin', 'Organisation Admin'),
        ('lead_manager', 'Lead Manager'),
        ('department_manager', 'Department Manager'),
        ('project_manager', 'Project Manager'),
        ('hr_manager', 'HR Manager'),
        ('finance_manager', 'Finance Manager'),
        ('staff', 'Staff'),
        ('intern', 'Intern'),
        # General / Workspace roles
        ('owner', 'Owner'),
        ('admin', 'Admin'),
        ('manager', 'Manager'),
        ('member', 'Member'),
        ('guest', 'Guest'),
    ]

    STATUS_CHOICES = [
        ('active', 'Active'),
        ('invited', 'Invited'),
        ('deactivated', 'Deactivated'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name='memberships')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='workspace_memberships')
    role = models.CharField(max_length=40, choices=ROLE_CHOICES, default='member')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    employee_id = models.CharField(max_length=50, blank=True, default="")
    designation = models.CharField(max_length=100, blank=True, default="")
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_workspace_members')
    reporting_manager = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='reporting_subordinates')
    joining_date = models.DateField(null=True, blank=True)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('workspace', 'user')

    def __str__(self):
        return f"{self.user} - {self.workspace.name} ({self.role})"

class DepartmentMember(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='members')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='department_memberships')
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('department', 'user')

class Project(models.Model):
    ONBOARDING_STATUS_CHOICES = [
        ('onboarded', 'Onboarded'),
        ('unboarded', 'Unboarded'),
    ]

    LIFECYCLE_STATUS_CHOICES = [
        ('ongoing', 'Ongoing'),
        ('completed', 'Completed'),
        ('on_hold', 'On Hold'),
        ('archived', 'Archived'),
    ]

    PRIORITY_CHOICES = [
        ('urgent', 'Urgent'),
        ('high', 'High'),
        ('medium', 'Medium'),
        ('low', 'Low'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organisation = models.ForeignKey(Organisation, on_delete=models.CASCADE, null=True, blank=True, related_name='projects')
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name='projects')
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, related_name='projects')
    project_id_code = models.CharField(max_length=50, blank=True, default="")
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, default="")
    project_manager = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='managed_projects')
    onboarding_status = models.CharField(max_length=20, choices=ONBOARDING_STATUS_CHOICES, default='unboarded')
    lifecycle_status = models.CharField(max_length=20, choices=LIFECYCLE_STATUS_CHOICES, default='ongoing')
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='medium')
    start_date = models.DateField(null=True, blank=True)
    expected_completion_date = models.DateField(null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='created_projects')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} [{self.lifecycle_status}]"

class ProjectMember(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='members')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='project_memberships')
    role = models.CharField(max_length=50, default='contributor')
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('project', 'user')

class WorkspaceInvite(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name='invites')
    email_or_phone = models.CharField(max_length=150)
    role = models.CharField(max_length=40, default='member')
    token = models.CharField(max_length=100, unique=True, default=uuid.uuid4)
    expires_at = models.DateTimeField()
    accepted_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def is_valid(self):
        from django.utils import timezone
        return self.accepted_at is None and timezone.now() <= self.expires_at
