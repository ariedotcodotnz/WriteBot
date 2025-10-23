"""
Database models for user authentication and activity tracking.
"""
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class User(UserMixin, db.Model):
    """User model for authentication and authorization."""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(150))
    role = db.Column(db.String(20), default='user', nullable=False)  # 'admin' or 'user'
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    last_login = db.Column(db.DateTime)

    # User settings
    default_style = db.Column(db.Integer, default=9)
    default_bias = db.Column(db.Float, default=0.75)
    default_stroke_color = db.Column(db.String(20), default='black')
    default_stroke_width = db.Column(db.Integer, default=2)

    # Relationships
    activities = db.relationship('UserActivity', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    statistics = db.relationship('UsageStatistics', backref='user', lazy='dynamic', cascade='all, delete-orphan')

    def set_password(self, password):
        """Hash and set the user's password."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Verify the user's password."""
        return check_password_hash(self.password_hash, password)

    def is_admin(self):
        """Check if user has admin role."""
        return self.role == 'admin'

    def update_last_login(self):
        """Update the last login timestamp."""
        self.last_login = datetime.utcnow()
        db.session.commit()

    def __repr__(self):
        return f'<User {self.username}>'


class UserActivity(db.Model):
    """Log of user activities for auditing."""
    __tablename__ = 'user_activities'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    activity_type = db.Column(db.String(50), nullable=False)  # 'login', 'logout', 'generate', 'batch', 'admin_action'
    description = db.Column(db.Text)
    ip_address = db.Column(db.String(45))  # Support both IPv4 and IPv6
    user_agent = db.Column(db.String(255))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Additional data (stored as JSON-compatible text)
    extra_data = db.Column(db.Text)  # Can store JSON string for extra data

    def __repr__(self):
        return f'<UserActivity {self.user_id}:{self.activity_type} at {self.timestamp}>'


class UsageStatistics(db.Model):
    """Usage statistics per user for generation tracking."""
    __tablename__ = 'usage_statistics'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    date = db.Column(db.Date, default=datetime.utcnow, nullable=False, index=True)

    # Generation counts
    svg_generations = db.Column(db.Integer, default=0)
    batch_generations = db.Column(db.Integer, default=0)
    total_lines_generated = db.Column(db.Integer, default=0)
    total_characters_generated = db.Column(db.Integer, default=0)

    # Processing time (in seconds)
    total_processing_time = db.Column(db.Float, default=0.0)

    # Last updated
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Unique constraint to ensure one record per user per day
    __table_args__ = (db.UniqueConstraint('user_id', 'date', name='_user_date_uc'),)

    def __repr__(self):
        return f'<UsageStatistics user_id={self.user_id} date={self.date}>'


class CharacterOverrideCollection(db.Model):
    """Collection of manual character overrides for handwriting generation."""
    __tablename__ = 'character_override_collections'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False, unique=True)
    description = db.Column(db.Text)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    # Relationships
    character_overrides = db.relationship('CharacterOverride', backref='collection', lazy='dynamic', cascade='all, delete-orphan')
    creator = db.relationship('User', backref='created_collections', foreign_keys=[created_by])

    def get_character_count(self):
        """Get the total number of character variants in this collection."""
        return self.character_overrides.count()

    def get_unique_characters(self):
        """Get a list of unique characters that have overrides in this collection."""
        return db.session.query(CharacterOverride.character).filter_by(collection_id=self.id).distinct().all()

    def __repr__(self):
        return f'<CharacterOverrideCollection {self.name}>'


class CharacterOverride(db.Model):
    """Individual character override with SVG data."""
    __tablename__ = 'character_overrides'

    id = db.Column(db.Integer, primary_key=True)
    collection_id = db.Column(db.Integer, db.ForeignKey('character_override_collections.id'), nullable=False, index=True)
    character = db.Column(db.String(1), nullable=False, index=True)  # Single character
    svg_data = db.Column(db.Text, nullable=False)  # SVG file contents

    # SVG metadata for seamless stitching
    viewbox_x = db.Column(db.Float, default=0.0)
    viewbox_y = db.Column(db.Float, default=0.0)
    viewbox_width = db.Column(db.Float, nullable=False)
    viewbox_height = db.Column(db.Float, nullable=False)
    baseline_offset = db.Column(db.Float, default=0.0)  # Vertical offset for baseline alignment

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Index for efficient lookup by collection and character
    __table_args__ = (db.Index('idx_collection_character', 'collection_id', 'character'),)

    def __repr__(self):
        return f'<CharacterOverride {self.character} in collection {self.collection_id}>'


