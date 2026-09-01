from enum import Enum


class ApplicationStatus(str, Enum):
    PENDING = "pending"
    APPLIED = "applied"
    IN_REVIEW = "in_review"
    INTERVIEW = "interview"
    REJECTED = "rejected"
    ACCEPTED = "accepted"
    WITHDRAWN = "withdrawn"


class ExperienceLevel(str, Enum):
    INTERN = "intern"
    JUNIOR = "junior"
    MID = "mid"
    SENIOR = "senior"
    LEAD = "lead"


class ScraperSource(str, Enum):
    REMOTEOK = "remoteok"
    LINKEDIN = "linkedin"
    INDEED = "indeed"
    GLASSDOOR = "glassdoor"
    MANUAL = "manual"


MIN_COMPATIBILITY_SCORE = 0.6
