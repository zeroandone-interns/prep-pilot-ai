from extensions import db
from datetime import datetime
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects.postgresql import ARRAY


class Organization(db.Model):
    __tablename__ = "Organization"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String, nullable=False)

    users = db.relationship("User", back_populates="organization")
    courses = db.relationship("Courses", back_populates="organization")


class User(db.Model):
    __tablename__ = "User"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    cognito_sub = db.Column(db.String, unique=True, nullable=False)
    organization_id = db.Column(
        db.Integer, db.ForeignKey("Organization.id"), nullable=False
    )

    organization = db.relationship("Organization", back_populates="users")
    chat_sessions = db.relationship("ChatSession", back_populates="user")
    enrollments = db.relationship("UserEnrollment", back_populates="user")


class UserEnrollment(db.Model):
    __tablename__ = "UserEnrollment"
    user_id = db.Column(db.Integer, db.ForeignKey("User.id"), primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey("Courses.id"), primary_key=True)
    enrollment_date = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", back_populates="enrollments")
    course = db.relationship("Courses", back_populates="enrollments")


class Courses(db.Model):
    __tablename__ = "Courses"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.String, nullable=False)
    description = db.Column(db.String)
    level = db.Column(db.String)
    duration = db.Column(db.String)
    nb_of_modules = db.Column(db.Integer)
    nb_of_sections = db.Column(db.Integer)
    terms = db.Column(ARRAY(db.String))

    organizationId = db.Column(
        db.Integer, db.ForeignKey("Organization.id"), nullable=False
    )

    organization = db.relationship("Organization", back_populates="courses")
    documents = db.relationship("Documents", back_populates="course")
    modules = db.relationship("Modules", back_populates="course")
    enrollments = db.relationship("UserEnrollment", back_populates="course")
    questions = db.relationship("Questions", back_populates="course")


class Modules(db.Model):
    __tablename__ = "Modules"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title_en = db.Column(db.String, nullable=False)
    title_fr = db.Column(db.String, nullable=False)
    title_ar = db.Column(db.String, nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey("Courses.id"), nullable=False)

    course = db.relationship("Courses", back_populates="modules")
    flashcards = db.relationship("FlashCards", back_populates="module")
    sections = db.relationship("Sections", back_populates="module")


class Sections(db.Model):
    __tablename__ = "Sections"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title_en = db.Column(db.String, nullable=False)
    title_fr = db.Column(db.String, nullable=False)
    title_ar = db.Column(db.String, nullable=False)
    module_id = db.Column(db.Integer, db.ForeignKey("Modules.id"), nullable=False)

    module = db.relationship("Modules", back_populates="sections")
    paragraphs = db.relationship("Paragraphs", back_populates="section")
    questions = db.relationship("Questions", back_populates="section")



class Paragraphs(db.Model):
    __tablename__ = "Paragraphs"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    content_title_en = db.Column(db.String)
    content_title_fr = db.Column(db.String)
    content_title_ar = db.Column(db.String)
    content_body_en = db.Column(db.String)
    content_body_fr = db.Column(db.String)
    content_body_ar = db.Column(db.String)
    section_id = db.Column(db.Integer, db.ForeignKey("Sections.id"), nullable=False)

    section = db.relationship("Sections", back_populates="paragraphs")


class Questions(db.Model):
    __tablename__ = "Questions"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    question_text_en = db.Column(db.String, nullable=False)
    question_text_fr = db.Column(db.String, nullable=False)
    question_text_ar = db.Column(db.String, nullable=False)
    option1_en = db.Column(db.String)
    option1_fr = db.Column(db.String)
    option1_ar = db.Column(db.String)
    option2_en = db.Column(db.String)
    option2_fr = db.Column(db.String)
    option2_ar = db.Column(db.String)
    option3_en = db.Column(db.String)
    option3_fr = db.Column(db.String)
    option3_ar = db.Column(db.String)
    correct_answer_en = db.Column(db.String)
    correct_answer_fr = db.Column(db.String)
    correct_answer_ar = db.Column(db.String)
    explanation_en = db.Column(db.String)
    explanation_fr = db.Column(db.String)
    explanation_ar = db.Column(db.String)
    course_id = db.Column(db.Integer, db.ForeignKey("Courses.id"), nullable=False)
    section_id = db.Column(db.Integer, db.ForeignKey("Sections.id"), nullable=True)

    course = db.relationship("Courses", back_populates="questions")
    section = db.relationship("Sections", back_populates="questions")



class FlashCards(db.Model):
    __tablename__ = "FlashCards"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    difficulty = db.Column(db.String)
    question_en = db.Column(db.String)
    question_fr = db.Column(db.String)
    question_ar = db.Column(db.String)
    answer_en = db.Column(db.String)
    answer_fr = db.Column(db.String)
    answer_ar = db.Column(db.String)
    module_id = db.Column(db.Integer, db.ForeignKey("Modules.id"), nullable=False)

    module = db.relationship("Modules", back_populates="flashcards")


class Documents(db.Model):
    __tablename__ = "Documents"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    s3_uri = db.Column(db.String)
    text = db.Column(db.String)
    course_id = db.Column(db.Integer, db.ForeignKey("Courses.id"), nullable=False)

    course = db.relationship("Courses", back_populates="documents")
    chunks = db.relationship("DocumentChunks", back_populates="document")


class DocumentChunks(db.Model):
    __tablename__ = "DocumentChunks"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    tokens = db.Column(db.Integer)
    text_en = db.Column(db.String)
    text_fr = db.Column(db.String)
    text_ar = db.Column(db.String)
    embeddings_ar = db.Column(Vector(1024))
    embeddings_fr = db.Column(Vector(1024))
    embeddings_en = db.Column(Vector(1024))
    document_id = db.Column(db.Integer, db.ForeignKey("Documents.id"), nullable=False)

    document = db.relationship("Documents", back_populates="chunks")


class ChatSession(db.Model):
    __tablename__ = "ChatSession"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    session_created_at = db.Column(db.DateTime)
    session_started_at = db.Column(db.DateTime)
    session_ended_at = db.Column(db.DateTime)
    user_id = db.Column(db.Integer, db.ForeignKey("User.id"), nullable=False)

    user = db.relationship("User", back_populates="chat_sessions")
    messages = db.relationship("ChatMessage", back_populates="session")


class ChatMessage(db.Model):
    __tablename__ = "ChatMessage"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    message = db.Column(db.String, nullable=False)
    sender = db.Column(db.String, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    session_id = db.Column(db.Integer, db.ForeignKey("ChatSession.id"), nullable=False)

    session = db.relationship("ChatSession", back_populates="messages")