class PageSizePreset(db.Model):
    """Custom page size preset configuration."""
    __tablename__ = 'page_size_presets'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True, index=True)
    description = db.Column(db.Text)
    width = db.Column(db.Float, nullable=False)  # Width in millimeters
    height = db.Column(db.Float, nullable=False)  # Height in millimeters
    is_default = db.Column(db.Boolean, default=False, nullable=False)  # Built-in preset (A4, Letter, etc.)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # Null for default presets
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    creator = db.relationship('User', backref='created_page_sizes', foreign_keys=[created_by])
    templates = db.relationship('TemplatePreset', backref='page_size_preset', lazy='dynamic', cascade='all, delete-orphan')

    def to_dict(self):
        """Convert preset to dictionary for API responses."""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'width': self.width,
            'height': self.height,
            'is_default': self.is_default,
            'is_active': self.is_active,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    def __repr__(self):
        return f'<PageSizePreset {self.name} ({self.width}x{self.height}mm)>'


class TemplatePreset(db.Model):
    """Template preset combining page size and generation settings."""
    __tablename__ = 'template_presets'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True, index=True)
    description = db.Column(db.Text)

    # Page configuration
    page_size_id = db.Column(db.Integer, db.ForeignKey('page_size_presets.id'), nullable=True)  # Null for custom dimensions
    custom_width = db.Column(db.Float, nullable=True)  # Custom width if not using preset
    custom_height = db.Column(db.Float, nullable=True)  # Custom height if not using preset
    orientation = db.Column(db.String(20), default='portrait')  # 'portrait' or 'landscape'

    # Margin settings (in millimeters)
    margin_top = db.Column(db.Float, default=20.0)
    margin_right = db.Column(db.Float, default=20.0)
    margin_bottom = db.Column(db.Float, default=20.0)
    margin_left = db.Column(db.Float, default=20.0)

    # Layout settings
    line_height = db.Column(db.Float, default=60.0)
    alignment = db.Column(db.String(20), default='left')  # 'left', 'center', 'right', 'justify'
    background = db.Column(db.String(50), default='white')

    # Writing settings
    global_scale = db.Column(db.Float, default=1.0)
    default_style = db.Column(db.Integer, default=9)
    default_bias = db.Column(db.Float, default=0.75)
    legibility = db.Column(db.Float, default=0.0)

    # Stroke settings
    stroke_color = db.Column(db.String(20), default='black')
    stroke_width = db.Column(db.Integer, default=2)

    # Text wrapping settings
    wrap_char_px = db.Column(db.Integer, nullable=True)
    wrap_ratio = db.Column(db.Float, nullable=True)
    wrap_utilization = db.Column(db.Float, nullable=True)

    # Advanced settings
    x_stretch = db.Column(db.Float, default=1.0)
    denoise = db.Column(db.Boolean, default=False)
    use_chunked = db.Column(db.Boolean, default=False)
    words_per_chunk = db.Column(db.Integer, nullable=True)
    chunk_spacing = db.Column(db.Float, nullable=True)
    rotate_chunks = db.Column(db.Boolean, default=False)

    # Metadata
    is_default = db.Column(db.Boolean, default=False, nullable=False)  # Built-in template
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # Null for default templates
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    creator = db.relationship('User', backref='created_templates', foreign_keys=[created_by])

    def to_dict(self, include_page_size=True):
        """Convert template to dictionary for API responses."""
        data = {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'page_size_id': self.page_size_id,
            'custom_width': self.custom_width,
            'custom_height': self.custom_height,
            'orientation': self.orientation,
            'margin_top': self.margin_top,
            'margin_right': self.margin_right,
            'margin_bottom': self.margin_bottom,
            'margin_left': self.margin_left,
            'line_height': self.line_height,
            'alignment': self.alignment,
            'background': self.background,
            'global_scale': self.global_scale,
            'default_style': self.default_style,
            'default_bias': self.default_bias,
            'legibility': self.legibility,
            'stroke_color': self.stroke_color,
            'stroke_width': self.stroke_width,
            'wrap_char_px': self.wrap_char_px,
            'wrap_ratio': self.wrap_ratio,
            'wrap_utilization': self.wrap_utilization,
            'x_stretch': self.x_stretch,
            'denoise': self.denoise,
            'use_chunked': self.use_chunked,
            'words_per_chunk': self.words_per_chunk,
            'chunk_spacing': self.chunk_spacing,
            'rotate_chunks': self.rotate_chunks,
            'is_default': self.is_default,
            'is_active': self.is_active,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

        if include_page_size and self.page_size_preset:
            data['page_size'] = self.page_size_preset.to_dict()

        return data

    def __repr__(self):
        return f'<TemplatePreset {self.name}>'
