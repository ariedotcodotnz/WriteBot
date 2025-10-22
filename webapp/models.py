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
