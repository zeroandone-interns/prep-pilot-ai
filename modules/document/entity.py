from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.postgresql import JSON, ENUM
from datetime import datetime
from extensions import db
from pgvector.sqlalchemy import Vector

# Enums
LevelEnum = ENUM(
    "beginner", "intermediate", "advanced", name="levelenum", create_type=False
)
SenderEnum = ENUM("Assistant", "User", name="senderenum", create_type=False)
DocumentStatusEnum = ENUM(
    "uploaded", "processing", "done", name="documentstatusenum", create_type=False
)


class Organization(db.Model):
    __tablename__ = "Organization"
    id = db.Column(db.String, primary_key=True)
    name = db.Column(db.String, nullable=False)
    logo = db.Column(db.String)
    users = db.relationship("User", back_populates="organization")


class User(db.Model):
    __tablename__ = "User"
    id = db.Column(db.String, primary_key=True)
    cognito_sub = db.Column(db.String, nullable=False)
    organizationId = db.Column(db.String, db.ForeignKey("Organization.id"))

    organization = db.relationship("Organization", back_populates="users")
    chatSessions = db.relationship("ChatSession", back_populates="user")
    coursesCreated = db.relationship(
        "Courses", back_populates="created_by", foreign_keys="Courses.user_id"
    )
    enrollments = db.relationship("UserEnrollment", back_populates="user")


class UserEnrollment(db.Model):
    __tablename__ = "UserEnrollment"
    user_id = db.Column(db.String, db.ForeignKey("User.id"), primary_key=True)
    course_id = db.Column(db.String, db.ForeignKey("Courses.id"), primary_key=True)
    enrollment_date = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", back_populates="enrollments")
    course = db.relationship("Courses", back_populates="enrollments")


class Courses(db.Model):
    __tablename__ = "Courses"
    id = db.Column(db.String, primary_key=True)
    title = db.Column(db.String, nullable=False)
    description = db.Column(db.String, nullable=False)
    level = db.Column(LevelEnum)
    duration = db.Column(db.String)
    user_id = db.Column(db.String, db.ForeignKey("User.id"))

    created_by = db.relationship(
        "User", back_populates="coursesCreated", foreign_keys=[user_id]
    )
    modules = db.relationship("Modules", back_populates="course")
    enrollments = db.relationship("UserEnrollment", back_populates="course")
    documents = db.relationship("Document", back_populates="course")


class Modules(db.Model):
    __tablename__ = "Modules"
    id = db.Column(db.String, primary_key=True)
    title = db.Column(db.String, nullable=False)
    course_id = db.Column(db.String, db.ForeignKey("Courses.id"))

    course = db.relationship("Courses", back_populates="modules")
    sections = db.relationship("Sections", back_populates="module")


class Sections(db.Model):
    __tablename__ = "Sections"
    id = db.Column(db.String, primary_key=True)
    title = db.Column(db.String, nullable=False)
    content_order_id = db.Column(db.Integer)
    content_body = db.Column(db.String)
    module_id = db.Column(db.String, db.ForeignKey("Modules.id"))

    module = db.relationship("Modules", back_populates="sections")
    flashCards = db.relationship("FlashCards", back_populates="section")
    paragraphs = db.relationship("Paragraph", back_populates="section")
    questions = db.relationship("Questions", back_populates="section")


class Paragraph(db.Model):
    __tablename__ = "Paragraph"
    id = db.Column(db.String, primary_key=True)
    section_id = db.Column(db.String, db.ForeignKey("Sections.id"))
    paragraph_order = db.Column(db.Integer)
    content_title = db.Column(db.String)
    content_body = db.Column(db.String)

    section = db.relationship("Sections", back_populates="paragraphs")


class Questions(db.Model):
    __tablename__ = "Questions"
    id = db.Column(db.String, primary_key=True)
    question_text = db.Column(db.String)
    correct_answer = db.Column(db.String)
    explanation = db.Column(db.String)
    options = db.Column(JSON)
    is_confirmed = db.Column(db.Boolean)
    section_id = db.Column(db.String, db.ForeignKey("Sections.id"))

    section = db.relationship("Sections", back_populates="questions")


class FlashCards(db.Model):
    __tablename__ = "Flashcards"
    id = db.Column(db.String, primary_key=True)
    section_id = db.Column(db.String, db.ForeignKey("Sections.id"))
    question = db.Column(db.String)
    answer = db.Column(db.String)
    source_chunk = db.Column(db.String)

    section = db.relationship("Sections", back_populates="flashCards")


class ChatSession(db.Model):
    __tablename__ = "ChatSession"
    id = db.Column(db.String, primary_key=True)
    user_id = db.Column(db.String, db.ForeignKey("User.id"))
    session_started_at = db.Column(db.DateTime, default=datetime.utcnow)
    session_ended_at = db.Column(db.DateTime)

    user = db.relationship("User", back_populates="chatSessions")
    chatMessages = db.relationship("ChatMessage", back_populates="chatSession")


class ChatMessage(db.Model):
    __tablename__ = "ChatMessage"
    id = db.Column(db.String, primary_key=True)
    message = db.Column(db.String)
    sender = db.Column(SenderEnum)
    session_id = db.Column(db.String, db.ForeignKey("ChatSession.id"))
    createdAt = db.Column(db.DateTime, default=datetime.utcnow)

    chatSession = db.relationship("ChatSession", back_populates="chatMessages")


class Document(db.Model):
    __tablename__ = "Document"
    id = db.Column(db.String, primary_key=True)
    course_id = db.Column(db.String, db.ForeignKey("Courses.id"))
    s3_key = db.Column(db.String)
    type = db.Column(db.String)
    content = db.Column(db.String)

    course = db.relationship("Courses", back_populates="documents")
    chunks = db.relationship("DocumentChunk", back_populates="document")


class DocumentChunk(db.Model):
    __tablename__ = "DocumentChunk"
    id = db.Column(db.String, primary_key=True)
    document_id = db.Column(db.String, db.ForeignKey("Document.id"))
    text = db.Column(db.String)
    tokens = db.Column(db.Integer)
    embeddings = db.Column(Vector(1024), nullable=True)

    document = db.relationship("Document", back_populates="chunks")
