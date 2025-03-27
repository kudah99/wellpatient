from import_export import resources, fields
from import_export.widgets import ForeignKeyWidget
from .models import Patient, Location


class PatientResource(resources.ModelResource):
    """
    Resource class for Patient model to enable import/export functionality
    """
    location = fields.Field(
        column_name='location',
        attribute='location',
        widget=ForeignKeyWidget(Location, 'name')
    )
    
    class Meta:
        model = Patient
        import_id_fields = ('phone_number',)
        export_order = (
            'id', 'first_name', 'last_name', 'gender', 'date_of_birth',
            'phone_number', 'email', 'location', 'address',
            'notification_preference', 'is_active'
        )
        fields = (
            'id', 'first_name', 'last_name', 'gender', 'date_of_birth',
            'phone_number', 'email', 'location', 'address',
            'notification_preference', 'is_active', 'created_at', 'updated_at'
        )
        skip_unchanged = True
        report_skipped = True
