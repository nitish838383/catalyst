from app.db.session import Base
from app.models.user import User
from app.models.student import Student
from app.models.company import Company
from app.models.college import College
from app.models.department import Department
from app.models.skill import Skill, StudentSkill
from app.models.project import Project
from app.models.certification import Certification
from app.models.opportunity import Opportunity, OpportunitySkill
from app.models.application import Application
from app.models.match_score import MatchScore
from app.models.resume import Resume, ResumeSkill
from app.models.career_readiness import CareerReadiness
from app.models.roadmap import LearningRoadmap, RoadmapStep
from app.models.chat import ChatSession, ChatMessage
from app.models.notification import Notification
from app.models.collaboration import Collaboration, CollaborationSkill
from app.models.collaboration_participant import CollaborationParticipant
from app.models.challenge import IndustryChallenge, ChallengeSubmission
from app.models.assessment import SkillAssessment
from app.models.interview import Interview
from app.models.consent import UserConsent
from app.models.audit import AuditLog
